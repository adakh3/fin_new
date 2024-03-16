import plotly.express as px
import plotly.graph_objects as go

class ChartManager:
    def __init__(self):
            self.config = {'displayModeBar': False}  # Configuration for all charts
            self.color_palette = [
    '#58A399', # Original Green
    '#A8CD9F', # Original Light Green
    '#E2F4C5', # Original Lightest Green
    '#83B5B3', # Brighter Teal
    '#B4D3C7', # Soft Mint
    '#F8E9A1', # Light Yellow
    '#F76C6C', # Soft Red
    '#A8DADC', # Sky Blue
    '#457B9D', # Deeper Blue
    '#F4A261', # Sandy Orange
    '#2A9D8F', # Vibrant Green
    '#E9C46A', # Mustard Yellow
    '#264653'  # Dark Slate
    ]
  # Color palette for all charts  # Color palette for all charts
        


    def create_chart_dataframe(self, df, account_type, date_column_count):
        # Get the date column count
        
        # Filter the DataFrame based on the account_type
        filtered_df = df[df['Account type'] == account_type]
        
        # Select the desired columns
        chart_df = filtered_df.iloc[:, [0] + list(range(1, date_column_count + 1))]
        
        return chart_df
    

    def plot_stacked_bar_charts(self, df, chartTitle):
        # Prepare data for stacked bar chart
        data = []
        for i in range(len(df)):
            row_name = df.iloc[i, 0]
            values = df.iloc[i, 1:].astype(float).values
            data.append(go.Bar(name=row_name, x=df.columns[1:], y=values, marker=dict(color=self.color_palette[i % len(self.color_palette)]), hoverinfo='y'))


        # Create figure
        fig = go.Figure(data=data)
        print('chart data is', fig.data)

        fig.update_layout(
        barmode='stack', 
        title = chartTitle,
        plot_bgcolor='rgba(0,0,0,0)',  # Set plot background color to transparent
        paper_bgcolor='rgba(0,0,0,0)',  # Set paper background color to transparent
        hoverlabel=dict(  # Customize hover label
                bgcolor="black",  # Background color
                font_size=16,  # Font size
                font_color="white"  # Font color
            )
    )

        print('chart layout is', fig.layout)


        # Convert the figure to HTML and return it
        return [fig.to_html(full_html=False, config = self.config)]
    
    def plot_bar_charts(self,df):
        charts = []

        for i in range(len(df)):
            values = df.iloc[i, 1:].astype(float).values

            fig = go.Figure()

            for j, value in enumerate(values):
                fig.add_trace(go.Bar(x=df.columns[1:][j:j+1], y=[value], marker=dict(color=self.color_palette[j % len(self.color_palette)]),hoverinfo='y'))

            fig.update_layout(
                title=df.iloc[i, 0],
                plot_bgcolor='rgba(0,0,0,0)',  # Set plot background color to transparent
                paper_bgcolor='rgba(0,0,0,0)',  # Set paper background color to transparent
                showlegend=False,  # Hide the legend
                hoverlabel=dict(  # Customize hover label
                    bgcolor="black",  # Background color
                    font_size=16,  # Font size
                    font_color="white"  # Font color
                )
            )

            charts.append(fig.to_html(full_html=False, config=self.config))  # Use self.config

        return charts

    '''

    def plot_bar_charts(self,df):
        charts = []

        for i in range(len(df)):
            row_name = df.iloc[i, 0]
            values = df.iloc[i, 1:].astype(float).values

            fig = px.bar(x=df.columns[1:], y=values,labels={'x': 'Columns', 'y': row_name}, color_discrete_sequence=self.color_palette)

            fig.update_layout(
            title=row_name,
            plot_bgcolor='rgba(0,0,0,0)',  # Set plot background color to transparent
            paper_bgcolor='rgba(0,0,0,0)'  # Set paper background color to transparent
            )

            charts.append(fig.to_html(full_html=False, config = self.config))

        return charts
        '''
    


