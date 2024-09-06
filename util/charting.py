import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from util.utils import get_stock_symbol

def create_market_summary_chart():
    indices = ['S&P 500', 'NASDAQ', 'DOW']
    values = [4200, 14000, 34000]
    changes = [2.1, 1.5, 1.8]
    
    fig = go.Figure(data=[
        go.Bar(name='Value', x=indices, y=values),
        go.Bar(name='Change %', x=indices, y=changes)
    ])
    fig.update_layout(barmode='group', title='Market Summary', title_x=0.5)
    return fig

def create_sector_performance_chart():
    sectors = ['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy']
    performance = [5.2, 3.1, 2.5, 1.8, -0.5]
    
    fig = px.bar(x=sectors, y=performance, title='Sector Performance', color=performance)
    fig.update_layout(title_x=0.5)
    return fig

def create_financial_metrics_chart(df):
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()
    if 'revenue' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['revenue'], mode='lines+markers', name='Revenue'))
    if 'gross_profit' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['gross_profit'], mode='lines+markers', name='Gross Profit'))
    if 'net_profit' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['net_profit'], mode='lines+markers', name='Net Profit'))
    if 'dividend_yield' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['dividend_yield'], mode='lines+markers', name='Dividend Yield', yaxis='y2'))

    # Update layout to correctly handle dual y-axes
    fig.update_layout(
        title='Financial Metrics Over Time',
        xaxis_title='Quarter',
        yaxis=dict(
            title='Amount',
        ),
        yaxis2=dict(
            title='Dividend Yield (%)',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig




def create_stock_price_chart(company_name):
    symbol = get_stock_symbol(company_name)
    if not symbol:
        return go.Figure()  # Return an empty figure if symbol is not found

    stock = yf.Ticker(symbol)
    hist = stock.history(period="1y")
    
    if hist.empty:
        return go.Figure()  # Return an empty figure if no data is available

    fig = go.Figure(data=[go.Candlestick(x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'])])
    fig.update_layout(title=f'{company_name} Stock Price - Past Year', xaxis_rangeslider_visible=False, title_x=0.5)
    return fig


