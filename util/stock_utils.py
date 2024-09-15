# util/stock_utils.py

import dash_bootstrap_components as dbc
from dash import html

def create_info_item(label, value, is_percentage=False, is_estimate=False, is_piotroski=False):
    color = ""
    icon = ""
    if is_percentage or is_estimate or 'growth' in label.lower() or label == "Net Profit Growth":
        try:
            value_float = float(value.replace(',', '').strip('%').split(':')[-1].strip())
            if value_float > 0:
                color = "text-success"
                icon = "▲"
            elif value_float < 0:
                color = "text-danger"
                icon = "▼"
        except ValueError:
            pass
    elif is_piotroski:
        try:
            value_float = float(value)
            if value_float > 5:
                color = "text-success"
                icon = "▲"
            elif value_float < 5:
                color = "text-danger"
                icon = "▼"
        except ValueError:
            pass
    
    if is_estimate:
        if "Beats" in value:
            color = "text-success"
            icon = "▲"
        elif "Missed" in value:
            color = "text-danger"
            icon = "▼"
    
    formatted_value = f"{icon} {value}" if icon else value
    
    return html.Div([
        html.Span(label, className="stock-details-label"),
        html.Span(formatted_value, className=f"stock-details-value {color}")
    ], className="stock-details-item")

def create_info_card(title, items, icon):
    return dbc.Card([
        dbc.CardHeader([
            html.I(className=f"fas {icon} me-2"),
            html.Span(title, className="h6 mb-0")
        ], className="d-flex align-items-center py-2"),
        dbc.CardBody([
            create_info_item(label, value, 
                             is_percentage='growth' in label.lower() or 'yield' in label.lower(),
                             is_estimate='estimates' in label.lower(),
                             is_piotroski='piotroski score' in label.lower())
            for label, value in items
        ], className="py-2")
    ], className="stock-details-card h-100")