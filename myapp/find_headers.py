
import json
import pandas as pd
import openai


def send_dataframe_to_gpt35():
    filepath = 'PL 8 months.xlsx'
    #filepath = 'Profit and Loss Sample.xlsx'
    # Read the first 20 rows from the excel file
    df = pd.read_excel(filepath, nrows=10)
    # Convert the dataframe to a JSON string
    csv_data = df.to_csv(index=False)
    
    # Load the prompt file
    prompt = ''' You will receive top 20 rows of an accounting statment 
    
    I want you to return the contents of the header row for the actual data
    accounting in the file, as JSON. It would mostly have two to three columns at least.
    
    This should be the row that contains headers like Accounts, Date 1, Period 1, June 2020 etc. 

    Example: Input is data with some empty rows, some semi filled rows, and then 
    a row with string values like accounts, Jan 22, percentage change, difference

    Make sure you only return data from one and only one row. Do not use more than one row for the response. Pick the most appropriate row and use just that. 
    
    Response should be contents of this row. Ignore any 'unnamed columns'...
    response should be like 

    {
    "headers": ["Accounts", "Jul 2023 - Jan 2024", "Jul 2022 - Jan 2023 (PP)", "Change", "% Change"],
    }
    '''
    
    # Send the JSON data to AI for column header matching
    #openai.api_key = ''

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": csv_data}
        ]
    )
    
    # Get the response from GPT-3.5
    response = completion.choices[0].message.content
    print(response)

   
    # Convert the response JSON string to a dictionary
    headers = json.loads(response)
    df_as_list = df.head(10).values.tolist()

    max_matches = 0
    best_row = None

    # Extract the list of headers from the dictionary
    headers_list = headers["headers"]

    for index, row in enumerate(df_as_list):
        # Convert the row to a list of strings
        row_as_strings = [str(item) for item in row]
        print(row_as_strings)
        
        # Count the number of headers found in the row
        matches = sum(header in row_as_strings for header in headers_list)
        
        if matches > max_matches:
            max_matches = matches
            best_row = index

    print('Row number in the file with the most matches is', best_row)



if __name__ == "__main__":
    send_dataframe_to_gpt35()