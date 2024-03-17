import pandas as pd

class FindInterestingThings:
    def __init__(self, dataframe, original_columns, date_columns, total_sales):
        self.dataframe = dataframe
        self.original_columns = original_columns
        self.date_columns = date_columns
        self.total_sales = total_sales
        self.dataframe['outliers'] = False
        

    #find outliers in comparison or time series            
    def find_column_outliers(self, column):
        mean = self.dataframe[column].mean()
        std = self.dataframe[column].std()
        self.dataframe['outlier'] = self.dataframe[column].apply(lambda x: (x < mean - 2 * std) or (x > mean + 2 * std))
        #find important patters in time series - eg growth etc 
        
    
    def find_patterns(self, column):
        # Implement your logic to find patterns in the specified column
        patterns = self.dataframe[column].value_counts()
        return patterns
    

    def add_percent_sales(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a '% of Sales' column for each non-NaN column in the original data.
        """
        try:
            i = 0
            for col in self.original_columns[1:]:
                if not data[col].isna().all():
                    data[f'% of Sales {col}'] = data[col] / self.total_sales[i]
                    i += 1
            return data
        except Exception as e:
            print('An error occurred while preparing data')
            return data


    def add_differences(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a 'Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        try:
            date_columns = [col for col in self.original_columns[1:] if not data[col].isna().all()]

            for i in range(0, len(date_columns)-1):
                data[f'Difference {date_columns[i]}'] = data[date_columns[i]] - data[date_columns[i+1]]
            return data
        except Exception as e:
            print('An error occurred while preparing data')
            return data


    def add_percentage_differences(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a 'Percentage Difference' column for each non-NaN column in the original data, starting from the second non-NaN column.
        """
        try:
            date_columns = [col for col in self.original_columns[1:] if not data[col].isna().all()]

            for i in range(0, len(date_columns)-1):
                data[f'Percentage Difference {date_columns[i]}'] = (data[date_columns[i]] - data[date_columns[i+1]]) / data[date_columns[i+1]] * 100
            return data
        except Exception as e:
            print('An error occurred while preparing data')
            return data
        


    '''
    # Example usage
    data = {'Name': ['John', 'Jane', 'Mike', 'Emily', 'David'],
            'Age': [25, 30, 35, 40, 45],
            'Salary': [50000, 60000, 70000, 80000, 90000]}
    df = pd.DataFrame(data)

    finder = FindInterestingThings(df)
    outliers = finder.find_outliers('Salary')
    patterns = finder.find_patterns('Age')

    print("Outliers:")
    print(outliers)

    print("\nPatterns:")
    print(patterns)
    '''