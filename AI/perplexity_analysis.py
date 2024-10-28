# util/analysis.py

import requests
import os

def fetch_stock_analysis(stock_name):
    api_url = 'https://api.perplexity.ai/chat/completions'
    api_key = os.getenv('PERPLEXITY_API_KEY')  # Ensure your API key is stored in an environment variable
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    prompt = f"""Provide a detailed below 700-word stock analysis for {stock_name} covering:

1. Company Overview:
   - Brief description of business model
   - Key products/services

2. Financial Performance:
   - Revenue growth (YoY and 5-year CAGR)
   - Profit margins (gross, operating, net)
   - Debt-to-equity ratio and cash position
   - Return on Equity (ROE) and Return on Assets (ROA)

3. Recent Developments:
   - Key news in last 3 months
   - Latest quarterly results highlights

4. Industry Analysis:
   - Market size and growth rate
   - Company's market share
   - Top competitors and their performance

5. Valuation Metrics:
   - Current P/E ratio vs industry average
   - PEG ratio
   - Price-to-Book (P/B) ratio
   - EV/EBITDA

6. Risks and Opportunities:
   - Top 3 risks facing the company
   - Potential growth catalysts

7. Analyst Opinions:
   - Consensus rating
   - Average price target

8. Recommendation:
   - Clear buy/hold/sell recommendation
   - Brief rationale for the recommendation"""

    payload = {
        'model': 'sonar-medium-online',
        'messages': [{'role': 'user', 'content': prompt}]
    }

    response = requests.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error fetching analysis: {response.status_code} {response.text}")
        return None
