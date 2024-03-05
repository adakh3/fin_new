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

    #load the data from an excel file
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


    '''
    # clean the data 
    def clean_data(self, data):

        # remove rows with all NaNs
        data = data.dropna(axis=0, how='all')
        # remove columns with all NaNs
        data = data.dropna(axis=1, how='all')

        #rename some of the columns
        #expected_columns = ['Accounts', 'Period 2 values', 'Period 1 values', 'Change in values', 'Percentage change']

        #todo: refactor this, its based on the idea of 4 exact columns, but it should be more flexible - this depends on QB data
        if len(data.columns) < 2:
            print('Data does not contain enough columns')
            raise Exception("File does not contain valid data. Please upload a file with data.")

        #check for the column with accounts and rename it to 'Accounts', at the momenbt assuming its the first column
        if data.columns[0] != 'Accounts':
            data.rename(columns={data.columns[0]: 'Accounts'}, inplace=True)

        #Next find the date columns using self.map_date_columns and delete the rest of the columns
        column_names = [str(col) for col in data.columns] 
        column_names_str = ', '.join(column_names)
        date_columns = self.map_date_columns(column_names_str, 'resources/prompt_columns_bool.txt')
        print ('Date columns:', date_columns)
        date_columns_dict =  json.loads(date_columns)

        # Get the keys in the dictionary as a list
        keys = list(date_columns_dict.keys())
        # Initialize an empty list to store the indices
        indices = []

        # Iterate over the items in the dictionary
        for key, value in date_columns_dict.items():
            # If the value is True, add the index of the key to the list
            if value:
                indices.append(keys.index(key))
        print('Indexes where value is true:', indices)

        # Select specific columns
        print('Before columns to check')
        columns_to_check = data.iloc[:, indices]
        print('After columns to check')
        df_periods = columns_to_check
        print('After df_periods')

        # Remove leading digits from the 'Accounts' column
        data['Accounts'] = data['Accounts'].apply(lambda x: str(x).lstrip().lstrip(string.digits))
        print('before checking null columns')

        # Check if all values are zero or NaN
        if (df_periods.isna() | (df_periods == 0)).all().all():
            return None

        print('after checking null columns')
        # check if there are columns with account names - if not, throw an error 

        #remove all columns that are not date columns or the column 0
        data_mask = data.iloc[:, [0] + indices]
        data = data[data_mask.columns]  # Remove columns not in data_mask

        return data
        '''
    

    def clean_and_prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the input data by removing NaN values, renaming columns, and selecting specific columns.

        Parameters:
        data (DataFrame): The input data to be cleaned.

        Returns:
        DataFrame: The cleaned data.
        """

        # Remove rows and columns with all NaNs
        data = self.remove_nan_values(data)

        # Validate and rename columns
        data = self.validate_and_rename_columns(data)

        # Clean the 'Accounts' column
        data = self.clean_accounts_column(data)

        # Get dictionary of date columns
        date_columns_dict = self.get_date_columns_dict(data)
        self.dateColumnCount = len(date_columns_dict)

        # Get indices of columns with True values (date columns)
        indices = self.get_true_indices(date_columns_dict)

        # Get all account names from the data
        account_names = self.get_account_names(data)


        # Select and clean specific columns
        data = self.select_baseline_columns(data, indices)
        if(data is None):
            return None

        # Store original column names
        original_columns = data.columns.tolist()


        # Add more columns
        data = self.add_percent_sales(data, original_columns)
        #data = self.add_differences(data, original_columns)
        #data = self.add_percent_sales_differences(data, original_columns)

        return data

    def remove_nan_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Removes rows and columns with all NaN values from the data.

        Parameters:
        data (DataFrame): The input data.

        Returns:
        DataFrame: The data with NaN rows and columns removed.
        """
        data = data.dropna(axis=0, how='all')
        data = data.dropna(axis=1, how='all')
        return data

    def validate_and_rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validates the data has at least 2 columns and renames the first column to 'Accounts' if necessary.

        Parameters:
        data (DataFrame): The input data.

        Returns:
        DataFrame: The data with validated and renamed columns.
        """
        if len(data.columns) < 2:
            raise Exception("File does not contain valid data. Please upload a file with data.")
        if data.columns[0] != 'Accounts':
            data.rename(columns={data.columns[0]: 'Accounts'}, inplace=True)
        return data

    def get_date_columns_dict(self, data: pd.DataFrame) -> Dict[str, bool]:
        """
        Gets a dictionary of date columns from the data. True for date columns and False for non-date columns.

        Parameters:
        data (DataFrame): The input data.

        Returns:
        Dict[str, bool]: A dictionary of date columns.
        """
        column_names = [str(col) for col in data.columns] 
        column_names_str = ', '.join(column_names)
        date_columns = self.get_AI_value_match(column_names_str, 'resources/prompt_columns_bool.txt')
        return json.loads(date_columns)
    

    def get_KPI_rows(self, data: pd.DataFrame) -> pd.Series:
        """
        Gets a DataFrame of rows that match key KPIs.

        Parameters:
        data (DataFrame): The input data.

        Returns:
        pd.DataFrame: A DataFrame of rows that match key KPIs.
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


    def get_true_indices(self, date_columns_dict: Dict[str, bool]) -> List[int]:
        """
        Gets the indices of columns with True values in the date columns dictionary.

        Parameters:
        date_columns_dict (Dict[str, bool]): The date columns dictionary.

        Returns:
        List[int]: A list of indices.
        """
        keys = list(date_columns_dict.keys())
        return [keys.index(key) for key, value in date_columns_dict.items() if value]

    def select_baseline_columns(self, data: pd.DataFrame, indices: List[int]) -> pd.DataFrame:
        """
        Selects specific columns from the data based on the indices and cleans the 'Accounts' column.

        Parameters:
        data (DataFrame): The input data.
        indices (List[int]): The indices of the columns to select.

        Returns:
        DataFrame: The data with selected and cleaned columns.
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
    def select_data(self, data, account_type):

        if account_type == 'All':
            return data
        else:
            data = data[data['Account type'] == account_type]

        return data
    
    def add_percent_sales(self, data: pd.DataFrame, original_columns: List[str]) -> pd.DataFrame:
        """
        Adds a '% of Sales' column for each non-NaN column in the original data.

        Parameters:
        data (pd.DataFrame): The input data.
        original_columns (List[str]): The original column names.

        Returns:
        pd.DataFrame: The data with added '% of Sales' columns.
        """
        for col in original_columns[1:]:
            if not data[col].isna().all():
                data[f'% of Sales {col}'] = data[col] / data[col].sum()
        return data

    def add_differences(self, data: pd.DataFrame, original_columns: List[str]) -> pd.DataFrame:
        """
        Adds a 'Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.

        Parameters:
        data (pd.DataFrame): The input data.
        original_columns (List[str]): The original column names.

        Returns:
        pd.DataFrame: The data with added 'Difference' columns.
        """
        date_columns = [col for col in original_columns[1:] if not data[col].isna().all()]

        for i in range(0, len(date_columns)-1):
            data[f'Difference {date_columns[i]}'] = data[date_columns[i]] - data[date_columns[i+1]]
        return data

    
    def add_percent_sales_differences(self, data: pd.DataFrame, original_columns: List[str]) -> pd.DataFrame:
        """
        Adds a '% Sales Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.

        Parameters:
        data (pd.DataFrame): The input data.
        original_columns (List[str]): The original column names.

        Returns:
        pd.DataFrame: The data with added '% Sales Difference' columns.
        """
        non_nan_columns = [col for col in original_columns[1:] if not data[col].isna().all()]
        for i in range(0, len(non_nan_columns)-1):
            data[f'% Sales Difference {non_nan_columns[i]}'] = (data[non_nan_columns[i]] - data[non_nan_columns[i+1]]) / data[non_nan_columns[i+1]]
        return data
    
    '''
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
        
        Args:
            data (pd.DataFrame): The input data containing the accounts.
            
        Returns:
            pd.DataFrame: The data with the Key KPIs marked.
        """
        #rather than creating a mask, send first column of accounts to AI to compare against this list        
        # Create a boolean mask
        #mask = data.iloc[:, 0].isin(titles_to_keep)

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
        

    def main(self, insights_preference, industry):        
        #calling all the functions now 
        i = self.find_data_start() 

        data = self.clean_and_prepare_data(self.load_data_table(i))        
        if data is None:
            return None

        #todo: refactor this 
        data = self.mark_account_types(data, 'Income')
        data = self.mark_account_types(data, 'Cost of Sales')
        data = self.mark_account_types(data, 'Expenses')
        data = self.mark_account_types(data, 'Other Income(Loss)')
        data = self.mark_account_types(data, 'Other Expenses')
        data = self.mark_key_kpis(data)

        savedFilename = 'uploaded_files/cleaned_data_all_accounts' + self.filename

        #data = self.add_more_columns(data)
 
        #select the data to send to AI based on user input 
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

        #choose your prompt based on number of data columns 
        if self.dateColumnCount > 2:
            prompt_file_path = 'resources/prompt_time_series_anaysis.txt'
        elif self.dateColumnCount == 2:
            prompt_file_path = 'resources/prompt_simple_pl.txt'
        else:
            prompt_file_path = 'resources/prompt_comparison.txt'

        aiResponse = None
        aiResponse = self.get_AI_analysis(data, prompt_file_path, industry)
        print('Data returned from AI ' + str(datetime.now().time()))
        
        #now similarly get analysis on income accounts only

        '''
        print(self.map_date_columns(["Accounts", "Random", "July 2020 - June 2023", "June 2021", "April 2020", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Accounting", "Data", "March 2019", "May 12 2020", "February 2022", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Assets", "Expenses", "Sept 2021", "Aug 2022", "July 2023", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Liabilities", "Income", "December 2019", "November 2020", "October 2021", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Equity", "Revenue", "January 2020", "February 2021", "March 2022", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Income Statement", "Balance Sheet", "April 2023", "May 2024", "June 2025", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Profit and Loss", "Cash Flow", "October 2020", "November 2021", "December 2022", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Ledger", "Journal", "January 2022", "February 2023", "March 2024", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Debits", "Credits", "June 2020", "July 2021", "August 2022", "Changes"], 'resources/prompt_columns_bool.txt'))
        print(self.map_date_columns(["Trial Balance", "Closing Entries", "March 2021", "April 2022", "May 2023", "Changes"], 'resources/prompt_columns_bool.txt'))
        '''
    
        return aiResponse

