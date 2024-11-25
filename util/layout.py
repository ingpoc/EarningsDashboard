# util/layout.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from util.utils import fetch_stock_names
from pymongo import MongoClient

# Update the NavLinks to separate icons and labels
nav_links = [
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-chart-line"), className="nav-icon"),
            html.Span("Overview", className="sidebar-label"),
        ],
        href="/overview",
        id="overview-link",
        active="exact"
    ),
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-briefcase"), className="nav-icon"),
            html.Span("Portfolio", className="sidebar-label"),
        ],
        href="/portfolio",
        id="portfolio-link",
        active="exact"
    ),
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-search"), className="nav-icon"),
            html.Span("Scraper", className="sidebar-label"),
        ],
        href="/scraper",
        id="scraper-link",
        active="exact"
    ),
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-users"), className="nav-icon"),
            html.Span("Community", className="sidebar-label"),
        ],
        href="/community",
        id="community-link",
        active="exact"
    ),
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-rocket"), className="nav-icon"),
            html.Span("IPOs", className="sidebar-label"),
        ],
        href="/ipos",
        id="ipos-link",
        active="exact"
    ),
    dbc.NavLink(
        [
            html.Span(html.I(className="fas fa-cog"), className="nav-icon"),
            html.Span("Settings", className="sidebar-label"),
        ],
        href="/settings",
        id="settings-link",
        active="exact"
    ),
]

sidebar = html.Div([
    # Sidebar header with toggle button and optional title
    html.Div([
        dbc.Button(
            html.I(className="fas fa-bars"),
            id="sidebar-toggle",
            color="primary",
            outline=True,
            size="lg",
            className="m-2",
            style={'color': '#fff'}  # Ensure the icon is visible
        ),
        html.H2("Earnings Dashboard", className="display-6 text-primary sidebar-label"),
    ], className="sidebar-header d-flex align-items-center"),
    # Sidebar content
    html.Div([
        html.Hr(),
        dcc.Dropdown(
            id='stock-search-sidebar',
            options=[{'label': name, 'value': name} for name in fetch_stock_names()],
            placeholder="Search for a stock...",
            multi=False,
            style={'width': '100%'},
            className="mb-3"
        ),
        html.Div(id='search-feedback', className="text-danger mb-3"),
        dbc.Nav(
            nav_links,
            vertical=True,
            pills=True,
            className="mb-3"
        ),
        dbc.Switch(
            id="dark-mode-switch",
            label="Dark Mode",
            value=False,
            className="mt-auto sidebar-label"
        ),
    ], className="sidebar-content h-100 d-flex flex-column")
], id="sidebar", className="sidebar")

content = html.Div(id='page-content', className='content')

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
            dcc.Markdown(
                id='ai-recommendation-content',
                style={'whiteSpace': 'pre-wrap'},
                dangerously_allow_html=True,  # Optional
            ),
        ]),
        dbc.ModalFooter([
            dbc.Button("Refresh Analysis", id="refresh-analysis-button", className="me-2"),
            dbc.Button("Close", id="close-ai-modal")
        ])
    ],
    id="ai-recommendation-modal",
    size="lg",
)