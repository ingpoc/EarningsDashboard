# util/analysis.py

import requests
import os
from typing import Union, List, Optional
from pymongo import MongoClient
from bson import ObjectId
from openai import OpenAI

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']

def fetch_stock_analysis(stock_input: Union[str, List[str]]) -> Optional[str]:
    """
    Fetches stock analysis from the selected AI API for a single stock or a portfolio of stocks.

    Args:
        stock_input (Union[str, List[str]]): A single stock symbol (str) or a list of stock symbols (List[str]).

    Returns:
        Optional[str]: The AI-generated analysis or None if an error occurs.
    """
    # Retrieve the selected API from the settings
    settings_doc = db['settings'].find_one({'_id': 'ai_api_selection'})
    selected_api = settings_doc.get('selected_api', 'perplexity') if settings_doc else 'perplexity'

    if selected_api == 'perplexity':
        return fetch_stock_analysis_perplexity(stock_input)
    elif selected_api == 'xai':
        return fetch_stock_analysis_xai(stock_input)
    else:
        print(f"Error: Unknown AI API selected '{selected_api}'.")
        return None


def fetch_stock_analysis_perplexity(stock_input: Union[str, List[str]]) -> Optional[str]:
    """
    Fetches stock analysis from Perplexity API.
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

def fetch_stock_analysis_xai(stock_input: Union[str, List[str]]) -> Optional[str]:
    """
    Fetches stock analysis from xAI API.
    """
    XAI_API_KEY = os.getenv("XAI_API_KEY")
    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1",
    )

    if isinstance(stock_input, str):
        stock_list = [stock_input]
    elif isinstance(stock_input, list):
        if not stock_input:
            print("Error: The stock list provided is empty.")
            return None
        stock_list = stock_input
    else:
        print("Error: Invalid input type. Please provide a stock symbol as a string or a list of stock symbols.")
        return None

    # Prepare the prompt
    if len(stock_list) == 1:
        stock_name = stock_list[0]
        prompt = f"""Provide a stock recommendation for {stock_name} in exactly 3-4 concise bullet points.
        The first 2-3 bullets should address fundamental metrics or recent news affecting the stock.
        The final bullet should clearly state whether to buy, sell, or hold the stock based on the analysis.
        Do not include any additional text or headers."""
    else:
        stocks_str = ', '.join(stock_list)
        prompt = f"""Analyze the following stocks and categorize each as "Hold," "Sell," or "Buy" based on their fundamental metrics and recent news.
        Provide the recommendations in a table format with the following columns: Stock Symbol, Recommendation, and Reason.
        Be concise and ensure accuracy.\n\nStocks:\n{stocks_str}"""

    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are Grok, an AI assistant providing stock analysis."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )

        # Corrected access to content
        analysis_content = response.choices[0].message.content.strip()
        return analysis_content

    except Exception as e:
        print(f"An error occurred while fetching analysis from xAI API: {e}")

    return None