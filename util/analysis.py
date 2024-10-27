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
    
    prompt = f"""Analyze {stock_name} and provide Stock recommendation. Be very concise in your response
    Use latest data. Prioritize accuracy and relevance."""

    payload = {
        'model': 'llama-3.1-sonar-small-128k-online',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 500,
    }

    response = requests.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error fetching analysis: {response.status_code} {response.text}")
        return None
