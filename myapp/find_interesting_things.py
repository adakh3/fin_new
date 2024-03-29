import pandas as pd

class FindInterestingThings:
    def __init__(self, dataframe, original_columns, total_sales):
        self.data = dataframe
        self.original_columns = original_columns
        self.total_sales = total_sales
        self.data['outliers'] = False
        

    '''
    def find_column_outliers(self, column, account_type):
        subset = self.data[self.data['account type'] == account_type]
        mean = subset[column].mean()
        std = subset[column].std()
        self.data.loc[subset.index, 'outlier'] = subset[column].apply(lambda x: (x < mean - 2 * std) or (x > mean + 2 * std))
    '''
             
    def find_column_outliers(self, column, account_type):
        # Find the column that contains the input as a substring
        matching_columns = self.data.filter(like=column).columns
        if matching_columns is None:
            print(f"No columns found with '{column}' in their names")
            return
        # If multiple columns match, you can choose to handle it however you want.
        # Here, we'll just use the first matching column.
        column = matching_columns[0]

        #for later do this in a loop - bit for now we will stick to a single column - just for single analysis
        '''
        for column in matching_columns:
            subset = self.data[self.data['Account type'] == account_type]
            mean = subset[column].mean()
            std = subset[column].std()
            self.data.loc[subset.index, f'outliers {column}'] = subset[column].apply(lambda x: (x < mean - 1 * std) or (x > mean + 1 * std))
        '''
            
        subset = self.data[self.data['Account type'] == account_type]
        mean = subset[column].mean()
        std = subset[column].std()
        self.data.loc[subset.index, 'outliers'] = subset[column].apply(lambda x: (x < mean - 1 * std) or (x > mean + 1 * std))
        
        return self.data


    def find_patterns(self, column):
        # Implement your logic to find patterns in the specified column
        patterns = self.data[column].value_counts()
        return patterns
    

    def add_percent_sales(self) -> pd.DataFrame:
        """
        Adds a '% of Sales' column for each non-NaN column in the original data.
        """
        try:
            i = 0
            for col in self.original_columns[1:]:
                if not self.data[col].isna().all():
                    self.data[f'% of Sales {col}'] = round((self.data[col] / self.total_sales[i]) * 100,1)
                    i += 1
            return self.data
        except Exception as e:
            print('An error occurred while preparing data')
            return self.data


    def add_percent_sales_differences(self) -> pd.DataFrame:
        """
        Adds a '% Sales Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        try:
            totSalesIndex = 0
            for i, col in enumerate(self.original_columns[1:], start=1):
                if i < len(self.original_columns) - 1:  # check if there's a next column
                    next_col = self.original_columns[i+1]
                    self.data[f'Percentage of Sales Difference {col}'] = round((self.data[col]/self.total_sales[totSalesIndex] - self.data[next_col]/self.total_sales[totSalesIndex+1])*100,1)
                totSalesIndex += 1
            return self.data
        except Exception as e:
            print('An error occurred while preparing data', e)
            return self.data


    def add_differences(self) -> pd.DataFrame:
        """
        Adds a 'Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        try:
            date_columns = [col for col in self.original_columns[1:] if not self.data[col].isna().all()]

            for i in range(0, len(date_columns)-1):
                self.data[f'Difference {date_columns[i]}'] = self.data[date_columns[i]] - self.data[date_columns[i+1]]
            return self.data
        except Exception as e:
            print('An error occurred while preparing data')
            return self.data


    def add_percentage_differences(self) -> pd.DataFrame:
        """
        Adds a 'Percentage Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        try:
            date_columns = [col for col in self.original_columns[1:] if not self.data[col].isna().all()]

            for i in range(0, len(date_columns)-1):
                self.data[f'% Difference {date_columns[i]}'] = round((self.data[date_columns[i]] - self.data[date_columns[i+1]]) / self.data[date_columns[i+1]] * 100,1)
            return self.data
        except Exception as e:
            print('An error occurred while preparing data')
            return self.data
        