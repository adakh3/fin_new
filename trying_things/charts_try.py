import pandas as pd
import plotly.express as px

# Create a DataFrame
df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [10, 15, 7, 10, 15, 7],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
})

# Create a scatter plot
fig = px.bar(df, x="Fruit", y="Amount", color="City")

# Show the plot
fig.show()


