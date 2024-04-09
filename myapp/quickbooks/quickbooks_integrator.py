from quickbooks import QuickBooks
from dotenv import load_dotenv
from quickbooks.objects.customer import Customer
from intuitlib.client import AuthClient
from django.conf import settings
from datetime import datetime, timedelta



import os
import pdb

class QuickbooksIntegrator:

    def __init__(self, refresh_token, realm_id):

        self.auth_client = AuthClient(
        client_id = settings.QUICKBOOKS_CLIENT_ID,
        client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
        redirect_uri=settings.QB_REDIRECT_URL,
        environment='sandbox'  # or 'production'
        )

        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=refresh_token,
            company_id=realm_id,
            minorversion=62
        )


    def refresh_and_store_tokens(self):
        # Refresh the access token
        self.client.refresh()

        # Store the new access and refresh tokens
        #store_tokens(quickbooks_client.access_token, quickbooks_client.refresh_token)

    def getCustomers(self):
        try:
            customers =  Customer.all(qb=self.client)
            return customers
        except Exception as e:
            # If we get an UnauthorizedException, the access token has expired
            self.refresh_and_store_tokens(self.client)

            #retry the call 
            customers =  Customer.all(qb=self.client)
            return customers

    #expects dates in '%Y-%m-%d' format eg '2022-12-31'
    def getReport(self, start_date=None, end_date=None):
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # Attempt to get the trial balance
            #trial_balance = self.client.get_report('TrialBalance', params=params)
                    # Fetch the Trial Balance report
            
            #print qb.get_report('ProfitAndLoss','summarize_column_by=Month&start_date=2014-01-01&end_date=2014-12-31')
            params = {
                'start_date': start_date,
                'end_date': end_date,
                }

            trial_balance = self.client.get_report(report_type='TrialBalance', qs=params)
            return trial_balance
        except Exception as e:
            # If we get an UnauthorizedException, the access token has expired
            self.refresh_and_store_tokens()

            # Retry the call

            #trial_balance = self.client.get_report('TrialBalance', params=params)
            '''
            trial_balance = self.client.get_report(
                report_type='TrialBalance',
                start_date=start_date,
                end_date=end_date
            )'''
            trial_balance = self.client.get_report(report_type='TrialBalance', qs=params)

            # Print the total assets
            print('Total assets:',trial_balance['Total Assets'])

            # Print the total liabilities
            print('Total liabilities:',trial_balance['Total Liabilities'])

            # Print the equity
            print('Total assets:',trial_balance['Equity'])

            return trial_balance