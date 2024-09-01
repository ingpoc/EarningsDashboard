# layout.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from util.utils import fetch_stock_names
from pymongo import MongoClient

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']

# Modal for displaying portfolio stock details
details_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Portfolio Stock Details")),
        dbc.ModalBody(id='details-body'),
    ],
    id="details-modal",
    size="lg",
)

# Modal for displaying stock details from the overview table
overview_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle(id='modal-title')),
        dbc.ModalBody(id='overview-details-body'),
    ],
    id="overview-details-modal",
    size="lg",
)

# Sidebar layout
sidebar = dbc.Col(
    [
        html.H2("Earnings Dashboard", className="display-4"),
        html.Hr(),
        dcc.Dropdown(
            id='stock-search-sidebar',
            options=[{'label': name, 'value': name} for name in fetch_stock_names(collection)],
            placeholder="Search for a stock...",
            multi=False,
            style={'width': '100%'}
        ),
        html.Br(),
        dbc.Nav(
            [
                dbc.NavLink([html.I(className="fas fa-chart-line mr-2"), "Overview"], href="/overview", id="overview-link"),
                dbc.NavLink([html.I(className="fas fa-briefcase mr-2"), "Portfolio"], href="/portfolio", id="portfolio-link"),
                dbc.NavLink([html.I(className="fas fa-search mr-2"), "Scraper"], href="/scraper", id="scraper-link"),
                dbc.NavLink([html.I(className="fas fa-users mr-2"), "Community"], href="/community", id="community-link"),
                dbc.NavLink([html.I(className="fas fa-rocket mr-2"), "IPOs"], href="/ipos", id="ipos-link"),
                dbc.NavLink([html.I(className="fas fa-cog mr-2"), "Settings"], href="/settings", id="settings-link"),
            ],
            vertical=True,
            pills=True,
        ),
        dbc.Switch(id="dark-mode-switch", label="Dark Mode", value=False),
    ],
    width=2,
    style={"height": "100vh", "position": "fixed", "background-color": "#f8f9fa"}
)

# Content layout
content = dbc.Col(id="page-content", width=10, style={"margin-left": "16.666667%", "padding": "20px"})

# App layout
app_layout = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        dbc.Row(
            [
                sidebar,
                content,
                details_modal,
                overview_modal
            ]
        ),
        # Global stores
        dcc.Store(id="combined-ipo-store"),
        dcc.Store(id="dark-mode-store"),
    ],
    fluid=True,
    style={"background-color": "#f0f2f5"}
)