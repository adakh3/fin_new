import pandas as pd
import numpy as np
import requests
import json
import os
import openai
from datetime import datetime
from openai import OpenAI
import string
import tiktoken





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

        for i, row in data.iterrows():
            if not row.isnull().any():
                if i == 0:
                    return i
                else:
                    return i -1
        return None


    def load_data_table(self, start_row):

        data = pd.DataFrame()
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

        #rename some of the columns
        expected_columns = ['Accounts', 'Period 2 values', 'Period 1 values', 'Change in values', 'Percentage change']
        print (len(data.columns))

        if len(data.columns) < len(expected_columns):
            print ('Expected columns not found in the data. Adding missing columns.')
            missing_columns = len(expected_columns) - len(data.columns)
            data[expected_columns[-missing_columns:]] = np.nan
        
        #renaming some of the columns for better AI readability
        data.rename(columns={data.columns[0]: expected_columns[0], 
                     data.columns[3]: expected_columns[3], 
                     data.columns[4]: expected_columns[4]}, inplace=True)
        

        # Select specific columns
        columns_to_check = [data.columns[1], data.columns[2]]
        df_selected = data[columns_to_check]


        data['Accounts'] = data['Accounts'].apply(lambda x: str(x).lstrip().lstrip(string.digits))

        # Check if all values are zero or NaN
        if (df_selected.isna() | (df_selected == 0)).all().all():
            return None
        
        return data

    #separate out what we need from the data, by account type 
    ''''Income', 'Cost of Sales', 'Expenses', 'Other Income(Loss)','Other Expenses', 'Key KPI', 'All')'''
    def select_data(self, data, account_type):
        #titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings', 'Total Other Expenses', 'Total Other Income(Loss)']
        
        if account_type == 'All':
            return data
        else:
            data = data[data['Account type'] == account_type]

        # Create a boolean mask
        #mask = data.iloc[:, 0].isin(titles_to_keep)
        # Index the DataFrame with the mask
        #data = data[mask]
        return data
    
    
    def add_more_columns(self, data):
    # add more columns to the data

        if data is not None:

            total_income_period_1 = data.loc[data.iloc[:, 0] == 'Total Income', data.columns[1]].values[0]

            try:
                data['Percentage of sales period 1'] = data.iloc[:, 1] / total_income_period_1 * 100
            except:
                print ('Division by zero error')
                data ['Percentage of sales period 1'] = 0

            total_income_period_2 = data.loc[data.iloc[:, 0] == 'Total Income', data.columns[2]].values[0]
            data['Percentage of sales period 2'] = data.iloc[:, 2] / total_income_period_2 * 100

            data['Change in percentage of sales'] = data['Percentage of sales period 2'] - data['Percentage of sales period 1'] 

        return data


        #from data mark all the accounts that are income accounts, where account type is the type of account
    def mark_account_types(self, data, accountType):
        # Find the indices of the rows where column 1 between account type and total account type
        #todo: improve this section 
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
        data.loc[start_index:end_index, 'Account hierarchy'] = np.nan
        
        # Set 'Account type' to none for rows where 'Accounts' contains 'total'
        mask = data['Accounts'].str.contains('total', case=False)
        data.loc[mask, 'Account hierarchy'] = 'Subtotals'
        
        # Set 'Account type' to none for rows where the account is an account group
        mask2 = data.iloc[:, 1].isnull() & data.iloc[:, 2].isnull()
        data.loc[mask2, 'Account hierarchy'] = 'Account group'
        mask1 = data.iloc[start_index:end_index, 1].isnull() & data.iloc[start_index:end_index, 2].isnull()
        
        # Set 'Account type' to none for rows where numbers are subtotals of any kind
        #data.loc[mask1, 'Account type'] = np.nan
        titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings', 'Total Other Expenses', 'Total Other Income(Loss)']
        
        # Create a boolean mask
        mask = data.iloc[:, 0].isin(titles_to_keep)
        
        # Index the DataFrame with the mask
        data.loc[mask, 'Account type'] = 'Key KPI'

        return data

    #analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 
    #send to AI for human language interpretation
    def send_to_AI(self, data, prompt_file_path, industry):
        #prompt2 gves much worse results - so I think my original prompt is better
        with open(prompt_file_path, 'r') as file: 
            prompt = file.read()
        csv_text = data.to_csv(index=False)
        completion = self.client.chat.completions.create(
        model = "gpt-4-turbo-preview",#"gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data. This is from {industry} industry for more context",}
            ]
        )
        return completion.choices[0].message.content


    def main(self, insights_preference, industry):        
        #calling all the functions now 
        i = self.find_data_start() 
        data = self.clean_data(self.load_data_table(i))
        if data is None:
            return 'The file is empty or might have formatting issues. Please open the file in Excel, save it, and try again.'
        print('Data cleaned', str(datetime.now().time()))
        
        #todo: refactor this 
        data = self.mark_account_types(data, 'Income')
        data = self.mark_account_types(data, 'Cost of Sales')
        data = self.mark_account_types(data, 'Expenses')
        data = self.mark_account_types(data, 'Other Income(Loss)')
        data = self.mark_account_types(data, 'Other Expenses')

        #to delete these checks later
        print('Account types marked', str(datetime.now().time()))
        savedFilename = 'uploaded_files/cleaned_data_all_accounts' + self.filename

        print('File with all accounts saved ' + str(datetime.now().time()))
        data = self.add_more_columns(data)
        
        #print some stats 
        print('More columns added ' + str(datetime.now().time()))
 

        #select the data to send to AI based on user input 
        ''''Income', 'Cost of Sales', 'Expenses', 'Other Income(Loss)','Other Expenses', 'Key KPI', 'All')'''
        #switch statement here with 5 options for account type
        if(insights_preference == 'Income'):
            data = self.select_data(data, 'Income')
        elif(insights_preference == 'Cost of Sales'):
            data = self.select_data(data, 'Cost of Sales')
        elif(insights_preference == 'Expenses'):
            data = self.select_data(data, 'Expenses')
        elif(insights_preference == 'Other Income(Loss)'):
            data = self.select_data(data, 'Other Income(Loss)')
        elif(insights_preference == 'Other Expenses'):
            data = self.select_data(data, 'Other Expenses')
        elif(insights_preference == 'Key KPI'):
            data = self.select_data(data, 'Key KPI')
        else:
            data = self.select_data(data, 'All')

        print('Number of rows in data: ', len(data))
        print('Number of columns in data: ', len(data.columns))
        print('Data being sent to AI for analysis and interpretation ' + str(datetime.now().time()))
        
        #save the data being sent as a new file for refernce
        data.to_excel(savedFilename, index=False)
        if(insights_preference == 'All' or insights_preference == 'Key KPI'):
            prompt_file_path = 'resources/prompt.txt'
        else:
            prompt_file_path = 'resources/prompt_category.txt'

        aiResponse = None
        aiResponse = self.send_to_AI(data, prompt_file_path, industry)
        print('Data returned from AI ' + str(datetime.now().time()))
        
        #now similarly get analysis on income accounts only

        return aiResponse

