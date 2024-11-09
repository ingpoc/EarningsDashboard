# tabs/settings_tab.py

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']

def settings_layout():
    # Retrieve the current AI API selection from the database
    settings_doc = db['settings'].find_one({'_id': 'ai_api_selection'})
    selected_api = settings_doc.get('selected_api', 'perplexity') if settings_doc else 'perplexity'

    return dbc.Container([
        html.H3("Settings", className="mb-4"),
        html.H4("AI API Selection", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Select AI API:"),
                dbc.RadioItems(
                    id='ai-api-selection',
                    options=[
                        {'label': 'Perplexity API', 'value': 'perplexity'},
                        {'label': 'xAI API', 'value': 'xai'}
                    ],
                    value=selected_api,  # Use the stored selection
                    inline=True
                ),
            ], width=12, className="mb-3"),
        ]),
        html.Div(id="api-selection-status", className="mb-3"),
        html.Hr(),
        html.H4("Database Backup and Restore", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Backup Detailed Financials DB", id="backup-detailed-financials-button", color="primary", className="mb-2 w-100"),
                dbc.Button("Restore Detailed Financials DB", id="restore-detailed-financials-button", color="secondary", className="mb-2 w-100"),
            ], width=6),
            dbc.Col([
                dbc.Button("Backup AI Analysis DB", id="backup-ai-analysis-button", color="primary", className="mb-2 w-100"),
                dbc.Button("Restore AI Analysis DB", id="restore-ai-analysis-button", color="secondary", className="mb-2 w-100"),
            ], width=6),
        ]),
        html.Div(id="backup-restore-status", className="mt-3"),
    ], className="py-3")

def register_settings_callbacks(app):

    @app.callback(
        Output("api-selection-status", "children"),
        Input("ai-api-selection", "value")
    )
    def update_api_selection(selected_api):
        # Store the selected API in the database
        db['settings'].update_one(
            {'_id': 'ai_api_selection'},
            {'$set': {'selected_api': selected_api}},
            upsert=True
        )
        api_name = "Perplexity API" if selected_api == "perplexity" else "xAI API"
        return dbc.Alert(f"AI API switched to {api_name}.", color="info")

    @app.callback(
        Output("backup-restore-status", "children"),
        [
            Input("backup-detailed-financials-button", "n_clicks"),
            Input("backup-ai-analysis-button", "n_clicks"),
            Input("restore-detailed-financials-button", "n_clicks"),
            Input("restore-ai-analysis-button", "n_clicks"),
        ],
        prevent_initial_call=True
    )
    def handle_backup_restore(
        backup_detailed_n_clicks,
        backup_ai_n_clicks,
        restore_detailed_n_clicks,
        restore_ai_n_clicks
    ):
        ctx = dash.callback_context
        if not ctx.triggered:
            return ""

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            if button_id == "backup-detailed-financials-button":
                backup_collection('detailed_financials')
                return dbc.Alert("Detailed Financials backup completed successfully.", color="success")
            elif button_id == "backup-ai-analysis-button":
                backup_collection('ai_analysis')
                return dbc.Alert("AI Analysis backup completed successfully.", color="success")
            elif button_id == "restore-detailed-financials-button":
                restore_collection('detailed_financials')
                return dbc.Alert("Detailed Financials restore completed successfully.", color="success")
            elif button_id == "restore-ai-analysis-button":
                restore_collection('ai_analysis')
                return dbc.Alert("AI Analysis restore completed successfully.", color="success")
            else:
                return dbc.Alert("Unknown action.", color="warning")
        except Exception as e:
            return dbc.Alert(f"An error occurred: {str(e)}", color="danger")

def backup_collection(collection_name):
    """
    Backup a MongoDB collection by copying it to a backup collection.
    """
    original_collection = db[collection_name]
    backup_collection_name = f"{collection_name}_copy"
    backup_collection = db[backup_collection_name]
    
    # Drop the backup collection if it exists
    backup_collection.drop()
    
    # Perform the aggregation with $out to copy the collection
    original_collection.aggregate([
        {'$match': {}},
        {'$out': backup_collection_name}
    ])

def restore_collection(collection_name):
    """
    Restore a MongoDB collection from its backup collection.
    """
    backup_collection_name = f"{collection_name}_copy"
    original_collection = db[collection_name]
    backup_collection = db[backup_collection_name]
    
    # Check if the backup collection exists
    if backup_collection_name not in db.list_collection_names():
        raise Exception(f"Backup collection '{backup_collection_name}' does not exist.")
    
    # Drop the original collection
    original_collection.drop()
    
    # Perform the aggregation with $out to copy the backup to the original collection
    backup_collection.aggregate([
        {'$match': {}},
        {'$out': collection_name}
    ])
