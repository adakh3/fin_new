from quickbooks import QuickBooks
from dotenv import load_dotenv
from quickbooks.objects.customer import Customer
from intuitlib.client import AuthClient
from django.conf import settings
from datetime import datetime, timedelta
import os
import pdb
import pandas as pd
from .quickbooks_auth import QuickbooksAuth
#from quickbooks.objects import Report

class QuickbooksIntegrator:

    #def __init__(self, refresh_token, realm_id):
    def __init__(self, qbAuth: QuickbooksAuth):

        #at the moment connects to my company sandbox, and later will connect to the prod company of my users through oAuth2
        self.auth_client = qbAuth.auth_client
        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=qbAuth.refresh_token,
            company_id=qbAuth.realm_id,
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
    def getReport(self, reportName, start_date=None, end_date=None):
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # Attempt to get the trial balance
            #trial_balance = self.client.get_report('TrialBalance', params=params)
                    # Fetch the report
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'summarize_column_by': 'Month'
            }
            
            print(self.client.get_report(reportName, qs=params))

            report = self.client.get_report(report_type=reportName, qs=params)
            return report
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
            trial_balance = self.client.get_report(report_type=reportName, qs=params)

            return trial_balance

    def get_profit_and_loss(self, start_date, end_date):
        try:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'summarize_column_by': 'Month'
            }
            
            report = self.getReport(reportName='ProfitAndLoss', start_date=start_date, end_date=end_date)
            
            # Convert the report data to a pandas DataFrame
            data = []
            for row in report['Rows']['Row']:
                if 'ColData' in row:
                    data.append({
                        'Account': row['ColData'][0]['value'],
                        'Amount': row['ColData'][1]['value'] if len(row['ColData']) > 1 else None
                    })
            
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            print(f"Error occurred while getting Profit and Loss report: {str(e)}")
            return None