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
        self.qb_auth = qbAuth
        self.client = QuickBooks(
            auth_client=qbAuth.auth_client,
            refresh_token=qbAuth.refresh_token,
            company_id=qbAuth.realm_id,
            minorversion=62 
        )


    def refresh_tokens(self):
        try:
            self.qb_auth.auth_client.refresh()
            self.client.auth_client = self.qb_auth.auth_client
            self.client.refresh_token = self.qb_auth.auth_client.refresh_token
        except AuthClientError as e:
            print(f"Error refreshing token: {str(e)}")
            raise

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
    def getTrialBalance(self, reportName, start_date=None, end_date=None):
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

    def get_report(self, report_type, start_date=None, end_date=None):
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'summarize_column_by': 'Month'
            }
            
            report = self.client.get_report(report_type=report_type, qs=params)
            #print the value of this report
            print(report)
            
            if any(option['Name'] == 'NoReportData' and option['Value'] == 'true' 
                   for option in report['Header']['Option']):
                print(f"No data available for {report_type} from {start_date} to {end_date}")
                return pd.DataFrame()

            data = []
            self.process_rows(report['Rows']['Row'], data)

            columns = ['Account'] + [col['ColTitle'] for col in report['Columns']['Column'][1:]]
            df = pd.DataFrame(data, columns=columns)
            print("Processed DataFrame:")
            print(df)
            return df

        except Exception as e:
            print(f"Error occurred while getting {report_type} report: {str(e)}")
            return pd.DataFrame()

    def process_rows(self, rows, data, parent=''):
        for row in rows:
            if row['type'] == 'Data':
                account = parent + row['ColData'][0]['value']
                amounts = [col['value'] for col in row['ColData'][1:]]
                data.append([account] + amounts)
            elif row['type'] == 'Section' and 'Rows' in row:
                new_parent = parent + row['Header']['ColData'][0]['value'] + ' - '
                self.process_rows(row['Rows']['Row'], data, new_parent)
            elif 'Summary' in row:
                account = parent + row['Summary']['ColData'][0]['value']
                amounts = [col['value'] for col in row['Summary']['ColData'][1:]]
                data.append([account] + amounts)

    def get_report_with_comparison(self, report_type, start_date, end_date, comparison_start_date, comparison_end_date):
        # Implementation for comparison with another period
        report = self.client.get_report(report_type, start_date, end_date)
        comparison_report = self.client.get_report(report_type, comparison_start_date, comparison_end_date)
        
        # Combine the reports and calculate differences
        # This is a simplified example; you'll need to implement the actual comparison logic
        combined_report = {
            'current': report,
            'comparison': comparison_report,
            'differences': self._calculate_differences(report, comparison_report)
        }
        
        return combined_report

    def get_report_with_budget(self, report_type, start_date, end_date):
        # Implementation for comparison with budget
        report = self.client.get_report(report_type, start_date, end_date)
        budget_report = self.client.get_report('Budget', start_date, end_date)
        
        # Combine the report with budget data
        # This is a simplified example; you'll need to implement the actual budget comparison logic
        combined_report = {
            'actual': report,
            'budget': budget_report,
            'variances': self._calculate_budget_variances(report, budget_report)
        }
        
        return combined_report

    def _calculate_differences(self, current_report, comparison_report):
        # Implement logic to calculate differences between two periods
        # This is a placeholder and should be replaced with actual implementation
        return {}

    def _calculate_budget_variances(self, actual_report, budget_report):
        # Implement logic to calculate variances between actual and budget
        # This is a placeholder and should be replaced with actual implementation
        return {}