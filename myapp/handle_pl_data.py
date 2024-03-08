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

''' Overall separate out key KPIs, revenues, COGS, costs, other income and costs --- 
one by one send these all to GPT-4 to get insights and predictions 
then get a summary of all the insights and predictions
'''

class HandlePLData:

    client = OpenAI()
    openai.api_key = os.getenv('OPENAI_API_KEY')
    dateColumnCount = 0
    total_sales = []
    original_columns = []

    def __init__(self, filename):
        self.filepath = 'uploaded_files/' + filename
        self.filename = filename

    #load the data from an excel file 
    def find_data_start(self, data):

        headers = self.data_headers_from_ai ('resources/find_headers_prompt.txt')

        row_number = self.get_file_header_row (headers)

        return row_number

        '''
        #data = pd.read_excel(self.filepath)
        print ('find data start', data)


        #data = data.reset_index(drop=True)
        for i, row in data.iterrows():
            print('row data', data.iloc[i])
            if not row.isnull().any():
                if i == 0:
                    return i
                else:
                    return i -1
        return None
        '''

    #load the data from an excel file
    def load_data_table(self, start_row):

        #data = pd.read_excel(self.filepath)
        if start_row is not None:
            data = pd.read_excel(self.filepath, skiprows=range(start_row+1))
            #data = data.iloc[start_row:]
            print('columns are', data.columns.tolist())

        else:
            data = None

        if len(data.shape) < 1:
            raise Exception("File does not contain data. Please upload a file with valid P&L data.")
            
        
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
        self.dateColumnCount = len(date_columns_dict)
        if self.dateColumnCount == 0:
            raise Exception("File does not contain any valid accounting periods. Please upload a file with valid P&L data.")
        

        # Get indices of columns with True values (date columns)
        indices = self.get_true_indices(date_columns_dict)

        # Select and clean specific columns
        data = self.select_baseline_columns(data, indices)
        if(data is None):
            return None
        
        print('Baseline columns selected and cleaned ' + str(datetime.now().time()))

        # Store original column names
        self.original_columns = data.columns.tolist()

        return data


    def remove_nan_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Removes rows and columns with all NaN values from the data.
        """
        data = data.dropna(axis=0, how='all')
        data = data.dropna(axis=1, how='all')
        return data


    def validate_and_rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validates the data has at least 2 columns and renames the first column to 'Accounts' if necessary.
        """
        if data.columns[0] != 'Accounts':
            data.rename(columns={data.columns[0]: 'Accounts'}, inplace=True)
        return data


    def get_date_columns_dict(self, data: pd.DataFrame) -> Dict[str, bool]:
        """
        Gets a dictionary of date columns from the data. True for date columns and False for non-date columns.
        """
        column_names = [str(col) for col in data.columns] 
        column_names_str = ', '.join(column_names)
        date_columns = self.get_AI_value_match(column_names_str, 'resources/prompt_columns_bool.txt')
        return json.loads(date_columns)
    

    def get_KPI_rows(self, data: pd.DataFrame) -> pd.Series:
        """
        Gets a DataFrame of rows that match key KPIs.
        """
        account_names = [str(name) for name in data.iloc[:, 0]]
        account_names_str = ', '.join(account_names)
        KPI_matches = self.get_AI_value_match(account_names_str, 'resources/prompt_account_kpis.txt')
        KPI_matches_dict = json.loads(KPI_matches)

        # Get a list of all account names that match KPIs (non-null values)
        matched_accounts = [value for value in KPI_matches_dict.values() if value is not None]

        # Create a data mask for rows with account names in matched_accounts
        data_mask = data.iloc[:, 0].isin(matched_accounts)

        return data_mask
    
    def save_total_sales(self, data):

        total_sales_row = data[data['Account type'] == 'Key KPI'].iloc[0]
        total_sales = total_sales_row.iloc[1:].tolist()
        return total_sales


    def get_true_indices(self, date_columns_dict: Dict[str, bool]) -> List[int]:
        """
        Gets the indices of columns with True values in the date columns dictionary.
        """
        keys = list(date_columns_dict.keys())
        return [keys.index(key) for key, value in date_columns_dict.items() if value]

    def select_baseline_columns(self, data: pd.DataFrame, indices: List[int]) -> pd.DataFrame:
        """
        Selects specific columns from the data based on the indices and cleans the 'Accounts' column.
        """
        dataDates = data.iloc[:, indices]

        if (dataDates.isna() | (dataDates == 0)).all().all():
            return None
        data_mask = data.iloc[:, [0] + indices]
        return data[data_mask.columns]    


    def clean_accounts_column(self, data: pd.DataFrame) -> pd.DataFrame:
        data['Accounts'] = data['Accounts'].apply(lambda x: str(x).lstrip().lstrip(string.digits))
        return data


    #separate out what we need from the data, by account type 
    #''''Income', 'Cost of Sales', 'Expenses', 'Other Income(Loss)','Other Expenses', 'Key KPI', 'All')'''
    def select_data(self, data, account_types):
        if account_types == 'All':
            return data
        else:
            data = data[data['Account type'].isin(account_types)]
        return data
        
    '''
    def select_data(self, data, account_type):

        if account_type == 'All':
            return data
        else:
            data = data[data['Account type'] == account_type]

        return data
    '''

    def add_percent_sales(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a '% of Sales' column for each non-NaN column in the original data.
        """
        i = 0
        for col in self.original_columns[1:]:
            if not data[col].isna().all():
                data[f'% of Sales {col}'] = data[col] / self.total_sales[i]
                i += 1
        return data

    def add_differences(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a 'Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        date_columns = [col for col in self.original_columns[1:] if not data[col].isna().all()]

        for i in range(0, len(date_columns)-1):
            data[f'Difference {date_columns[i]}'] = data[date_columns[i]] - data[date_columns[i+1]]
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
        
        #mask1 = data.iloc[start_index:end_index, 1].isnull() & data.iloc[start_index:end_index, 2].isnull()
        # Set 'Account type' Key KPI where the account title is in the list
        #titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings', 'Total Other Expenses', 'Total Other Income(Loss)']
        

        return data
    
    def mark_key_kpis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Marks the Key KPIs in the data by comparing the first column of accounts against a predefined list.
        """
        kpiMask = self.get_KPI_rows(data)
        
        # Index the DataFrame with the mask
        data.loc[kpiMask, 'Account type'] = 'Key KPI'

        return data

    #analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 
    #send to AI for human language interpretation
    def get_AI_analysis(self, data, prompt_file_path, industry):
        #prompt2 gves much worse results - so I think my original prompt is better
        with open(prompt_file_path, 'r') as file: 
            prompt = file.read()
        csv_text = data.to_csv(index=False)
        completion = self.client.chat.completions.create(
        model = "gpt-4-turbo-preview",#"gpt-3.5-turbo",
        seed=50,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Here is a CSV dataset:\n{csv_text}\nNow, perform some analysis on this data. This is from {industry} industry for more context",}
            ]
        )
        return completion.choices[0].message.content


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

    #sends columns to GPT 3.5 to map to a set of tags that I give it
    #returns a dictionary with indexes for accounts and date columns 
    def get_AI_value_match(self, values, prompt_file_path):
        with open(prompt_file_path, 'r') as file: 
            prompt = file.read()
        data_string = values
        #data_string = columns.to_csv(index=False)
        completion = self.client.chat.completions.create(
        model = "gpt-3.5-turbo",
        seed=50,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Here is a CSV dataset:\n{data_string}\n",}
            ]
        )
        return completion.choices[0].message.content
        

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
            
    '''***** NEW FUNCTION ***** TO TEST ****  '''

    def data_headers_from_ai(self, prompt_file_path):

        # Read the first 10 rows from the excel file
        df = pd.read_excel(self.filepath, nrows=10)

        # Convert the dataframe to a JSON string
        csv_data = df.to_csv(index=False)
        
        # Load the prompt file
        with open(prompt_file_path, 'r') as file: 
            prompt = file.read()
        
        # Send the JSON data to AI for column header matching
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": csv_data}
            ]
        )
        
        # Get the response from AI
        response = completion.choices[0].message.content
        return response
    
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

        for index, row in enumerate(df_as_list):
            # Convert the row to a list of strings
            row_as_strings = [str(item) for item in row]
            print('Headers rows found are:', row_as_strings)
            
            # Count the number of headers found in the row
            matches = sum(header in row_as_strings for header in headers_list)
            
            if matches > max_matches:
                max_matches = matches
                best_row = index

        print('Row number in the file with the most matches is', best_row)

        return best_row



    def main(self, insights_preference, industry):

        try:
            self.file_content_check()   
        except Exception as e:
            raise ValueError(str(e)) from e
        
        df = pd.read_excel(self.filepath)
        
        #calling all the functions now 
        i = self.find_data_start(df) 
        if (i is None):
            raise Exception("File does not contain valid data. Please upload a file with valid P&L data.")

        data = self.load_data_table(i)

        print('Data loaded ' + str(datetime.now().time()))

        data = self.clean_and_prepare_data(data)        
        if data is None:
            raise Exception ('File does not contain valid data. Try opening your file in excel, saving it and then uploading it again.')
        
        print('Data cleaned and prepared ' + str(datetime.now().time()))
        
        #todo: refactor this 
        data = self.mark_account_types(data, 'Income')
        data = self.mark_account_types(data, 'Cost of Sales')
        data = self.mark_account_types(data, 'Expenses')
        data = self.mark_account_types(data, 'Other Income(Loss)')
        data = self.mark_account_types(data, 'Other Expenses')
        data = self.mark_key_kpis(data)

        print('Data marked ' + str(datetime.now().time()))

        self.total_sales = self.save_total_sales(data)

        print('Total sales saved ' + str(datetime.now().time()))
        print('Total sales are', self.total_sales)

        #todo: Maybe remove this - or add emphasis in the prompt
        data = self.add_differences(data)
        print('Differences added ' + str(datetime.now().time()))
        
        data = self.add_percent_sales(data)
        print('Percent sales differences added ' + str(datetime.now().time()))
 
        #select the data to send to AI based on user input 
        if(insights_preference == 'Income'):
            data = self.select_data(data, ['Income'])
        elif(insights_preference == 'Cost of Sales'):
            data = self.select_data(data, ['Cost of Sales'])
        elif(insights_preference == 'Expenses'):
            data = self.select_data(data, ['Expenses'])
        elif(insights_preference == 'Other Income(Loss)'):
            data = self.select_data(data, ['Other Income(Loss)'])
        elif(insights_preference == 'Other Expenses'):
            data = self.select_data(data, ['Other Expenses'])
        elif(insights_preference == 'Key KPI'):
            data = self.select_data(data, ['Key KPI'])
        else:
            data = self.select_data(data, 'All')

        print('Number of rows in data: ', len(data))
        print('Number of columns in data: ', len(data.columns))

        savedFilename = 'uploaded_files/cleaned_' + self.filename
        #save the data being sent as a new file for refernce
        data.to_excel(savedFilename, index=False)


        #choose your prompt based on number of data columns 
        if(insights_preference == 'All' or insights_preference == 'Key KPI'):
            if self.dateColumnCount > 2:
                prompt_file_path = 'resources/pl_timeseries_prompt.txt'
            elif self.dateColumnCount == 2:
                prompt_file_path = 'resources/pl_simple_prompt.txt'
            else:
                prompt_file_path = 'resources/pl_comparison_prompt.txt'
        else:
            prompt_file_path = 'resources/pl_category_prompt.txt'

        print('Data being sent to AI for analysis and interpretation ' + str(datetime.now().time()))

        aiResponse = None
        aiResponse = self.get_AI_analysis(data, prompt_file_path, industry)

        print('Data returned from AI ' + str(datetime.now().time()))
        
    
        return aiResponse

