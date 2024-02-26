import pandas as pd
import numpy as np
import requests
import json
import os
import openai
from openai import OpenAI



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
        data = pd.read_excel(self.filepath)
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
        #data['Percentage of sales period 1'] = data['Period 1 values'] / data['Total Income']

        if data is not None:

            total_income_period_1 = data.loc[data['Accounts'] == 'Total Income', 'Period 1 values'].values[0]
            
            try:
                data['Percentage of sales period 1'] = data['Period 1 values'] / total_income_period_1
            except:
                print ('Division by zero error')
                data ['Percentage of sales period 1'] = 0

            total_income_period_2 = data.loc[data['Accounts'] == 'Total Income', 'Period 2 values'].values[0]
            data['Percentage of sales period 2'] = data['Period 2 values'] / total_income_period_2

            data['Change in percentage of sales'] = data['Percentage of sales period 2'] - data['Percentage of sales period 1'] 

        return data

    # structure the data into hierarchy (accounts and sub accounts) - will do this later


    #analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 





    #send to AI for human language interpretation
    def send_to_AI(self, data):

        csv_text = data.to_csv(index=False)

        completion = self.client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": '''You are an expert in finacial analysis 
             and describe your analysis to business owners who only have rudimentary 
             financial knowledge, so you expain it to them in easy language. 
             
             Structure your analysis in a sequence thats right for profit and loss statements
             focusing only on important considerations rather than a line by line analysis. 

             Dont just reiterate numbers in human language, 
             but provide your insight as well. If there are any discrepencies in the 
             data, or things you cant explain from the data, point those out too. 
             
             Make sure to  look at all the columns for your analysis and explanation.
             
             Finally summarize your analysis especially giving insights about net profits.

             Structure your respond with headings and formating, suiteable for a business report, and 
             suitable for html rendering. Headings will be <h3> and <h4> tags.

             Headings shougld always be exactly as follows:
                - Introduction
                - Revenues
                - Costs of sales
                - Gross profit
                - Administrative costs
                - Other income and costs
                - Net profit
                - Discrepencies
                - Summary
             
             '''},
            {"role": "user", "content": f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data.",}
            ]
        )

        return completion.choices[0].message.content





    def main(self):        
        #calling all the functions now 
        i = self.find_data_start()
        data = self.clean_data(self.load_data_table(i))
        data = self.key_kpis(data)
        data = self.add_more_columns(data)
        savedFilename = 'uploaded_files/cleaned_data_' + self.filename + '.xlsx'
        data.to_excel(savedFilename, index=False)
        data = self.send_to_AI(data)

        #print (data)
        return data








