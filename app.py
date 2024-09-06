
import dash
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from tabs.scraper_tab import scraper_layout, register_scraper_callbacks
from tabs.community_tab import (
    community_layout,
    settings_layout,
    register_community_callbacks,
    register_twitter_callbacks,
    register_twitter_post_callbacks  
)
from util.utils import get_recommendation  

from util.layout import app_layout  # Import the layout
from tabs.ipo_tab import ipo_layout, register_ipo_callbacks
from tabs.overview_tab import register_overview_callbacks, overview_layout
from tabs.portfolio_tab import register_portfolio_callback, portfolio_layout
from tabs.stock_details_tab import stock_details_layout


# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)



# Register callbacks from other files
register_community_callbacks(app)
register_twitter_callbacks(app)
register_twitter_post_callbacks(app)  
register_scraper_callbacks(app)
register_ipo_callbacks(app)  # Register IPO callbacks
register_overview_callbacks(app)
register_portfolio_callback(app)

app.layout = app_layout



@app.callback(
    Output('recommendation-alert', 'children'),
    Input('quarter-dropdown', 'value'),
    State('url', 'pathname')
)
def update_quarter_details(selected_quarter, pathname):
    company_name = pathname.split("/stock/")[1]
    stock = collection.find_one({"company_name": company_name})
    
    if not stock:
        return "No data available."

    selected_data = next((metric for metric in stock['financial_metrics'] if metric['quarter'] == selected_quarter), None)
    
    if not selected_data:
        return "No data available for this quarter."
    
    recommendation = get_recommendation(pd.DataFrame([selected_data]))
    return f"Recommendation: {recommendation}"



# Callback to update page content
@app.callback(
    dash.dependencies.Output('page-content', 'children'),
    [dash.dependencies.Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == "/overview" or pathname == "/":
        return overview_layout()
    elif pathname.startswith("/stock/"):
        company_name = pathname.split("/stock/")[1]
        return stock_details_layout(company_name)
    elif pathname == "/portfolio":
        return portfolio_layout()
    elif pathname == "/scraper":
        return scraper_layout()
    elif pathname == "/community":
        return community_layout()
    elif pathname == "/ipos":
        return ipo_layout()  # This should now include the 'refresh-ipo-data' button
    elif pathname == "/settings":
        return settings_layout()
    return html.Div(["404 - Page not found"], className="text-danger")



@app.callback(
    Output('url', 'pathname'),
    [Input('stock-search-sidebar', 'value')]
)
def search_stock(value):
    if value:
        return f"/stock/{value}"
    return dash.no_update


# Callback for dark mode
@app.callback(
    Output('page-content', 'style'),
    [Input('dark-mode-switch', 'value')]
)
def toggle_dark_mode(dark_mode):
    return {'backgroundColor': '#222', 'color': '#ddd', 'margin-left': '16.666667%'} if dark_mode else {'backgroundColor': '#fff', 'color': '#000', 'margin-left': '16.666667%'}

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)