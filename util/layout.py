# util/layout.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from util.stock_utils import fetch_stock_names

# Modern Sidebar
sidebar = dbc.Col(
    [
        html.Div([
            # Logo and Title Section
            html.Div([
                html.I(className="fas fa-chart-pie fa-2x text-primary mb-2"),
                html.H2("Earnings Dashboard", className="display-6 text-primary mb-0"),
                html.P("Real-time market insights", className="text-muted small")
            ], className="text-center mb-4"),
            
            html.Hr(className="my-4"),
            
            # Enhanced Search with Feedback
            dbc.InputGroup([
                dbc.InputGroupText(html.I(className="fas fa-search")),
                dcc.Dropdown(
                    id='stock-search-sidebar',
                    options=[{'label': name, 'value': name} for name in fetch_stock_names()],
                    placeholder="Search stocks...",
                    multi=False,
                    className="border-0",
                    style={'flex': '1'}
                ),
            ], className="mb-3 shadow-sm"),
            html.Div(id='search-feedback', className="text-danger small mb-3"),
            
            # Navigation Menu
            dbc.Nav(
                [
                    dbc.NavLink(
                        [
                            html.Div([
                                html.I(className="fas fa-chart-line me-3"),
                                html.Span("Overview", className="flex-grow-1"),
                                html.I(className="fas fa-chevron-right ms-auto opacity-50 small")
                            ], className="d-flex align-items-center")
                        ],
                        href="/overview",
                        id="overview-link",
                        active="exact",
                        className="rounded-3 mb-2"
                    ),
                    dbc.NavLink(
                        [
                            html.Div([
                                html.I(className="fas fa-briefcase me-3"),
                                html.Span("Portfolio", className="flex-grow-1"),
                                html.I(className="fas fa-chevron-right ms-auto opacity-50 small")
                            ], className="d-flex align-items-center")
                        ],
                        href="/portfolio",
                        id="portfolio-link",
                        active="exact",
                        className="rounded-3 mb-2"
                    ),
                    dbc.NavLink(
                        [
                            html.Div([
                                html.I(className="fas fa-robot me-3"),
                                html.Span("Scraper", className="flex-grow-1"),
                                html.I(className="fas fa-chevron-right ms-auto opacity-50 small")
                            ], className="d-flex align-items-center")
                        ],
                        href="/scraper",
                        id="scraper-link",
                        active="exact",
                        className="rounded-3 mb-2"
                    ),
                    dbc.NavLink(
                        [
                            html.Div([
                                html.I(className="fas fa-users me-3"),
                                html.Span("Community", className="flex-grow-1"),
                                html.I(className="fas fa-chevron-right ms-auto opacity-50 small")
                            ], className="d-flex align-items-center")
                        ],
                        href="/community",
                        id="community-link",
                        active="exact",
                        className="rounded-3 mb-2"
                    ),
                    dbc.NavLink(
                        [
                            html.Div([
                                html.I(className="fas fa-rocket me-3"),
                                html.Span("IPOs", className="flex-grow-1"),
                                html.I(className="fas fa-chevron-right ms-auto opacity-50 small")
                            ], className="d-flex align-items-center")
                        ],
                        href="/ipos",
                        id="ipos-link",
                        active="exact",
                        className="rounded-3 mb-2"
                    ),
                ],
                vertical=True,
                pills=True,
                className="mb-auto nav-pills-custom"
            ),
            
            # Settings and Theme Controls
            html.Div([
                html.Hr(className="my-4"),
                dbc.NavLink(
                    [
                        html.Div([
                            html.I(className="fas fa-cog me-3"),
                            html.Span("Settings", className="flex-grow-1"),
                        ], className="d-flex align-items-center")
                    ],
                    href="/settings",
                    id="settings-link",
                    active="exact",
                    className="rounded-3 mb-3"
                ),
                dbc.Switch(
                    id="dark-mode-switch",
                    label=html.Div([
                        html.I(className="fas fa-moon me-2"),
                        "Dark Mode"
                    ], className="d-flex align-items-center"),
                    value=False,
                    className="custom-switch"
                ),
            ], className="mt-auto")
        ], className="h-100 d-flex flex-column")
    ],
    width=2,
    className="sidebar",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "280px",
        "padding": "24px",
        "transition": "all 0.3s ease",
        "zIndex": 1000,
    }
)

# Enhanced Content Area
content = dbc.Col(
    id="page-content",
    width=10,
    className="content fade-in",
    style={
        "marginLeft": "280px",  # This should match the sidebar width
        "padding": "24px",
        "minHeight": "100vh",
        "transition": "all 0.3s ease",
        "background": "linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%)"
    }
)

# Portfolio Details Modal
details_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [
                    html.I(className="fas fa-info-circle me-2"),
                    "Portfolio Details"
                ],
                className="d-flex align-items-center"
            ),
            className="border-0"
        ),
        dbc.ModalBody(
            id='details-body',
            className="px-4 py-3"
        ),
    ],
    id="details-modal",
    size="lg",
    className="modal-custom",
    style={"backdropFilter": "blur(5px)"}
)

# Overview Modal
overview_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                id='modal-title',
                className="d-flex align-items-center"
            ),
            className="border-0"
        ),
        dbc.ModalBody(
            id='overview-details-body',
            className="px-4 py-3"
        ),
    ],
    id="overview-details-modal",
    size="lg",
    className="modal-custom",
    style={"backdropFilter": "blur(5px)"}
)

# AI Recommendation Modal
ai_recommendation_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [
                    html.I(className="fas fa-brain me-2"),
                    "AI Stock Analysis"
                ],
                className="d-flex align-items-center"
            ),
            className="border-0"
        ),
        dbc.ModalBody([
            dcc.Store(id='selected-stock-symbol'),
            dcc.Store(id='selected-stock-name'),
            dbc.Row([
                dbc.Col([
                    html.Label(
                        [
                            html.I(className="fas fa-history me-2"),
                            "Analysis History"
                        ],
                        className="text-muted mb-2 d-flex align-items-center"
                    ),
                    dcc.Dropdown(
                        id='analysis-history-dropdown',
                        placeholder='Select previous analysis',
                        clearable=False,
                        className="dropdown-custom"
                    ),
                ], width=12),
            ], className='mb-4'),
            html.Div([
                dcc.Markdown(
                    id='ai-recommendation-content',
                    className="analysis-content",
                    style={
                        'whiteSpace': 'pre-wrap',
                        'backgroundColor': 'rgba(0,0,0,0.02)',
                        'padding': '20px',
                        'borderRadius': '8px',
                        'fontSize': '0.95rem',
                        'lineHeight': '1.6'
                    }
                ),
            ], className="mb-4"),
        ], className="px-4 py-3"),
        dbc.ModalFooter([
            dbc.Button(
                [
                    html.I(className="fas fa-sync-alt me-2"),
                    "Refresh Analysis"
                ],
                id="refresh-analysis-button",
                color="primary",
                className="me-2"
            ),
            dbc.Button(
                [
                    html.I(className="fas fa-times me-2"),
                    "Close"
                ],
                id="close-ai-modal",
                color="secondary"
            )
        ], className="border-0")
    ],
    id="ai-recommendation-modal",
    size="lg",
    className="modal-custom",
    style={"backdropFilter": "blur(5px)"}
)