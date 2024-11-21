import base64
from functools import lru_cache
import pandas as pd
import numpy as np
import re
from datetime import datetime
from util.database import DatabaseConnection
import logging
from util.ai_recommendation import process_stock_batch



# Optimize fetch_latest_quarter_data with bulk operations and caching
@lru_cache(maxsize=100)
def fetch_latest_quarter_data():
    try:
        collection = DatabaseConnection.get_collection('detailed_financials')
        portfolio_collection = DatabaseConnection.get_collection('holdings')
        
        # Bulk fetch portfolio stocks
        portfolio_stocks = set(portfolio_collection.distinct('Instrument'))
        
        # Bulk fetch all stocks with latest metrics
        pipeline = [
            {
                '$project': {
                    'company_name': 1,
                    'symbol': 1,
                    'financial_metrics': {'$slice': ['$financial_metrics', -1]},
                }
            }
        ]
        
        stocks = list(collection.aggregate(pipeline))
        
        # Prefetch AI analyses in bulk
        symbols = [stock['symbol'] for stock in stocks]
        ai_analyses = {
            doc['symbol']: doc 
            for doc in DatabaseConnection.get_collection('ai_analysis').find(
                {'symbol': {'$in': symbols}},
                sort=[('timestamp', -1)]
            )
        }
        
        # Process stocks in batches
        batch_size = 100
        stock_data = []
        
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            batch_data = process_stock_batch(
                batch, 
                portfolio_stocks, 
                ai_analyses
            )
            stock_data.extend(batch_data)
        
        df = pd.DataFrame(stock_data)
        return df.sort_values(by="result_date", ascending=False)
        
    except Exception as e:
        logging.error(f"Error fetching latest quarter data: {str(e)}")
        return pd.DataFrame()

