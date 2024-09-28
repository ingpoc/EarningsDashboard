# tabs/settings_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from pymongo import MongoClient

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']

def settings_layout():
    return dbc.Container([
        html.H3("Settings", className="mb-4"),
        dbc.FormGroup([
            dbc.Label("Moneycontrol Username", html_for="mc-username"),
            dbc.Input(id="mc-username", placeholder="Enter your Moneycontrol username", type="text"),
        ]),
        dbc.FormGroup([
            dbc.Label("Moneycontrol Password", html_for="mc-password"),
            dbc.Input(id="mc-password", placeholder="Enter your Moneycontrol password", type="password"),
        ]),
        dbc.Button("Save Credentials", id="save-credentials-button", color="primary", className="mt-3"),
        html.Div(id="save-credentials-response", className="mt-3"),
        html.Hr(),
        dbc.FormGroup([
            dbc.Checkbox(
                id="enable-notifications",
                className="form-check-input",
                checked=False
            ),
            dbc.Label(
                "Enable Notifications",
                html_for="enable-notifications",
                className="form-check-label",
            ),
        ]),
        html.Div(id="notifications-status", className="mt-3"),
    ], className="py-3")

def register_settings_callbacks(app):
    @app.callback(
        Output("save-credentials-response", "children"),
        Input("save-credentials-button", "n_clicks"),
        State("mc-username", "value"),
        State("mc-password", "value")
    )
    def save_credentials(n_clicks, username, password):
        if n_clicks:
            if username and password:
                # Store credentials securely in the database
                db['settings'].update_one(
                    {'_id': 'moneycontrol_credentials'},
                    {'$set': {'username': username, 'password': password}},
                    upsert=True
                )
                return dbc.Alert("Credentials saved successfully!", color="success")
            else:
                return dbc.Alert("Please enter both username and password.", color="danger")
        return ""

    @app.callback(
        Output("notifications-status", "children"),
        Input("enable-notifications", "checked")
    )
    def toggle_notifications(checked):
        # Update notification settings in the database
        db['settings'].update_one(
            {'_id': 'notifications'},
            {'$set': {'enabled': checked}},
            upsert=True
        )
        status = "enabled" if checked else "disabled"
        return dbc.Alert(f"Notifications {status}.", color="info")
