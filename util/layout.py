# util/layout.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from util.utils import fetch_stock_names
from pymongo import MongoClient

# Sidebar layout
sidebar = dbc.Col(
    [
        html.Div([
            html.H2("Earnings Dashboard", className="display-6 text-primary"),
            html.Hr(),
            dcc.Dropdown(
                id='stock-search-sidebar',
                options=[{'label': name, 'value': name} for name in fetch_stock_names()],
                placeholder="Search for a stock...",
                multi=False,
                style={'width': '100%'},
                className="mb-3"
            ),
            html.Div(id='search-feedback', className="text-danger mb-3"),  # New feedback div
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-chart-line me-2"), "Overview"], href="/overview", id="overview-link", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-briefcase me-2"), "Portfolio"], href="/portfolio", id="portfolio-link", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-search me-2"), "Scraper"], href="/scraper", id="scraper-link", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-users me-2"), "Community"], href="/community", id="community-link", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-rocket me-2"), "IPOs"], href="/ipos", id="ipos-link", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-cog me-2"), "Settings"], href="/settings", id="settings-link", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            dbc.Switch(
                id="dark-mode-switch",
                label="Dark Mode",
                value=False,
                className="mt-auto"
            ),
        ], className="h-100 d-flex flex-column")
    ],
    width=2,
    className="sidebar bg-light",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16.666667%",
        "padding": "20px",
        "boxShadow": "2px 0 5px rgba(0,0,0,0.1)"
    }
)

content = dbc.Col(
    id="page-content",
    width=10,
    className="content",
    style={"marginLeft": "16.666667%", "padding": "20px"}
)

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

# Modal for AI Recommendation
ai_recommendation_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("AI Stock Analysis")),
        dbc.ModalBody([
            dcc.Store(id='selected-stock-symbol'),
            dcc.Store(id='selected-stock-name'),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id='analysis-history-dropdown',
                        placeholder='Select previous analysis',
                        clearable=False,
                    ),
                ], width=12),
            ], className='mb-3'),
            html.Div(id='ai-recommendation-content'),
        ]),
        dbc.ModalFooter([
            dbc.Button("Refresh Analysis", id="refresh-analysis-button", className="me-2"),
            dbc.Button("Close", id="close-ai-modal")
        ])
    ],
    id="ai-recommendation-modal",
    size="lg",
)