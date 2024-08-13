import pandas as pd
import numpy as np
import requests
import json
import os
import openai
from datetime import datetime
from openai import OpenAI
import string
import json
from typing import List, Dict
from .chart_manager import ChartManager
from .find_interesting_things import FindInterestingThings
import anthropic
import tiktoken
from dotenv import load_dotenv
from .quickbooks.quickbooks_integrator import QuickbooksIntegrator
from .quickbooks.quickbooks_auth import QuickbooksAuth
from django.conf import settings


''' Overall separate out key KPIs, revenues, COGS, costs, other income and costs --- 
one by one send these all to GPT-4 to get insights and predictions 
then get a summary of all the insights and predictions
'''

class HandlePLData:



    def __init__(self, filename):
        self.filepath = 'uploaded_files/' + filename
        self.filename = filename
        self.aiModel = "gpt-4o-mini"

        self.client = OpenAI()
        load_dotenv()  # take environment variables from .env.
        openai.api_key = os.getenv('OPENAI_API_KEY')

        self.dateColumnCount = 0
        self.total_sales = []
        self.original_columns = []
        self.chart_manager = ChartManager()
        self.charts = None

        '''
        #Quickbooks sample code 
        self.qbAuth = QuickbooksAuth()
        #todo: store this refresh token somewhere in the db and the realm
        self.qbrefreshToken = 'AB11723717905KEc1VyGQV7atitZvz58PLqSfMDXNszjTHsTcJ'
        self.qbRelamID = '9341452098469139'
        self.qbIntegrator = QuickbooksIntegrator(self.qbrefreshToken, self.qbRelamID)
        self.customers = self.qbIntegrator.getCustomers()
        #pl for period 1
        self.qbPl1 = self.qbIntegrator.getReport(reportName='ProfitAndLoss')
        #pl for period 2
        self.qbPl2 = self.qbIntegrator.getReport(reportName='ProfitAndLoss')
        #budgeted PL for period 1
        self.qbBudgetPl = self.qbIntegrator.getBudget() #todo: this is not working - fix it

        self.qbTb = self.qbIntegrator.getReport(reportName='TrialBalance')

        #add the PL and budget to a self dataframe
        '''
            
    #load the data from an excel file 
    def find_data_start(self, data, row_number):
        try:
            headers = self.data_headers_from_ai('resources/find_headers_prompt.txt')
            #row_number = row_number - 2 #self.get_file_header_row(headers)
            row_number = self.get_file_header_row(headers)
            
            return row_number
        except Exception as e:
            print("Error finding data in the file")
            return None

    #load the data from an excel file
    def load_data_table(self, start_row):

        try:
            if start_row is not None:
                data = pd.read_excel(self.filepath, skiprows=range(start_row+1))
                #data = data.iloc[start_row:]
                print('columns are', data.columns.tolist())

            else:
                data = None

            if len(data.shape) < 1:
                raise Exception("File does not contain data. Please upload a file with valid P&L data.")
            
        except Exception as e:
            print("An error occurred while loading the data")
            data = None
        
        return data
    

    def clean_and_prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the input data by removing NaN values, renaming columns, and selecting specific columns.
        """

        # Remove rows and columns with all NaNs
        data = self.remove_nan_values(data)

        # Validate and rename columns
        data = self.validate_and_rename_columns(data)
        print('Data validated and renamed ' + str(datetime.now().time()))

        # Clean the 'Accounts' column
        data = self.clean_accounts_column(data)
        print('Accounts column cleaned ' + str(datetime.now().time()))

        # Get dictionary of date columns
        date_columns_dict = self.get_date_columns_dict(data)
        # Remove key-value pairs where value is 'false'
        #date_columns_dict = {key: value for key, value in date_columns_dict.items() if value}
        #self.dateColumnCount = len(date_columns_dict)
        
        # Get indices of columns with True values (date columns)
        indices = self.get_true_indices(date_columns_dict)
        self.dateColumnCount = len(indices)
        if self.dateColumnCount == 0:
            raise Exception("File does not contain any valid accounting periods. Make sure you have provided the correct row number.")


        # Select and clean specific columns
        data = self.select_baseline_columns(data, indices)
        if data is None:
            return None

        print('Baseline columns selected and cleaned ' + str(datetime.now().time()))

        # Store original column names
        self.original_columns = data.columns.tolist()

        return data


    def remove_nan_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Removes rows and columns with all NaN values from the data.
        """
        try:
            data = data.dropna(axis=0, how='all')
            data = data.dropna(axis=1, how='all')
        except Exception as e:
            print(f"An error occurred while cleaning the data")
        return data


    def validate_and_rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validates the data has at least 2 columns and renames the first column to 'Accounts' if necessary.
        """
        try:
            if data.columns[0] != 'Accounts':
                data.rename(columns={data.columns[0]: 'Accounts'}, inplace=True)
        except Exception as e:
            print('An error occered while preparing data')
        return data


    def get_date_columns_dict(self, data: pd.DataFrame) -> Dict[str, bool]:
        """
        Gets a dictionary of date columns from the data. True for date columns and False for non-date columns.
        """
        try:
            #column_names = [str(col) for col in data.columns] 
            column_names = [str(col).replace(',', ' ') for col in data.columns]
            column_names_str = ', '.join(column_names)
            date_columns = self.get_AI_value_match(column_names_str, 'resources/prompt_columns_bool.txt')
            return json.loads(date_columns)
        except Exception as e:
            print('An error occered while preparing data')
            return {}


    def get_KPI_rows(self, data: pd.DataFrame) -> pd.Series:
        """
        Gets a DataFrame of rows that match key KPIs.
        """
        try:
            account_names = [str(name) for name in data.iloc[:, 0]]
            account_names_str = ', '.join(account_names)
            KPI_matches = self.get_AI_value_match(account_names_str, 'resources/prompt_account_kpis.txt')
            KPI_matches_dict = json.loads(KPI_matches)

            # Get a list of all account names that match KPIs (non-null values)
            matched_accounts = [value for value in KPI_matches_dict.values() if value is not None]

            # Create a data mask for rows with account names in matched_accounts
            data_mask = data.iloc[:, 0].isin(matched_accounts)

            return data_mask
        except Exception as e:
            print('An error occered while preparing data')
            return pd.Series([])


    def save_total_sales(self, data):
        try:
            total_sales_row = data[data['Account type'] == 'Key KPI'].iloc[0]
            total_sales = total_sales_row.iloc[1:].tolist()
            return total_sales
        except Exception as e:
            print('An error occered while preparing data')
            return []


    def get_true_indices(self, date_columns_dict: Dict[str, bool]) -> List[int]:
        """
        Gets the indices of columns with True values in the date columns dictionary.
        """
        try:
            keys = list(date_columns_dict.keys())
            return [keys.index(key) for key, value in date_columns_dict.items() if value]
        except Exception as e:
            print('An error occered while preparing data')
            return []


    def select_baseline_columns(self, data: pd.DataFrame, indices: List[int]) -> pd.DataFrame:
        """
        Selects specific columns from the data based on the indices and cleans the 'Accounts' column.
        """
        try:
            dataDates = data.iloc[:, indices]

            if (dataDates.isna() | (dataDates == 0)).all().all():
                return None
            
            for col in dataDates.columns:
                dataDates[col] = dataDates[col].apply(lambda x: f'{x:,.2f}' if x >= 0 else f'({abs(x):,.2f})')

            data_mask = data.iloc[:, [0] + indices]
            return data[data_mask.columns]
        except Exception as e:
            print('An error occered while preparing data')
            return None


    def clean_accounts_column(self, data: pd.DataFrame) -> pd.DataFrame:
        try:
            data['Accounts'] = data['Accounts'].apply(lambda x: str(x).lstrip().lstrip(string.digits))
            return data
        except Exception as e:
            print('An error occered while preparing data')
            return data


    #separate out what we need from the data, by account type 
    #''''Income', 'Cost of Sales', 'Expenses', 'Other Income(Loss)','Other Expenses', 'Key KPI', 'All')'''
    def select_data(self, data, account_types):
        try:
            if account_types == ['Key KPI']:
                data2 = data.groupby('Account type').apply(lambda x: x.sort_values(x.columns[1], ascending=False).head(10)).reset_index(drop=True)
                data = data[data['Account type'].isin(account_types) | (data['outliers'] == True)]
                data = pd.concat([data, data2]).drop_duplicates()
                return data
            else:
                data = data[data['Account type'].isin(account_types)]
                dataSorted = data.sort_values(data.columns[1], ascending=False).head(20)
                dataOutliers = data[(data['outliers'] == True) & (~data.index.isin(dataSorted.index))]
                data = pd.concat([dataSorted, dataOutliers])
            return data
        except Exception as e:
            print('An error occered while preparing data')
            return data


    '''
    #do not use this function at the moment 
    def add_percent_sales_differences(self, data: pd.DataFrame, original_columns: List[str]) -> pd.DataFrame:
        """
        Adds a '% Sales Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        non_nan_columns = [col for col in original_columns[1:] if not data[col].isna().all()]
        for i in range(0, len(non_nan_columns)-1):
            data[f'% Sales Difference {non_nan_columns[i]}'] = (data[non_nan_columns[i]] - data[non_nan_columns[i+1]]) / data[non_nan_columns[i+1]]
        return data
        '''

        #from data mark all the accounts that are income accounts, where account type is the type of account
    def mark_account_types(self, data, accountType):
        # Find the indices of the rows where column 1 between account type and total account type
        #todo: improve this section 
        #data = data.loc[~data.index.duplicated(keep='first')]
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
        if(accountType == 'Other Income'):
            data.loc[start_index:end_index, 'Account type'] = 'Income'
        elif( accountType == 'Other Expenses'):
            data.loc[start_index:end_index, 'Account type'] = 'Expenses'
        else:
            data.loc[start_index:end_index, 'Account type'] = accountType
            data.loc[start_index:end_index, 'Account hierarchy'] = np.nan
        
        # Set 'Account type' to none for rows where 'Accounts' contains 'total'
        mask = data['Accounts'].str.contains('total', case=False)
        data.loc[mask, 'Account hierarchy'] = 'Subtotals'
        data.loc[mask, 'Account type'] = np.nan

        
        # Set 'Account type' to none for rows where the account is an account group
        mask2 = data.iloc[:, 1].isnull() & data.iloc[:, 2].isnull()
        data.loc[mask2, 'Account hierarchy'] = 'Account group'
        data.loc[mask2, 'Account type'] = np.nan
        
        return data
    
    def mark_key_kpis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Marks the Key KPIs in the data by comparing the first column of accounts against a predefined list.
        """
        kpiMask = self.get_KPI_rows(data)
        
        # Index the DataFrame with the mask
        data.loc[kpiMask, 'Account type'] = 'Key KPI'

        return data


    def count_tokens(self, text, model):
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding.encode(text)
        num_tokens = len(encoding.encode(text))
        return num_tokens

    #analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 
    #send to AI for human language interpretation
    def get_openai_analysis(self, data, prompt_file_path, industry, additionalInfo, aiModel):
        #prompt2 gves much worse results - so I think my original prompt is better
        try:
            with open(prompt_file_path, 'r') as file: 
                prompt = file.read()
            csv_text = data.to_csv(index=False)
            userMessage = f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data. The company is from {industry} industry, and there is additional context in {additionalInfo} - use these in your analysis as well"
            totalText = prompt + userMessage
            tokens = self.count_tokens(totalText, aiModel)
            print("Total prompt tokens are", self.count_tokens(prompt, aiModel))
            print("Total user message tokens are", self.count_tokens(userMessage, aiModel))
            print ("Total input costs is", tokens * 10 / 1000000 )
        
        
            completion = self.client.chat.completions.create(
                model = aiModel,
                seed=50,
                #max_tokens=750,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": userMessage ,}
                ]
            )

            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error occurred during AI analysis")
            return None
        

    def get_anthropic_analysis(self, data, prompt_file_path, industry,additionalInfo, aiModel):
        try:
            with open(prompt_file_path, 'r') as file: 
                prompt = file.read()
            csv_text = data.to_csv(index=False)

            client = anthropic.Anthropic(
            # defaults to os.environ.get("ANTHROPIC_API_KEY")
            api_key=os.getenv('ANTHROPIC_API_KEY'),)
            message = client.messages.create(
                model=aiModel,
                max_tokens=1500,
                system = prompt,
                messages=[
                    {"role": "user", "content": f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data. The company is from {industry} industry, and there is additional context in {additionalInfo} - use these in your analysis as well"}
                ]
            )
            print(message.content[0].text)
            return message.content[0].text
        except Exception as e:
            print("Error occurred during AI analysis")
            print("Error is:", e)
            return None
        

    #get a list of column headers from the data - call this on cleaned data
    def get_column_headers(self, data):
        return data.columns.tolist()
    

    #get all the accounts names from the data
    def get_account_names(self, data):
        first_column = data.iloc[:, 0]
        # Filter rows where the first column contains some strings
        rows_with_strings = data[first_column.str.contains(r'\S')]

        # Define the account names to look for
        account_names = ['revenue', 'sales', 'income', 'gross profit', 'net income', 'net revenue', 'expenses', 'cost of sales', 'cost of goods sold', 'other income', 'other expenses']

        # Check if any of the account names are substrings of the strings in the first column
        #if not any(first_column.str.lower().str.contains(name) for name in account_names):
        if not any(first_column.str.lower().str.contains(name).any() for name in account_names):
            raise Exception('File does not seem to contain valid P&L data. Please upload a file with valid P&L data.')
        


        return rows_with_strings

    #sends columns to GPT to map to a set of tags that I give it
    #returns a dictionary with indexes for accounts and date columns 
    def get_AI_value_match(self, values, prompt_file_path):
        try:
            with open(prompt_file_path, 'r') as file: 
                prompt = file.read()
            data_string = values
            #data_string = columns.to_csv(index=False)
            completion = self.client.chat.completions.create(
            model =  self.aiModel, #"gpt-4o-mini",#"gpt-3.5-turbo",
            seed=50,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Here is a CSV dataset:\n{data_string}\n",}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"An error occurred during AI analysis")
            return None
        

    def file_content_check(self):
        # Read the file into a pandas DataFrame
        df = pd.read_excel(self.filepath)

        # Check if the file is emptyß
        if df.empty:
            raise Exception('File does not seem to contain any data. Try opening your file in excel, saving it and then uploading it again.')
        
        if len(df.shape) < 2:
            raise Exception("File does not contain enough data. Please upload a file with valid P&L data.")


        # Check if there are more than 12 date columns
        if len(df.shape) > 15:
            raise Exception('Please upload a file with a maximum of 12 periods for comaparison.')
            
        return True
            
    #
    def data_headers_from_ai(self, prompt_file_path):
        try:
            # Read the first 10 rows from the excel file
            df = pd.read_excel(self.filepath, nrows=10)

            # Convert the dataframe to a JSON string
            csv_data = df.to_csv(index=False)
            
            # Load the prompt file
            with open(prompt_file_path, 'r') as file: 
                prompt = file.read()
            
            # Send the JSON data to AI for column header matching
            completion = openai.chat.completions.create(
                model= self.aiModel,
                seed=50,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": csv_data}
                ]
            )
            
            # Get the response from AI
            response = completion.choices[0].message.content
            print ("Headers response from AI is:", response)
            return response
        except Exception as e:
            print("An error occurred during AI analysis. Please try agian.")
            return None
    
    def get_file_header_row(self, column_names):

        max_matches = 0
        best_row = None

        # Read the first 10 rows from the excel file
        df = pd.read_excel(self.filepath, nrows=10)
        df_as_list = df.head(10).values.tolist()
   
        # Convert the response JSON string to a dictionary
        headers = json.loads(column_names)
        # Extract the list of headers from the dictionary
        headers_list = headers["headers"]
        print('Headers list is:', headers_list)

        for index, row in enumerate(df_as_list):
            # Convert the row to a list of strings
            row_as_strings = [str(item) for item in row]
            
            # Count the number of headers found in the row
            matches = sum(header in row_as_strings for header in headers_list)
            
            if matches > max_matches:
                max_matches = matches
                best_row = index

        print('Row number in the file with the most matches is', best_row)

        return best_row


    def main(self, insights_preference, industry, additionalInfo, row_number):

        try:
            self.file_content_check()   
        except Exception as e:
            raise ValueError(str(e)) from e
        
        df = pd.read_excel(self.filepath)
        
        #calling all the functions now 
        i = self.find_data_start(df, row_number) 
        if (i is None):
            raise Exception("File does not contain valid data. Please upload a file with valid P&L data.")

        data = self.load_data_table(i)

        print('Data loaded ' + str(datetime.now().time()))

        data = self.clean_and_prepare_data(data)
        if data is None:
            raise Exception ('File does not contain valid data. Try opening your file in excel, saving it and then uploading it again.')
        
        data['outliers'] = False
        print('Data cleaned and prepared ' + str(datetime.now().time()))
        
        #todo: refactor this 
        data = self.mark_account_types(data, 'Income')
        data = self.mark_account_types(data, 'Cost of Sales')
        data = self.mark_account_types(data, 'Expenses')
        data = self.mark_account_types(data, 'Other Income')
        data = self.mark_account_types(data, 'Other Expenses')
        data = self.mark_key_kpis(data)

        print('Data marked ' + str(datetime.now().time()))

        self.total_sales = self.save_total_sales(data)

        print('Total sales saved ' + str(datetime.now().time()))
        print('Total sales are', self.total_sales)


        #if its a comparison only of two periods, find outliers in the data
        if(self.dateColumnCount == 2):
            #find and add more analysis
            analyser = FindInterestingThings(data, self.original_columns, self.total_sales)
            data = analyser.add_differences()
            data = analyser.add_percent_sales()
            data = analyser.add_percentage_differences()
            data = analyser.add_percent_sales_differences()

            data = analyser.find_column_outliers('% Difference','Income')
            data = analyser.find_column_outliers('Percentage of Sales Difference', 'Cost of Sales')
            data = analyser.find_column_outliers('% Difference','Expenses')
            data = analyser.find_column_outliers('% Difference','Key KPI')

 
        #select the data based on user input 
        if(insights_preference == 'Income'):
            data = self.select_data(data, ['Income'])#here as well we should be able to send a list perhaps
        elif(insights_preference == 'Cost of Sales'):
            data = self.select_data(data, ['Cost of Sales'])#here we should be able to send a list of values 
        elif(insights_preference == 'Expenses'):
            data = self.select_data(data, ['Expenses'])
        else:
            data = data = self.select_data(data, ['Key KPI'])
            #data = data
        
 

        #data ['outliers'] = False

        #get some KPI charts before adding anything else 
        if(insights_preference == 'Income'):
            charts_df = self.chart_manager.create_chart_dataframe(data,'Income', self.dateColumnCount)
            self.charts = self.chart_manager.plot_diff_bar_charts(charts_df, 'Top Revenue Accounts', 'stack')
            #add outliers column back by joining with data on accounts
            charts_df = pd.merge(charts_df, data[['Accounts', 'outliers']], on='Accounts', how='left')
            charts_df = self.chart_manager.create_chart_dataframe(charts_df,'outliers', self.dateColumnCount)
            if(not charts_df.empty):
                chart_html = self.chart_manager.plot_diff_bar_charts_by_rows(charts_df, 'Signifcant Outliers', 'group')[0]
                self.charts.append(chart_html)            

        elif(insights_preference == 'Cost of Sales'):
            charts_df = self.chart_manager.create_chart_dataframe(data,'Cost of Sales', self.dateColumnCount)
            self.charts = self.chart_manager.plot_diff_bar_charts(charts_df, 'Top Cost of Sales Accounts', 'stack' )
            #add outliers column back by joining with data on accounts
            charts_df = pd.merge(charts_df, data[['Accounts', 'outliers']], on='Accounts', how='left')
            charts_df = self.chart_manager.create_chart_dataframe(charts_df,'outliers', self.dateColumnCount)   
            if(not charts_df.empty):
                chart_html = self.chart_manager.plot_diff_bar_charts_by_rows(charts_df, 'Significant Outliers', 'group')[0]
                self.charts.append(chart_html)            

        elif(insights_preference == 'Expenses'):
            charts_df = self.chart_manager.create_chart_dataframe(data,'Expenses', self.dateColumnCount)
            self.charts = self.chart_manager.plot_diff_bar_charts(charts_df, 'Top Expense Accounts', 'stack' )
            #add outliers column back by joining with data on accounts
            charts_df = pd.merge(charts_df, data[['Accounts', 'outliers']], on='Accounts', how='left')
            charts_df = self.chart_manager.create_chart_dataframe(charts_df,'outliers', self.dateColumnCount)
            if(not charts_df.empty):
                chart_html = self.chart_manager.plot_diff_bar_charts_by_rows(charts_df, 'Significant Outliers', 'group')[0]
                self.charts.append(chart_html)             

        else: #if its a general P&L analyis
            charts_df = self.chart_manager.create_chart_dataframe(data,'Key KPI', self.dateColumnCount)
            self.charts = self.chart_manager.plot_diff_bar_charts_by_rows(charts_df, 'Key KPIs', 'group')    
            #add an outliers chart
            charts_df = self.chart_manager.create_chart_dataframe(data,'outliers', self.dateColumnCount)
            if(not charts_df.empty):
                chart_html = self.chart_manager.plot_diff_bar_charts_by_rows(charts_df, 'Significant Outliers', 'group')[0]
                self.charts.append(chart_html)


        print('content for charts is:',charts_df)

        print('Outliers analysis done ' + str(datetime.now().time()))
        
        print('Number of rows in data: ', len(data))
        print('Number of columns in data: ', len(data.columns))

        savedFilename = 'uploaded_files/cleaned_' + self.filename
        #save the data being sent as a new file for refernce
        data.to_excel(savedFilename, index=False)


        #choose your prompt based on number of data columns 
        if(insights_preference == 'All' or insights_preference == 'Key KPI'):
            if self.dateColumnCount > 2:
                prompt_file_path =  'resources/pl_founder_prompt.txt' #'resources/pl_simple_prompt.txt'
            elif self.dateColumnCount == 2:
                prompt_file_path = 'resources/pl_founder_prompt.txt' #'resources/pl_simple_prompt.txt'
            else:
                prompt_file_path = 'resources/pl_founder_prompt.txt' #'resources/pl_simple_prompt.txt'
        else:
            prompt_file_path = 'resources/pl_founder_prompt.txt' #'resources/pl_simple_prompt.txt'

        print('Data being sent to AI for analysis and interpretation ' + str(datetime.now().time()))

        aiResponse = None
        aiResponse = self.get_openai_analysis(data, prompt_file_path, industry, additionalInfo, self.aiModel)#"gpt-3.5-turbo"  
        #aiResponse = self.get_anthropic_analysis(data, prompt_file_path, industry,additionalInfo,"claude-3-sonnet-20240229")#"claude-3-haiku-20240307"  

        print('Data returned from AI ' + str(datetime.now().time()))
        
        return aiResponse
