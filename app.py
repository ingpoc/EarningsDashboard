# app.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
from tabs.scraper_tab import scraper_layout, register_scraper_callbacks
from tabs.community_tab import community_layout, settings_layout, register_twitter_callbacks
from util.layout import sidebar, content, details_modal, overview_modal, ai_recommendation_modal
from tabs.ipo_tab import ipo_layout, register_ipo_callbacks
from tabs.overview_tab import register_overview_callbacks, overview_layout
from tabs.portfolio_tab import register_portfolio_callback, portfolio_layout
from tabs.stock_details_tab import stock_details_layout, register_stock_details_callbacks
from tabs.settings_tab import settings_layout, register_settings_callbacks
from tabs.notifications_tab import notifications_layout, register_notifications_callbacks
from util.utils import get_collection



import threading
import schedule
import time


# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.FLATLY,
    'https://use.fontawesome.com/releases/v5.8.1/css/all.css'
], suppress_callback_exceptions=True)
server = app.server  # For deploying on platforms like Heroku

# Register callbacks from other files
register_overview_callbacks(app)
register_portfolio_callback(app)
register_twitter_callbacks(app)
register_scraper_callbacks(app)
register_ipo_callbacks(app)
register_settings_callbacks(app)
register_notifications_callbacks(app)
register_stock_details_callbacks(app)

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        sidebar,
        html.Div(id='page-content', className='content')
    ], id='layout', className='d-flex flex-row'),
    details_modal,
    overview_modal,
    ai_recommendation_modal,
    dcc.Store(id="combined-ipo-store"),
    dcc.Store(id="dark-mode-store", data={'dark_mode': False}),
    dcc.Store(id="selected-data-store"),
], id="main-container", className="h-100")



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
        elif pathname == "/notifications":
            return notifications_layout()
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
            stock = get_collection('detailed_financials').find_one({"company_name": {'$regex': f'^{value}$', '$options': 'i'}})
            if stock:
                return f"/stock/{stock['company_name']}", ""
            else:
                return current_pathname, f"Stock '{value}' not found."
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return current_pathname, f"An error occurred during search: {str(e)}"
    return dash.no_update, dash.no_update

@app.callback(
    Output('main-container', 'className'),
    Input('dark-mode-switch', 'value')
)
def toggle_dark_mode(dark_mode):
    if dark_mode:
        return "h-100 dark-mode"
    else:
        return "h-100"

@app.callback(
    [Output('sidebar', 'className'), Output('page-content', 'className')],
    Input('sidebar-toggle', 'n_clicks'),
    [State('sidebar', 'className'), State('page-content', 'className')]
)
def toggle_sidebar(n_clicks, sidebar_class, content_class):
    if n_clicks and 'collapsed' not in sidebar_class:
        new_sidebar_class = sidebar_class + ' collapsed'
        new_content_class = content_class + ' collapsed'
    elif n_clicks and 'collapsed' in sidebar_class:
        new_sidebar_class = sidebar_class.replace(' collapsed', '')
        new_content_class = content_class.replace(' collapsed', '')
    else:
        new_sidebar_class = sidebar_class
        new_content_class = content_class
    return [new_sidebar_class, new_content_class]

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
