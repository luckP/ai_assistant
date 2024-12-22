import pandas as pd

# Load the CSV file
df = pd.read_csv('data.csv')

# Print summary statistics
print(df.describe())

# Check for missing values
if df.isnull().values.any():
    print("Missing Values:")
    print(df.isnull().sum())
