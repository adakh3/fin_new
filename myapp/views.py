# views.py
from django.shortcuts import render
from .forms import UploadFileForm
import os
from .handle_uploaded_file import HandleUploadedFile
from django.http import JsonResponse
import pandas as pd




def upload_file_view(request):
    #by default this should show the html file in my templates folder called upload.html

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            response = handle_file(request.FILES['file'], request )
            print('Form submitted')
            #print (response)
            return render(request, 'myapp/upload.html', {'form': form, 'message': response})
            
            
            #return redirect('success_url')  # replace with your success url
    else:
        form = UploadFileForm()
    return render(request, 'myapp/upload.html', {'form': form})

def handle_file(f, request):
#if the file is an excel file, then we upload it and start, else send an error message
    
    print('Handle file called')
    
        # Check the file extension
    _, ext = os.path.splitext(f.name)
    if ext not in ['.xls', '.xlsx']:
        print('Not an excel file. Please upload an excel file')
        return render(request, 'myapp/upload.html', {'error': 'Invalid file type. Please upload an excel file'})

    try:
        # Try to read the file with pandas
        data = pd.read_excel(f)
        # rest of your code
        
    except ValueError as e:
        print('Invalid file type. Please upload an excel file')
        return render(request, 'myapp/upload.html', {'error': 'Invalid file type. Please upload an excel file'})

    '''except Exception as e:
        raise ValueError("The provided file is not a valid Excel file.") from e'''

    if not os.path.exists('uploaded_files'):
        os.makedirs('uploaded_files')

    with open('uploaded_files/' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    #now we can load the data from the file and do some analysis
    #initialise the object
    my_object = HandleUploadedFile(f.name)
    #call the main method
    print('This is what the user selected:', request.POST['insights'])
    print('The industry is:', request.POST['industry'])



    return my_object.main(request.POST['insights'], request.POST['industry'])





