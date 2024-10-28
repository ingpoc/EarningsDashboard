# util/analysis.py

import requests
import os
from typing import Union, List, Optional

def fetch_stock_analysis(stock_input: Union[str, List[str]]) -> Optional[str]:
    """
    Fetches stock analysis from Perplexity API for a single stock or a portfolio of stocks.

    Args:
        stock_input (Union[str, List[str]]): A single stock symbol (str) or a list of stock symbols (List[str]).

    Returns:
        Optional[str]: The API response content containing stock recommendations or None if an error occurs.
    """
    api_url = 'https://api.perplexity.ai/chat/completions'
    api_key = os.getenv('PERPLEXITY_API_KEY')  # Ensure your API key is stored securely
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Determine if input is a single stock or a list of stocks
    if isinstance(stock_input, str):
        # Single Stock Analysis
        prompt = f"""Provide a stock recommendation for {stock_input} in exactly 3-4 concise bullet points. The first 2-3 bullets should address fundamental metrics or recent news affecting the stock. The final bullet should clearly state whether to buy, sell, or hold the stock based on the analysis. Do not include any additional text or headers."""
        max_tokens = 200
    elif isinstance(stock_input, list):
        # Portfolio Analysis
        if not stock_input:
            print("Error: The stock list provided is empty.")
            return None
        stock_list = ', '.join(stock_input)
        prompt = f"""
Analyze the following stocks and categorize each as "Hold," "Sell," or "Add" based on their fundamental metrics and recent news. Provide the recommendations in a table format with the following columns: Stock Symbol, Recommendation, and Reason. Be concise and ensure accuracy.

Stocks:
{stock_list}
"""
        max_tokens = 500
    else:
        print("Error: Invalid input type. Please provide a stock symbol as a string or a list of stock symbols.")
        return None

    # Configure the payload
    payload = {
        'model': 'llama-3.1-sonar-small-128k-online',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.3
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Raises HTTPError if the status is 4xx, 5xx

        # Extract the content from the response
        analysis_content = response.json()['choices'][0]['message']['content'].strip()
        return analysis_content

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred: {req_err}")
    except KeyError:
        print("Unexpected response structure. Unable to find 'choices' or 'message' in the response.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None