import pandas as pd
import numpy as np

# Load the CSV file
df = pd.read_csv('data.csv')

# Display summary statistics
print(df.describe())
