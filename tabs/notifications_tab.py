# tabs/notifications_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output
from pymongo import MongoClient
import threading
import time

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']

def notifications_layout():
    return dbc.Container([
        html.H3("Notifications", className="mb-4"),
        html.Div(id="notifications-content"),
        dcc.Interval(
            id='notifications-interval',
            interval=60*1000,  # Update every minute
            n_intervals=0
        )
    ], className="py-3")

def register_notifications_callbacks(app):
    @app.callback(
        Output("notifications-content", "children"),
        Input("notifications-interval", "n_intervals")
    )
    def update_notifications(n):
        # Fetch notifications from the database
        notifications = list(db['notifications'].find().sort("timestamp", -1).limit(10))
        if not notifications:
            return html.Div("No notifications at this time.", className="text-muted")

        notifications_list = [
            dbc.ListGroupItem([
                html.Div([
                    html.Strong(noti.get('title', 'Notification')),
                    html.P(noti.get('message', ''), className="mb-0"),
                    html.Small(noti.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S'), className="text-muted")
                ])
            ])
            for noti in notifications
        ]

        return dbc.ListGroup(notifications_list)

    # Background thread to generate notifications (example implementation)
    def notification_generator():
        while True:
            settings = db['settings'].find_one({'_id': 'notifications'})
            if settings and settings.get('enabled'):
                # Example: Check for new IPOs and create a notification
                new_ipos = db['ipo_data'].find({'notified': {'$ne': True}})
                for ipo in new_ipos:
                    db['notifications'].insert_one({
                        'title': f"New IPO: {ipo['Company Name']}",
                        'message': f"{ipo['Company Name']} IPO is now open for subscription.",
                        'timestamp': time.time()
                    })
                    # Mark as notified
                    db['ipo_data'].update_one({'_id': ipo['_id']}, {'$set': {'notified': True}})
            time.sleep(60)  # Check every minute

    # Start the background thread
    threading.Thread(target=notification_generator, daemon=True).start()
