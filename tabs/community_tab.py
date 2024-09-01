# Community page layout

import pandas as pd
import requests
import html
import dash_bootstrap_components as dbc
import tweepy
import os
from dash import html, callback_context
from dash.dependencies import Input, Output, State
from util.utils import  get_recommendation


TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    return_type=requests.Response,
    wait_on_rate_limit=True
)


def community_layout():
    return html.Div([
        html.H3("Community Insights"),
        dbc.Input(id='post-input', type='text', placeholder="Share your insights..."),
        html.Br(),
        dbc.Button("Post to App", id='post-button', color="primary"),
        dbc.Button("Post to Twitter", id='twitter-post-button', color="info", style={"marginLeft": "10px"}),
        dbc.Button("Delete Last Tweet", id='twitter-delete-button', color="danger", style={"marginLeft": "10px"}),
        html.Br(),
        html.Div(id='community-feed'),
        html.Div(id='twitter-response', style={'marginTop': 20})
    ])


# Settings page layout
def settings_layout():
    return html.Div([
        html.H3("Settings"),
        dbc.Row([
            dbc.Col([
                dbc.Label("API Key"),
                dbc.Input(id='api-key-input', type='text', placeholder="Enter your API key..."),
                dbc.FormText("This key is used for fetching real-time data."),
            ])
        ]),
        dbc.Button("Save Settings", id='save-settings', color="primary"),
    ])

# Twitter API error handling decorator
def twitter_api_error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
            return response.json()
        except requests.exceptions.HTTPError as errh:
            print("Http Error:", errh)
            return {"error": str(errh)}
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
            return {"error": str(errc)}
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
            return {"error": str(errt)}
        except requests.exceptions.RequestException as err:
            print("Something went wrong", err)
            return {"error": str(err)}
    return wrapper

@twitter_api_error_handler
def tweet_post(text):
    return client.create_tweet(text=text)

@twitter_api_error_handler
def tweet_delete(tweet_id):
    return client.delete_tweet(tweet_id)


# Global variable for tracking the last tweet ID
last_tweet_id = None

def register_twitter_callbacks(app):
    @app.callback(
        Output('twitter-response', 'children'),
        [Input('twitter-post-button', 'n_clicks'),
         Input('twitter-delete-button', 'n_clicks')],
        [State('post-input', 'value')]
    )
    def handle_twitter_actions(post_clicks, delete_clicks, post_content):
        global last_tweet_id  # Access the global variable
        ctx = callback_context

        if not ctx.triggered:
            return "No action taken."

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'twitter-post-button':
            if post_clicks and post_content:
                response = tweet_post(post_content)
                if 'data' in response:
                    last_tweet_id = response['data']['id']  # Store the tweet ID
                    return f"Tweet posted successfully: {last_tweet_id}"
                else:
                    return f"Failed to post tweet: {response.get('error', 'Unknown error')}"
            else:
                return "No content to post."

        elif button_id == 'twitter-delete-button':
            if delete_clicks and last_tweet_id:
                response = tweet_delete(last_tweet_id)
                if 'data' in response:
                    last_tweet_id = None  # Reset after deletion
                    return f"Tweet deleted successfully."
                else:
                    return f"Failed to delete tweet: {response.get('error', 'Unknown error')}"
            else:
                return "No tweet to delete."

        return "No action taken."
     

def register_twitter_post_callbacks(app):
    @app.callback(
        Output('twitter-share-response', 'children'),
        Input('twitter-share-button', 'n_clicks'),
        State('selected-data-store', 'data'),  # Retrieve data from dcc.Store
        State('modal-title', 'children')
    )
    def post_to_twitter(n_clicks, selected_data, company_name):
        if n_clicks:
            # selected_data is directly available here as a dict
            tweet_content = format_tweet(selected_data, company_name)
            print(tweet_content)
            
            # Post to Twitter (uncomment when ready)
            response = tweet_post(tweet_content)
            
            if 'data' in response:
                last_tweet_id = response['data']['id']  # Store the tweet ID
                return f"Tweet posted successfully: {last_tweet_id}"
            else:
                return f"Failed to post tweet: {response.get('error', 'Unknown error')}"
        
        # Return an empty string if no clicks or any other issues
        return ""


    # Callback for community posts
def register_community_callbacks(app):
    @app.callback(
        Output('community-feed', 'children'),
        [Input('post-button', 'n_clicks')],
        [State('post-input', 'value')]
    )
    def update_community_feed(n_clicks, post_content):
        if n_clicks is None or post_content is None:
            return html.Div("No posts yet.")
        
        # In a real application, you would store this in a database
        return html.Div([
            html.P(f"User posted: {post_content}"),
            html.Hr()
        ])


def format_tweet(selected_data, company_name):
    try:
        # Extract data directly from the dictionary
        report_type = selected_data.get('report_type', 'N/A')
        result_date = selected_data.get('result_date', 'N/A')

        # Valuation Metrics
        market_cap = selected_data.get('market_cap', 'N/A')
        ttm_pe = selected_data.get('ttm_pe', 'N/A')

        # Financial Performance
        revenue = selected_data.get('revenue', 'N/A')
        gross_profit = selected_data.get('gross_profit', 'N/A')
        revenue_growth = selected_data.get('revenue_growth', 'N/A')
        net_profit = selected_data.get('net_profit', 'N/A')

        # Insights
        net_profit_growth = selected_data.get('net_profit_growth', 'N/A')
        piotroski_score = selected_data.get('piotroski_score', 'N/A')

        # Formatting the tweet content
        tweet_content = f"""
📊  {company_name}*

📅 Report Type: {report_type}
🗓️ Result Date: {result_date}

💹 Valuation Metrics:
• Market Cap: {market_cap}
• TTM P/E: {ttm_pe}

📈 Financial Performance:
• Revenue: {revenue}
• Gross Profit: {gross_profit}
• Net Profit: {net_profit}

💡 Insights:
• Revenue Growth (YoY): {revenue_growth}
• Net Profit Growth (YoY): {net_profit_growth}
• Piotroski Score: {piotroski_score}

#StockAnalysis #Investing #FinancialPerformance #ValuationMetrics #Insights
        """

        return tweet_content.strip()
    except Exception as e:
        return f"Error formatting tweet: {str(e)}"




