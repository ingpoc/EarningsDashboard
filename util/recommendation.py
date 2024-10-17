import numpy as np
import pandas as pd
from util.utils import parse_numeric_value




def generate_stock_recommendation(data):
    """
    Generates a stock recommendation based on various financial metrics.

    Parameters:
    - data (pd.Series or dict): A dictionary or DataFrame row containing financial metrics.

    Returns:
    - str: Recommendation ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell", or "NR" for No Recommendation)
    """
    default_values = {
        'ttm_pe': 25.0,
        'pb_ratio': 2.0,
        'net_profit_growth': 0.0,
        'revenue_growth': 0.0,
        'piotroski_score': 3,
        'technicals_trend': 'NEUTRAL',
        'strengths': 0,
        'weaknesses': 0,
        'dividend_yield': 0.0,
        'sector_pe': 25.0,
        'ttm_eps': 0.0,
        'face_value': 10.0,
        'book_value': 0.0,
        'fundamental_insights': ''
    }

    # List of metrics to check for missing data
    metrics_keys = [
        'ttm_pe', 'pb_ratio', 'net_profit_growth', 'revenue_growth',
        'piotroski_score', 'technicals_trend', 'strengths', 'weaknesses',
        'dividend_yield', 'sector_pe', 'ttm_eps', 'face_value', 'book_value',
        'fundamental_insights'
    ]

    missing_metrics = 0  # Counter for missing metrics

    if isinstance(data, pd.Series) or isinstance(data, dict):
        ttm_pe = parse_numeric_value(data.get('TTM P/E', default_values['ttm_pe']))
        if np.isnan(ttm_pe):
            ttm_pe = default_values['ttm_pe']
            missing_metrics += 1

        pb_ratio = parse_numeric_value(data.get('pb_ratio', data.get('P/B Ratio', default_values['pb_ratio'])))
        if np.isnan(pb_ratio):
            pb_ratio = default_values['pb_ratio']
            missing_metrics += 1

        net_profit_growth = parse_numeric_value(
            data.get('Net Profit Growth %', default_values['net_profit_growth']), '%')
        if np.isnan(net_profit_growth):
            net_profit_growth = default_values['net_profit_growth']
            missing_metrics += 1

        revenue_growth = parse_numeric_value(
            data.get('revenue_growth', data.get('Revenue Growth', default_values['revenue_growth'])), '%')
        if np.isnan(revenue_growth):
            revenue_growth = default_values['revenue_growth']
            missing_metrics += 1

        piotroski_score = parse_numeric_value(
            data.get('piotroski_score', data.get('Piotroski Score', default_values['piotroski_score'])))
        if np.isnan(piotroski_score):
            piotroski_score = default_values['piotroski_score']
            missing_metrics += 1

        technicals_trend = data.get('technicals_trend', data.get('Technicals Trend', default_values['technicals_trend']))
        if not technicals_trend or technicals_trend in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
            technicals_trend = default_values['technicals_trend']
            missing_metrics += 1
        technicals_trend = technicals_trend.upper()

        strengths = parse_numeric_value(data.get('strengths', default_values['strengths']))
        if np.isnan(strengths):
            strengths = default_values['strengths']
            missing_metrics += 1

        weaknesses = parse_numeric_value(data.get('weaknesses', default_values['weaknesses']))
        if np.isnan(weaknesses):
            weaknesses = default_values['weaknesses']
            missing_metrics += 1

        dividend_yield = parse_numeric_value(
            data.get('dividend_yield', data.get('Dividend Yield', default_values['dividend_yield'])))
        if np.isnan(dividend_yield):
            dividend_yield = default_values['dividend_yield']
            missing_metrics += 1

        sector_pe = parse_numeric_value(
            data.get('sector_pe', data.get('Sector P/E', default_values['sector_pe'])))
        if np.isnan(sector_pe):
            sector_pe = default_values['sector_pe']
            missing_metrics += 1

        ttm_eps = parse_numeric_value(
            data.get('ttm_eps', data.get('TTM EPS', default_values['ttm_eps'])))
        if np.isnan(ttm_eps):
            ttm_eps = default_values['ttm_eps']
            missing_metrics += 1

        face_value = parse_numeric_value(
            data.get('face_value', data.get('Face Value', default_values['face_value'])))
        if np.isnan(face_value):
            face_value = default_values['face_value']
            missing_metrics += 1

        book_value = parse_numeric_value(
            data.get('book_value', data.get('Book Value', default_values['book_value'])))
        if np.isnan(book_value):
            book_value = default_values['book_value']
            missing_metrics += 1

        fundamental_insights = data.get('fundamental_insights', data.get('Fundamental Insights', default_values['fundamental_insights']))
        if not fundamental_insights or fundamental_insights in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
            fundamental_insights = default_values['fundamental_insights']
            missing_metrics += 1
    else:
        return "Invalid data format"

    # Set a threshold for missing metrics
    total_metrics = len(metrics_keys)
    missing_threshold = total_metrics * 0.3  # Adjust threshold as needed (e.g., 30% missing data)

    if missing_metrics > missing_threshold:
        return "NR"  # No Recommendation due to insufficient data

    # Define weights for each criterion
    weights = {
        'ttm_pe': 1.5,
        'pb_ratio': 1.0,
        'net_profit_growth': 2.0,
        'revenue_growth': 2.0,
        'piotroski_score': 1.5,
        'technicals_trend': 1.0,
        'strengths_vs_weaknesses': 1.0,
        'dividend_yield': 0.5,
        'ttm_eps': 1.0,
        'face_value': 0.5,
        'book_value_vs_price': 1.0,
        'fundamental_insights': 1.0
    }

    # Initialize total score and maximum possible score
    total_score = 0
    max_score = sum([abs(weight) for weight in weights.values()])

    # Scoring logic with weights

    # TTM P/E Ratio
    if ttm_pe < sector_pe and ttm_pe > 0:
        total_score += weights['ttm_pe']
    elif ttm_pe > sector_pe:
        total_score -= weights['ttm_pe']

    # P/B Ratio
    if pb_ratio < 1.5 and pb_ratio > 0:
        total_score += weights['pb_ratio']
    elif pb_ratio > 3:
        total_score -= weights['pb_ratio']

    # Net Profit Growth %
    if net_profit_growth > 0:
        total_score += weights['net_profit_growth'] * np.clip(net_profit_growth / 100, 0, 1)
    elif net_profit_growth < 0:
        total_score -= weights['net_profit_growth'] * np.clip(-net_profit_growth / 100, 0, 1)

    # Revenue Growth %
    if revenue_growth > 0:
        total_score += weights['revenue_growth'] * np.clip(revenue_growth / 100, 0, 1)
    elif revenue_growth < 0:
        total_score -= weights['revenue_growth'] * np.clip(-revenue_growth / 100, 0, 1)

    # Piotroski Score
    if piotroski_score >= 7:
        total_score += weights['piotroski_score']
    elif piotroski_score <= 3:
        total_score -= weights['piotroski_score']

    # Technicals Trend
    if technicals_trend in ['VERY BULLISH', 'BULLISH']:
        total_score += weights['technicals_trend']
    elif technicals_trend in ['BEARISH', 'VERY BEARISH']:
        total_score -= weights['technicals_trend']

    # Strengths vs Weaknesses
    if strengths + weaknesses > 0:
        sw_ratio = (strengths - weaknesses) / (strengths + weaknesses)
        total_score += weights['strengths_vs_weaknesses'] * sw_ratio

    # Dividend Yield
    if dividend_yield > 1:
        total_score += weights['dividend_yield']
    elif dividend_yield == 0:
        total_score -= weights['dividend_yield']

    # TTM EPS
    if ttm_eps > 0:
        total_score += weights['ttm_eps']
    else:
        total_score -= weights['ttm_eps']

    # Face Value
    if face_value >= 10:
        total_score += weights['face_value']
    else:
        total_score -= weights['face_value']

    # Book Value vs Current Price
    current_price = parse_numeric_value(data.get('LTP', default_values.get('current_price', 0.0)))
    if np.isnan(current_price) or current_price == 0:
        current_price = default_values.get('current_price', 0.0)
        missing_metrics += 1  # Increment missing metrics if current price is missing
        if missing_metrics > missing_threshold:
            return "NR"
    if book_value > 0 and current_price > 0:
        bv_cp_ratio = (book_value - current_price) / current_price
        total_score += weights['book_value_vs_price'] * np.clip(bv_cp_ratio, -1, 1)

    # Fundamental Insights (Qualitative Assessment)
    if fundamental_insights and isinstance(fundamental_insights, str):
        if 'strong performer' in fundamental_insights.lower():
            total_score += weights['fundamental_insights']
        elif 'mid range performer' in fundamental_insights.lower() or 'mid-range performer' in fundamental_insights.lower():
            total_score += 0  # Neutral
        elif 'neutral' in fundamental_insights.lower():
            total_score += 0  # Neutral
        else:
            total_score -= weights['fundamental_insights']

    # Normalize total score to a scale between -1 and 1
    normalized_score = total_score / max_score

    # Determine recommendation based on normalized score
    if normalized_score >= 0.5:
        return "Strong Buy"
    elif normalized_score >= 0.1:
        return "Buy"
    elif normalized_score <= -0.5:
        return "Strong Sell"
    elif normalized_score <= -0.1:
        return "Sell"
    else:
        return "Hold"


