import plotly.express as px

class ChartManager:
    def __init__(self):
        pass


    def create_chart_dataframe(self, df, account_type, date_column_count):
        # Get the date column count
        
        # Filter the DataFrame based on the account_type
        filtered_df = df[df['Account type'] == account_type]
        
        # Select the desired columns
        chart_df = filtered_df.iloc[:, [0] + list(range(1, date_column_count + 1))]
        
        return chart_df
    

    def plot_charts(self,df):
        charts = []

        for i in range(1, len(df)):
            row_name = df.iloc[i, 0]
            values = df.iloc[i, 1:].astype(float).values

            fig = px.bar(x=df.columns[1:], y=values,labels={'x': 'Columns', 'y': row_name})

            fig.update_layout(title=row_name)

            charts.append(fig.to_html(full_html=False))

        return charts
