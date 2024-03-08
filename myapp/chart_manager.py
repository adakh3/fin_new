import pandas as pd
import plotly.express as px
import plotly.offline as opy

class ChartManager:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def create_scatter_plot(self, x: str, y: str, color: str) -> str:
        fig = px.scatter(self.df, x=x, y=y, color=color)
        plot_div = opy.plot(fig, auto_open=False, output_type='div')
        return plot_div

    def create_bar_chart(self, x: str, y: str, color: str) -> str:
        fig = px.bar(self.df, x=x, y=y, color=color)
        plot_div = opy.plot(fig, auto_open=False, output_type='div')
        return plot_div
    
    def create_line_chart(self, x: str, y: str, color: str) -> str:
        fig = px.line(self.df, x=x, y=y, color=color)
        plot_div = opy.plot(fig, auto_open=False, output_type='div')
        return plot_div