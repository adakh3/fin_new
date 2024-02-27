import pandas as pd
import numpy as np
import requests
import json
import os
import openai
from datetime import datetime
from openai import OpenAI
from openpyxl import load_workbook




''' Overall separate out key KPIs, revenues, COGS, costs, other income and costs --- 
one by one send these all to GPT-4 to get insights and predictions 
then get a summary of all the insights and predictions
'''



class HandleUploadedFile:

    client = OpenAI()
    openai.api_key = os.getenv('OPENAI_API_KEY')

    def __init__(self, filename):
        self.filepath = 'uploaded_files/' + filename
        self.filename = filename

    #load the data from an excel file 
    def find_data_start(self):

        # Load the workbook
        #wb = load_workbook(self.filepath)

        # Save the workbook
        #wb.save(filename=self.filepath)


        data = pd.read_excel(self.filepath)

        df_numeric = data.select_dtypes(include=[np.number])

         # Check if all numeric values are zero
        if (df_numeric == 0).all().all():
            return("Zero value error")
    
        
        for i, row in data.iterrows():
            if not row.isnull().any():
                if i == 0:
                    return i
                else:
                    return i -1
        return None


    def load_data_table(self, start_row):
        if start_row is not None:
            start_row = self.find_data_start()
            if start_row is not None:
                data = pd.read_excel(self.filepath, skiprows=range(start_row))
            else:
                data = pd.DataFrame()

        if len(data.columns) < 1:
            raise Exception("File does not contain any data. Please upload a file with data.")
            
        
        return data


    # clean the data 
    def clean_data(self, data):

        # remove rows with all NaNs
        data = data.dropna(axis=0, how='all')
        # remove columns with all NaNs
        data = data.dropna(axis=1, how='all')

        #rename the columns

        expected_columns = ['Accounts', 'Period 2 values', 'Period 1 values', 'Change in values', 'Percentage change']
        print (len(data.columns))

        if len(data.columns) < len(expected_columns):
            print ('Expected columns not found in the data. Adding missing columns.')
            missing_columns = len(expected_columns) - len(data.columns)
            data[expected_columns[-missing_columns:]] = np.nan
        
        data.columns = expected_columns
        
        return data


    def key_kpis(self, data):
        titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings', 'Total Other Expenses', 'Total Other Income(Loss)']

        # Create a boolean mask
        mask = data.iloc[:, 0].isin(titles_to_keep)

        # Index the DataFrame with the mask
        data = data[mask]

        return data


    def add_more_columns(self, data):
        # add more columns to the data

        if data is not None:

            total_income_period_1 = data.loc[data['Accounts'] == 'Total Income', 'Period 1 values'].values[0]
            
            try:
                data['Percentage of sales period 1'] = data['Period 1 values'] / total_income_period_1 * 100
            except:
                print ('Division by zero error')
                data ['Percentage of sales period 1'] = 0

            total_income_period_2 = data.loc[data['Accounts'] == 'Total Income', 'Period 2 values'].values[0]
            data['Percentage of sales period 2'] = data['Period 2 values'] / total_income_period_2 * 100

            data['Change in percentage of sales'] = data['Percentage of sales period 2'] - data['Percentage of sales period 1'] 
            data ['Account type'] = np.nan

        return data
    

        #from data mark all the accounts that are income accounts, where account type is the type of account
    def mark_account_types(self, data, accountType):
        # Find the indices of the rows where column 1 between account type and total account type
        
        matching_rows_start = data[data['Accounts'] == accountType]
        if matching_rows_start.empty:
            print(f"No rows with accountType: {accountType}")
            return data
        start_index = matching_rows_start.index[0] + 1

        # Check if 'Total '+ accountType exists in 'Accounts'
        matching_rows_end = data[data['Accounts'] == 'Total '+ accountType]
        if matching_rows_end.empty or matching_rows_end.index[0] == 0:
            print(f"No rows with 'Total {accountType}'")
            return data
        end_index = matching_rows_end.index[0] - 1


        # Add the 'account type' column for the rows between start_index and end_index
        data.loc[start_index:end_index, 'Account type'] = accountType

        # Set 'Account type' to none for rows where 'Accounts' contains 'total'
        mask = data['Accounts'].str.contains('total', case=False)
        data.loc[mask, 'Account type'] = np.nan


        titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings', 'Total Other Expenses', 'Total Other Income(Loss)']

        # Create a boolean mask
        mask = data.iloc[:, 0].isin(titles_to_keep)

        # Index the DataFrame with the mask
        data.loc[mask, 'Account type'] = 'Key KPI'

        return data


    # structure the data into hierarchy (accounts and sub accounts) - will do this later


    #analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 



    #send to AI for human language interpretation
    def send_to_AI(self, data):

        csv_text = data.to_csv(index=False)

        completion = self.client.chat.completions.create(
        #model="gpt-3.5-turbo",
        model ="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": '''You are an expert in finacial analysis 
             and describe your analysis to business owners who only have rudimentary 
             financial knowledge, so you expain it to them in easy language. 
             
             Focusing only on important considerations rather than a line by line analysis. 

             In additio to re-iterating numbers, also mentione precentages where necessary, 
             and provide your insight as well. If there are any discrepencies in the 
             data, or things you cant explain from the data, point those out too. 
             
             Make sure to  look at all the columns for your analysis and explanation, especially percentage of sales.
             
             Start with a summary of your analysis especially giving insights about net profits, and then delve deeper

             Structure your respond with headings and formating, suiteable for a business report, and 
             suitable for html rendering. Headings will be <h3> and <h4> tags.

             - First go through the 'account type' column and summarise key KPIs, then similarly go through the 
             'account type' columns and summarise 'Income' accounts, then 'Expense' accounts and so on. With these non-KPI 
             accounts, ignore the ones with low % to sales unless the increase is significant.

             Output structure and headings shougld always be exactly as follows:
                - Summary
                - Revenues
                - Costs of Goods Sold   
                - Gross Profits
                - Administrative Costs
                - Other Income and Costs
                - Net Profits
                - Discrepencies
                
             


            In the end summarise the entire analysis and provide insights about net profits.   
             '''},
            {"role": "user", "content": f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data.",}
            ]
        )

        return completion.choices[0].message.content





    def main(self):        
        #calling all the functions now 
        i = self.find_data_start()
        if i == 'Zero value error':
            return 'Unable to read the data. Please open the file in Excel, save it, and try again.'
        
        data = self.clean_data(self.load_data_table(i))
        print('Data cleaned', str(datetime.now().time()))

        dataDetails = self.mark_account_types(data, 'Income')
        dataDetails = self.mark_account_types(data, 'Cost of Sales')
        dataDetails = self.mark_account_types(data, 'Expenses')
        dataDetails = self.mark_account_types(data, 'Other Income(Loss)')
        dataDetails = self.mark_account_types(data, 'Other Expenses')
        #to delete these checks later
        print('Account types marked', str(datetime.now().time()))
        savedFilename = 'uploaded_files/cleaned_data_all_accounts' + self.filename
        data.to_excel(savedFilename, index=False)
        print('File with all accounts saved ' + str(datetime.now().time()))

        data = self.add_more_columns(dataDetails)
        print('More columns added ' + str(datetime.now().time()))
        
        '''
        #first get analysis on key KPIs
        data = self.key_kpis(dataDetails)
        savedFilename = 'uploaded_files/cleaned_data_' + self.filename
        print('Data saved to: ', savedFilename, str(datetime.now().time()))
        data.to_excel(savedFilename, index=False)
       '''
        
        print('Data being sent to AI for analysis and interpretation ' + str(datetime.now().time()))
        data = self.send_to_AI(data)
        print('Data returned from AI ' + str(datetime.now().time()))
        
        #now similarly get analysis on income accounts only

        
        
        return data

