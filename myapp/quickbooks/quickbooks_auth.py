from quickbooks import QuickBooks
from dotenv import load_dotenv
from quickbooks.objects.customer import Customer
from intuitlib.client import AuthClient
from django.conf import settings
import os
import pdb


"""
QuickBooks Integration Views

This module contains views for integrating with QuickBooks and processing financial data.
It includes functions for:
- Initiating QuickBooks operations
- Retrieving profit and loss data
- Processing financial data and generating insights
- Handling QuickBooks authentication (currently using hardcoded credentials for development)

Note: The use of hardcoded credentials is for development purposes only and should be
replaced with proper authentication flow in a production environment.
"""

class QuickbooksAuth:

    def __init__(self):
        load_dotenv()  # take environment variables from .env.
        self.auth_client = AuthClient(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
            redirect_uri=settings.QB_REDIRECT_URL,
            environment=settings.QB_APP_ENV
        )
        # Use your development tokens here
        self.realm_id = settings.QUICKBOOKS_REALM_ID
        self.access_token = settings.QUICKBOOKS_ACCESS_TOKEN
        self.refresh_token = settings.QUICKBOOKS_REFRESH_TOKEN
        self.auth_client.access_token = self.access_token
        self.auth_client.refresh_token = self.refresh_token
        self.environment = settings.QB_APP_ENV

    
    def has_valid_token(self):
        return True  # Always return True for development tokens

    def get_access_token(self):
        return self.access_token

    def get_auth_url(self):
        """
        Get the authorization URL for QuickBooks OAuth 2.0.
        """
        auth_url = self.auth_client.get_authorization_url()
        return auth_url

    def exchange_code_for_token(self, code):
        """
        Exchange the authorization code for an access token and refresh token.
        """
        tokens = self.auth_client.get_bearer_token(code)
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        return access_token, refresh_token

    def refresh_access_token(self, refresh_token):
        """
        Refresh the access token using the refresh token.
        """
        tokens = self.auth_client.refresh(refresh_token)
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        return access_token, refresh_token

    def revoke_access_token(self, access_token):
        """
        Revoke the access token.
        """
        self.auth_client.revoke(access_token)

    def get_customer_data(self, access_token, realm_id):
        """
        Get customer data from QuickBooks using the access token and realm ID.
        """
        quickbooks_client = QuickBooks(
            auth_client=self.auth_client,
            access_token=access_token,
            company_id=realm_id
        )
        customers = Customer.all(quickbooks_client)
        return customers