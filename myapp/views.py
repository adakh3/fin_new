# views.py
import profile
from django.shortcuts import render

from myapp.openai_function_caller import OpenAIFunctionCaller
from .forms import UploadFileForm
import os
from .handle_pl_data import HandlePLData
from django.http import JsonResponse
import pandas as pd
import mimetypes
from .text_formatter import TextFormatter
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import get_template
import json
from django.http import FileResponse
import tempfile
from .quickbooks.quickbooks_integrator import QuickbooksIntegrator
from .quickbooks.quickbooks_auth import QuickbooksAuth
from django.conf import settings
from intuitlib.exceptions import AuthClientError
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags
from .models import UserProfile
from django.contrib.auth.models import User
import logging


logger = logging.getLogger(__name__)

#@login_required
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def upload_file_view(request):
    #by default this should show the html file in my templates folder called upload.html
    context = {}
    if request.method == 'POST':
        try:
            #row_number = int(request.POST['row_number'])  # Get the row_number field
            #ignoring the row number at the moment 
            row_number = 0
            response, charts = handle_file(request.FILES['file'], request)
        except Exception as e:
            context['error'] = f'{e}'
            return render(request, 'myapp/upload.html', context)
        
        print('Form submitted')
        return render(request, 'myapp/upload.html', {'message': response, 'charts': charts})
    return render(request, 'myapp/upload.html')


def file_sanitiser(f, max_size=5000000):

    # Check the file extension
    ext = os.path.splitext(f.name)[1]
    valid_extensions = ['.xls', '.xlsx']
    if ext not in valid_extensions:
        raise ValueError('Invalid file type. Please upload a valid excel file.')

    # Check the MIME type
    mime_type = mimetypes.guess_type(f.name)[0]
    valid_mime_types = ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    if mime_type not in valid_mime_types:
        raise ValueError('Invalid file type. Please upload a valid excel file.')
    
        # Check the file content
    try:
        data = pd.read_excel(f)

    except Exception as e:
        raise ValueError('Invalid file content. Please upload a valid excel file.')
    

    # Check the file size
    if f.size > max_size:
        raise ValueError('File size is too large. Please upload a file smaller than 5MB.')
    
    return True


def handle_file(f, request):
    try:
        file_sanitiser(f)
    except Exception as e:
        raise ValueError(str(e)) from e
    
    if not os.path.exists('uploaded_files'):
        os.makedirs('uploaded_files')

    with open('uploaded_files/' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    #now we can load the data from the file and do some analysis
    my_object = HandlePLData(f.name)
    
    #call the main method of the HandlePLData class
    try:
        results = my_object.main(request.POST['insights'], request.POST['industry'], request.POST["additional_info"])
        #self, insights_preference, industry, additionalInfo, row_number
        if(results is not None):
            results = TextFormatter.convert_markdown_to_html(results)
    except Exception as e:
        raise ValueError(str(e)) from e

    #else:
    return results, my_object.charts


@login_required
def start_quickbooks_auth(request):
    qb_auth = QuickbooksAuth(request.user)
    auth_url = qb_auth.get_authorization_url()
    return redirect(auth_url)


@login_required
def quickbooks_callback(request):
    auth_code = request.GET.get('code')
    realm_id = request.GET.get('realmId')
    
    if auth_code and realm_id:
        qb_auth = QuickbooksAuth(request.user)
        qb_auth.realm_id = realm_id
        qb_auth.get_bearer_token(auth_code)
        # Save the tokens after obtaining them
        qb_auth.save_tokens()


        return redirect('home')  # or wherever you want to redirect after successful auth
    else:
        # Handle error
        return redirect('error_page')


# Update the existing quickbooks_report_analysis view
@csrf_exempt
@require_POST
@login_required
def quickbooks_report_analysis(request):
    data = json.loads(request.body)
    qb_auth = QuickbooksAuth(user=request.user)
    
    try:
        if not qb_auth.is_access_token_valid():
            if not qb_auth.refresh_tokens():
                # Token refresh failed, user needs to re-authenticate
                return JsonResponse({
                    'error': 'QuickBooks authentication has expired',
                    'needs_reauth': True
                }, status=401)

        qb_integrator = QuickbooksIntegrator(qb_auth)
        
        report_type = data['report_type']
        start_date = data['start_date']
        end_date = data['end_date']
        comparison_type = data.get('comparison_type', 'none')
        
        if comparison_type == 'none':
            pl_data = qb_integrator.get_report(report_type, start_date=start_date, end_date=end_date)
        elif comparison_type == 'period':
            comparison_start_date = data['comparison_start_date']
            comparison_end_date = data['comparison_end_date']
            pl_data = qb_integrator.get_report_with_comparison(
                report_type, 
                start_date=start_date, 
                end_date=end_date,
                comparison_start_date=comparison_start_date,
                comparison_end_date=comparison_end_date
            )
        elif comparison_type == 'budget':
            pl_data = qb_integrator.get_report_with_budget(
                report_type,
                start_date=start_date,
                end_date=end_date
            )
        else:
            raise ValueError(f"Invalid comparison type: {comparison_type}")
        
        # Create HandlePLData instance with QuickBooks data
        my_object = HandlePLData(qb_data=pl_data)
        
        # Call main function with appropriate parameters
        results = my_object.main(
            data['insights'],
            data['industry'],
            data['additional_info']
        )
        
        if results is not None:
            results = TextFormatter.convert_markdown_to_html(results)
        
        return JsonResponse({
            'success': True,
            'results': mark_safe(results),
            'charts': [mark_safe(chart) for chart in my_object.charts]
        }, safe=False)
        
    except Exception as e:
        logger.error(f"Error in quickbooks_report_analysis: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    

    from django.shortcuts import redirect

def after_logout(request):
    return redirect('home')

# Create a dictionary to store OpenAIFunctionCaller instances for each user
function_callers = {}

@csrf_exempt
@require_POST
@login_required
def quickbooks_chat(request):
    data = json.loads(request.body)
    user_message = data.get('message', '')
    
    # Get or create an OpenAIFunctionCaller instance for this user
    if request.user.id not in function_callers:
        function_callers[request.user.id] = OpenAIFunctionCaller(request.user, "gpt-4o-mini")
    
    function_caller = function_callers[request.user.id]
    ai_response = function_caller.process_message(user_message)
    
    
    return JsonResponse({'response': ai_response})# Keep the existing start_quickbooks_operations function unchanged

@login_required
def check_quickbooks_auth(request):
    qb_auth = QuickbooksAuth(request.user)
    is_valid = qb_auth.is_access_token_valid()
    if not is_valid:
        is_valid = qb_auth.refresh_tokens()
    return JsonResponse({'is_valid': is_valid})
