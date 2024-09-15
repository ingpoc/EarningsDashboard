import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from tabs.scraper_tab import scraper_layout, register_scraper_callbacks
from tabs.community_tab import community_layout, settings_layout, register_twitter_callbacks
from util.utils import get_recommendation
from util.layout import sidebar, content, details_modal, overview_modal
from tabs.ipo_tab import ipo_layout, register_ipo_callbacks
from tabs.overview_tab import register_overview_callbacks, overview_layout
from tabs.portfolio_tab import register_portfolio_callback, portfolio_layout
from tabs.stock_details_tab import stock_details_layout

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, 'https://use.fontawesome.com/releases/v5.8.1/css/all.css'], suppress_callback_exceptions=True)

# Register callbacks from other files
register_overview_callbacks(app)
register_portfolio_callback(app)
register_twitter_callbacks(app)
register_scraper_callbacks(app)
register_ipo_callbacks(app)

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dbc.Row([
        sidebar,
        content,
        details_modal,
        overview_modal
    ], className="h-100"),
    dcc.Store(id="combined-ipo-store"),
    dcc.Store(id="dark-mode-store", data={'dark_mode': False}),
    dcc.Store(id="selected-data-store"),
], fluid=True, className="h-100", style={"backgroundColor": "#f8f9fa"})

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    try:
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
            return ipo_layout()
        elif pathname == "/settings":
            return settings_layout()
        else:
            return dbc.Container(html.Div(["404 - Page not found"], className="text-danger"), fluid=True)
    except Exception as e:
        print(f"Error loading page: {str(e)}")
        return dbc.Container(html.Div(["An error occurred while loading the page."], className="text-danger"), fluid=True)

@app.callback(
    [Output('url', 'pathname'),
     Output('search-feedback', 'children')],
    Input('stock-search-sidebar', 'value'),
    State('url', 'pathname')
)
def search_stock(value, current_pathname):
    if value:
        try:
            # Validate that the stock exists in your database
            stock = collection.find_one({"company_name": value})
            if stock:
                return f"/stock/{value}", ""
            else:
                return current_pathname, f"Stock '{value}' not found."
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return current_pathname, f"An error occurred during search: {str(e)}"
    return dash.no_update, dash.no_update

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)