# views.py
from django.shortcuts import render
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
from django.http import FileResponse
from django.template.loader import get_template
import json
from django.http import FileResponse
import tempfile
from .quickbooks.quickbooks_integrator import QuickbooksIntegrator



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
            response, charts = handle_file(request.FILES['file'], request, row_number )
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


#do this later - not implemented yet *****
@csrf_exempt
@require_POST
def save_as_pdf(request):
    data = json.loads(request.body)
    aioutput = data['aioutput']

    # Render the aioutput in a Django template
    template = get_template('aioutput_template.html')
    html = template.render({'aioutput': aioutput})

    # Convert the HTML to PDF
    html_weasyprint = HTML(string=html)
    pdf_file = html_weasyprint.write_pdf()

    # Create a temporary file to hold the PDF
    temp = tempfile.NamedTemporaryFile()

    # Write the PDF data to the temporary file
    temp.write(pdf_file)
    temp.seek(0)

    # Return the PDF file as a response
    return FileResponse(temp, as_attachment=True, filename='aioutput.pdf')

def handle_file(f, request, row_number):
#if the file is an excel file, then we upload it and start, else send an error message
    
    try:
        file_sanitiser(f)
    except Exception as e:
        raise ValueError(str(e)) from e
        #return str(e)
        
    
    if not os.path.exists('uploaded_files'):
        os.makedirs('uploaded_files')

    with open('uploaded_files/' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    #now we can load the data from the file and do some analysis
    my_object = HandlePLData(f.name)
    
    #call the main method of the HandlePLData class
    try:
        results = my_object.main(request.POST['insights'], request.POST['industry'], request.POST["additional_info"], row_number)
        #self, insights_preference, industry, additionalInfo, row_number
        if(results is not None):
            results = TextFormatter.convert_markdown_to_html(results)
    except Exception as e:
        raise ValueError(str(e)) from e

    #else:
    return results, my_object.charts



def start_quickbooks_auth(request):
    qb_auth = AccountsIntegrator()
    auth_url = qb_auth.get_authorization_url()
    return redirect(auth_url)


# views.py continued

def quickbooks_callback(request):
    auth_code = request.GET.get('code')
    if auth_code:
        qb_auth = AccountsIntegrator()
        access_token = qb_auth.get_bearer_token(auth_code)
        # Store this access token securely for future API calls
        return HttpResponse("QuickBooks Connected Successfully!")
    else:
        return HttpResponse("Error connecting to QuickBooks", status=400)
