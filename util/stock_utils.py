# util/stock_utils.py

import dash_bootstrap_components as dbc
from dash import html
from typing import Any, Tuple, Optional

def get_value_attributes(value: Any, label: str) -> Tuple[str, str, str]:
    """Helper function to determine color and icon for values"""
    color = ""
    icon = ""
    
    if value is None or str(value).strip() in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
        return "", "", "N/A"
        
    try:
        if any(term in label.lower() for term in ['growth', 'yield', 'estimates']):
            value_float = float(str(value).replace(',', '').strip('%').split(':')[-1].strip())
            if value_float > 0:
                return "text-success", "▲", str(value)
            elif value_float < 0:
                return "text-danger", "▼", str(value)
    except (ValueError, IndexError):
        pass
        
    return color, icon, str(value)

def create_info_item(label: str, value: Any, is_percentage: bool = False, 
                    is_estimate: bool = False, is_piotroski: bool = False) -> html.Div:
    color, icon, formatted_value = get_value_attributes(value, label)
    
    if is_estimate and ':' in str(value):
        value_parts = str(value).split(':', 1)
        value_component = html.Div([
            html.Span(value_parts[0] + ':'),
            html.Span(value_parts[1].strip() if len(value_parts) > 1 else '')
        ])
    else:
        value_component = f"{icon} {formatted_value}" if icon else formatted_value
        
    return html.Div([
        html.Span(label, className="stock-details-label"),
        html.Div(value_component, className=f"stock-details-value {color}")
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