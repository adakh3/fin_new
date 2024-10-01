from venv import logger
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError
from django.utils import timezone
from django.conf import settings
import datetime
import logging

class QuickbooksAuth:


    scopes = [Scopes.ACCOUNTING]  # This uses the enum, which is what intuitlib expects]
    def __init__(self, user):
        self.user = user
        self.auth_client = AuthClient(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
            environment=settings.QB_APP_ENV,
            redirect_uri=settings.QB_REDIRECT_URL,
        )
        self.load_tokens()

    def load_tokens(self):
        profile = self.user.userprofile
        self.auth_client.access_token = profile.quickbooks_access_token
        self.auth_client.refresh_token = profile.quickbooks_refresh_token
        self.realm_id = profile.quickbooks_realm_id
        self.token_expiry = profile.quickbooks_token_expiry

    def save_tokens(self):
        profile = self.user.userprofile
        profile.quickbooks_access_token = self.auth_client.access_token
        profile.quickbooks_refresh_token = self.auth_client.refresh_token
        profile.quickbooks_realm_id = self.realm_id
        profile.quickbooks_token_expiry = self.token_expiry
        profile.save()

    def is_access_token_valid(self):
        if not self.token_expiry:
            return False
        return self.token_expiry > timezone.now()

    def refresh_tokens(self):
        try:
            self.auth_client.refresh()
            self.token_expiry = timezone.now() + datetime.timedelta(hours=1)
            self.save_tokens()
            return True
        except AuthClientError as e:
            logger.error(f"Error refreshing token: {str(e)}")
            if 'invalid_grant' in str(e):
                # The refresh token is no longer valid
                self.clear_tokens()
            return False

    def clear_tokens(self):
        self.auth_client.access_token = None
        self.auth_client.refresh_token = None
        self.token_expiry = None
        self.save_tokens()

    def get_authorization_url(self):
        return self.auth_client.get_authorization_url(self.scopes)

    def get_bearer_token(self, auth_code):
        self.auth_client.get_bearer_token(auth_code, realm_id=self.realm_id)
        self.token_expiry = timezone.now() + datetime.timedelta(hours=1)
        self.save_tokens()

    def ensure_valid_token(self):
        if not self.is_access_token_valid():
            return self.refresh_tokens()
        return True