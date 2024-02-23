import pandas as pd
import numpy as np


''' Overall separate out key KPIs, revenues, COGS, costs, other income and costs --- 
one by one send these all to GPT-4 to get insights and predictions 
then get a summary of all the insights and predictions
'''



#load the data from an excel file 
def find_data_start(file_path):
    data = pd.read_excel(file_path)
    for i, row in data.iterrows():
        if not row.isnull().any():
            if i == 0:
                return i
            else:
                return i -1
    return None




def load_data_table(file_path, start_row):
    start_row = find_data_start(file_path)
    if start_row is not None:
        data = pd.read_excel(file_path, skiprows=range(start_row))
    else:
        data = pd.DataFrame()
    return data


# clean the data 
def clean_data(data):

    # remove rows with all NaNs
    data = data.dropna(axis=0, how='all')
    # remove columns with all NaNs
    data = data.dropna(axis=1, how='all')


     # print basic information about the data
    print("Shape of the data: ", data.shape)
    print("Column names: ", data.columns)
    print("Number of null values in each column: ", data.isnull().sum())
    print("Data types of each column: ", data.dtypes)
    print("Summary of the data: ")
    print(data.describe(include='all'))
    print(data.iloc[:,0])

    
    return data


def key_kpis(data):
    titles_to_keep = ['Total Income', 'Total Cost of Sales', 'Gross Profit', 'Total Expenses', 'Net Earnings']

    # Create a boolean mask
    mask = data.iloc[:, 0].isin(titles_to_keep)

    # Index the DataFrame with the mask
    data = data[mask]

    return data






# structure the data into hierarchy (accounts and sub accounts)





#analyse the data starting with revenues, gross proits, net profits and other KPIs, and then details 





    
#calling all the functions now 
i = find_data_start('Profit and Loss Sample.xlsx')
data = clean_data(load_data_table('Profit and Loss Sample.xlsx', i))
data = key_kpis(data)
data.to_excel('cleaned_data.xlsx', index=False)







