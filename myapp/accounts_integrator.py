from quickbooks import QuickBooks

#To do:replace these with environment variables 
client = QuickBooks(
    auth_type='oauth2',
    client_id='ABeJieEWZIujd5ZU6gigEYcnFSjSgElDrSv8tYoNIeaNB5NsA3',
    client_secret='Ef0QyYIrFNhZtMplSQ6hNEYRS03wRwD9ZMw4DccS',
    app_environment='sandbox',
    callback_url='upload_file_view',
    )

'''
        realm_id=os.getenv('REALM_ID'),
    consumer_key=os.getenv('CLIENT_ID'),
    consumer_secret=os.getenv('CLIENT_SECRET'),
    callback_url=os.getenv('CALLBACK_URL'),
'''


# Get all customers
customers = client.get_all('Customer')

# Create a new customer
new_customer = {
    "DisplayName": "New Customer",
    # Other customer fields...
}
client.create('Customer', new_customer)