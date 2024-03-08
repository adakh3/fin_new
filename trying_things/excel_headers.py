import pandas as pd

# Hardcoded file path
file_path = '/Users/adnan/Desktop/python stuff/fin_analysis_django/trying_things/error file.xlsx'

# Load the Excel file into a DataFrame
df = pd.read_excel(file_path)

df = df.dropna(how='all')  # Drop rows that contain only NaN values
df = df[~df.apply(lambda row: row.astype(str).str.contains('Unnamed').any(), axis=1)]
#df = df.reset_index(drop=True)  # Reset the index of the DataFrame

header_row = df.iloc[0]  # Take the first row of the resulting DataFrame

# Print the first 5 rows before the headers
print(df.head(5))
columns_headers = df.columns
print('column headers initially are', columns_headers)

non_null_counts = df.notnull().sum(axis=1)
non_null_counts = non_null_counts[non_null_counts > 0]
avg_non_null_counts = non_null_counts.expanding().mean()
first_greater_row_index = non_null_counts[non_null_counts > avg_non_null_counts].index[0]


# Move the DataFrame to start with the identified row
df = df.iloc[first_greater_row_index-1:]

# Print the column headers

column_headers = df.iloc[first_greater_row_index].tolist()
print('the data frame head is', df.head(5))
print('column headers are', column_headers)