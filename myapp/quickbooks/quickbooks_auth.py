
from quickbooks import QuickBooks
from dotenv import load_dotenv
from quickbooks.objects.customer import Customer
from intuitlib.client import AuthClient
from django.conf import settings
import os
import pdb

class QuickbooksAuth:

    def __init__(self):
        load_dotenv()  # take environment variables from .env.
        self.auth_client = AuthClient(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
            redirect_uri=settings.QB_REDIRECT_URL,
            environment=settings.QB_APP_ENV
        )
