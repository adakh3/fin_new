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
        #filtered_df = df[df['Account type'] == account_type]

        print("Dataframe is", df.columns)
        # Filter the DataFrame based on the account_type
        if account_type == 'outliers':
            filtered_df = df[df['outliers'] == True]
        else:
            filtered_df = df[df['Account type'] == account_type]
        
        print ("Fitered dataframe is" , filtered_df.columns)
        
        # Select the desired columns
        chart_df = filtered_df.iloc[:, [0] + list(range(1, date_column_count + 1))]

        #sort values in desc order and pick top 15 only if more than 15
        chart_df = chart_df.sort_values(by=chart_df.columns[1], ascending=False) #sort by first values column
        if len(chart_df) > 15: #if more than 15 rows
            chart_df = chart_df.iloc[:15] #pick top 15 rows

        print (df.head)
        
        return chart_df
    

    def plot_diff_bar_charts(self, df, chartTitle, chartMode):
        # Prepare data for stacked bar chart
        data = []
        for i in range(len(df)):
            row_name = df.iloc[i, 0]
            values = df.iloc[i, 1:].astype(float).values
            data.append(go.Bar(name=row_name, x=df.columns[1:], 
                               y=values, 
                               marker=dict(color=self.color_palette[i % len(self.color_palette)]),
                               hovertemplate=f'<b>{row_name}</b>: %{{y}}<extra></extra>'))

        # Create figure
        fig = go.Figure(data=data)
        print('chart data is', fig.data)

        fig.update_layout(
        #barmode='stack', 
        title = chartTitle,
        dragmode = False,
        barmode = chartMode,
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
    

    #To group the bars by row instead of by column
    def plot_diff_bar_charts_by_rows(self, df, chartTitle, chartMode):
        # Prepare data for stacked bar chart
        data = []
        for column in df.columns[1:]:
            column_values = df[column].astype(float).values
            data.append(go.Bar(name=column, x=df.iloc[:, 0], 
                            y=column_values, 
                            marker=dict(color=self.color_palette[df.columns.get_loc(column) % len(self.color_palette)]),
                            hovertemplate=f'<b>{column}</b>: %{{y}}<extra></extra>'))

        # Create figure
        fig = go.Figure(data=data)
        print('chart data is', fig.data)

        fig.update_layout(
            title = chartTitle,
            dragmode = False,
            barmode = chartMode,
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
                dragmode = False,
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
    


