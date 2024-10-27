import json
from pymongo import MongoClient

# Load JSON data from file
with open('symbol.json', 'r') as f:
    company_symbols = json.load(f)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Adjust the URI if necessary
db = client['stock_data']
collection = db['detailed_financials']

# Iterate over the JSON data and update the database
for company_name, symbol in company_symbols.items():
    if symbol != "Not listed":
        result = collection.update_one(
            {'company_name': company_name},
            {'$set': {'symbol': symbol}}
        )
        if result.matched_count == 0:
            print(f"No document found for company: {company_name}")
        else:
            print(f"Updated symbol for company: {company_name}")
    else:
        print(f"Symbol for company '{company_name}' is 'Not listed'. Skipping update.")

# Close the MongoDB connection
client.close()
