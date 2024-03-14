# views.py
from django.shortcuts import render
from .forms import UploadFileForm
import os
from .handle_pl_data import HandlePLData
from django.http import JsonResponse
import pandas as pd
import mimetypes


def upload_file_view(request):
    #by default this should show the html file in my templates folder called upload.html
    context = {}
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                row_number = int(request.POST['row_number'])  # Get the row_number field
                response, charts = handle_file(request.FILES['file'], request, row_number )
            except Exception as e:
                context['error'] = f'{e}'
                return render(request, 'myapp/upload.html', context)
            
            print('Form submitted')
            return render(request, 'myapp/upload.html', {'form': form, 'message': response, 'charts': charts})
    else:
        form = UploadFileForm()
    return render(request, 'myapp/upload.html', {'form': form})


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
        results = my_object.main(request.POST['insights'], request.POST['industry'], row_number)
    except Exception as e:
        raise ValueError(str(e)) from e

    #else:
    return results, my_object.charts

