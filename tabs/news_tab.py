#tabs/news_tab.py
import requests
import subprocess
import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dcc, html, dash_table, callback_context
import tweepy
import os

NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Set up Twitter API client


def fetch_stock_news(query="Indian stock market"):
    search_query = f"{query} stock OR share price OR financial results OR NSE OR BSE"
    url = f"https://newsapi.org/v2/everything?q={search_query}&from=2024-07-21&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    
    print(url)
    try:
        response = requests.get(url)
        response.raise_for_status()
        news_data = response.json()
        articles = news_data.get('articles', [])
        return articles
    except requests.exceptions.HTTPError as errh:
        print("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Something went wrong", err)
    return []
