from quickbooks import QuickBooks
from dotenv import load_dotenv
from quickbooks.objects.customer import Customer
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from django.conf import settings
import os
import pdb
import logging
import requests



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


logger = logging.getLogger(__name__)

class QuickbooksAuth:

    def __init__(self):
        load_dotenv()  # take environment variables from .env.
        self.auth_client = AuthClient(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
            redirect_uri=settings.QB_REDIRECT_URL,
            environment=settings.QB_APP_ENV
        )
        self.realm_id = None
        self.access_token = None
        self.refresh_token = None

    def get_auth_url(self):
        return self.auth_client.get_authorization_url([
            Scopes.ACCOUNTING,
            Scopes.OPENID,
            Scopes.EMAIL
        ])

    def exchange_code_for_token(self, auth_code, realm_id):
        self.realm_id = realm_id
        logger.info(f"Attempting to get bearer token. Auth code: {auth_code}, Realm ID: {realm_id}")
        
        # Prepare the request data
        token_endpoint = self.auth_client.token_endpoint
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': settings.QB_REDIRECT_URL
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        auth = (settings.QUICKBOOKS_CLIENT_ID, settings.QUICKBOOKS_CLIENT_SECRET)

        try:
            # Make the request
            response = requests.post(token_endpoint, data=data, headers=headers, auth=auth)
            
            # Log the full request and response details
            logger.info(f"Token request URL: {token_endpoint}")
            logger.info(f"Token request headers: {headers}")
            logger.info(f"Token request data: {data}")
            logger.info(f"Token response status code: {response.status_code}")
            logger.info(f"Token response content: {response.text}")

            # Check if the request was successful
            response.raise_for_status()

            # Parse the JSON response
            tokens = response.json()
            
            if not tokens:
                raise ValueError("Received empty response from QuickBooks API")

            self.access_token = tokens.get('access_token')
            self.refresh_token = tokens.get('refresh_token')

            if not self.access_token or not self.refresh_token:
                raise ValueError("Access token or refresh token missing from response")

            return self.access_token, self.refresh_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to QuickBooks API failed: {str(e)}")
            raise
        except ValueError as e:
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Unexpected error in exchange_code_for_token: {str(e)}", exc_info=True)
            raise

    '''
    def exchange_code_for_token(self, auth_code, realm_id):
        #self.realm_id = realm_id
        tokens = self.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        self.access_token = tokens['access_token']
        self.refresh_token = tokens['refresh_token']
        return self.access_token, self.refresh_token
    '''
    
    def refresh_tokens(self):
        if self.refresh_token:
            tokens = self.auth_client.refresh(refresh_token=self.refresh_token)
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            return self.access_token, self.refresh_token
        else:
            raise Exception("No refresh token available. User needs to reauthorize.")

    def has_valid_token(self):
        return self.access_token is not None and not self.auth_client.token_expired()

    def set_tokens(self, access_token, refresh_token, realm_id):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.realm_id = realm_id

    def get_user_info(self):
        return self.auth_client.get_user_info(self.access_token)