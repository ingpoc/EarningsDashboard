import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import sys

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['stock_data']
collection = db['detailed_financials']

def scrape_estimates(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    estimates_cards = soup.select('#estVsAct > div > ul > li')
    
    for card in estimates_cards:
        company_name = card.select_one('div:nth-child(2) > h3 > a').text.strip()
        quarter = card.select_one('div:nth-child(3) > span:nth-child(1)').text.strip()
        estimates_line = card.select_one('div.EastimateCard_botTxtCen__VpdiR').text.strip()
        
        # Find the company in the database
        company_data = collection.find_one({"company_name": company_name})
        
        if company_data:
            financial_metrics = company_data.get('financial_metrics', [])
            
            # Check if the quarter matches the latest financial metric
            if financial_metrics and financial_metrics[-1].get('quarter') == quarter:
                # Update the existing financial metric
                financial_metrics[-1]['estimates'] = estimates_line
                collection.update_one(
                    {"company_name": company_name},
                    {"$set": {"financial_metrics": financial_metrics}}
                )
                print(f"Updated estimates for {company_name} - {quarter}")
            else:
                # Add a new financial metric
                new_metric = {
                    "quarter": quarter,
                    "estimates": estimates_line
                }
                financial_metrics.append(new_metric)
                collection.update_one(
                    {"company_name": company_name},
                    {"$set": {"financial_metrics": financial_metrics}}
                )
                print(f"Added new estimate for {company_name} - {quarter}")
        else:
            # Create a new company entry
            new_company = {
                "company_name": company_name,
                "financial_metrics": [{
                    "quarter": quarter,
                    "estimates": estimates_line
                }]
            }
            collection.insert_one(new_company)
            print(f"Created new entry for {company_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        scrape_estimates(url)
    else:
        print("Please provide a URL as an argument.")