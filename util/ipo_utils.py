import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['stock_data']
ipo_collection = db['ipo_data']


def get_combined_ipo_data(from_db=True):
    logger.info(f"get_combined_ipo_data called with from_db={from_db}")
    try:
        if from_db:
            return get_ipo_data_from_db()
        else:
            return fetch_and_store_ipo_data()
    except Exception as e:
        logger.error(f"Error in get_combined_ipo_data: {str(e)}")
        raise

def get_ipo_data_from_db():
    logger.info("Attempting to get IPO data from database")
    try:
        ipo_data = list(ipo_collection.find({}, {'_id': 0}))
        logger.info(f"Retrieved {len(ipo_data)} records from database")
        if not ipo_data:
            logger.info("No data found in database, fetching fresh data")
            return fetch_and_store_ipo_data()
        
        df = pd.DataFrame(ipo_data)
        upcoming_ipos = df[df['category'] == 'Upcoming'].sort_values('Open')
        current_ipos = df[df['category'] == 'Current'].sort_values('Close')
        closed_ipos = df[df['category'] == 'Closed'].sort_values('Close', ascending=False)

        # Limit closed IPOs to 3 Main and 3 SME
        closed_main = closed_ipos[closed_ipos['IPO Type'] == 'Main'].head(3)
        closed_sme = closed_ipos[closed_ipos['IPO Type'] == 'SME'].head(3)
        closed_ipos = pd.concat([closed_main, closed_sme], ignore_index=True)

        result = {
            'upcoming': upcoming_ipos,
            'current': current_ipos,
            'closed': closed_ipos
        }
        logger.info(f"Returning data from DB: Upcoming: {len(result['upcoming'])}, Current: {len(result['current'])}, Closed: {len(result['closed'])}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving data from database: {str(e)}")
        raise

def fetch_and_store_ipo_data():
    logger.info("Fetching fresh IPO data")
    try:
        mainboard_df = fetch_ipo_data('mainboard')
        sme_df = fetch_ipo_data('sme')

        combined_df = pd.concat([mainboard_df, sme_df], ignore_index=True)
        combined_df['category'] = combined_df.apply(categorize_ipo, axis=1)

        logger.info(f"Fetched total of {len(combined_df)} IPO records")

        # Store in database
        ipo_collection.delete_many({})
        ipo_collection.insert_many(combined_df.to_dict('records'))
        logger.info(f"Stored {len(combined_df)} IPO records in database")

        upcoming_ipos = combined_df[combined_df['category'] == 'Upcoming'].sort_values('Open')
        current_ipos = combined_df[combined_df['category'] == 'Current'].sort_values('Close')
        closed_ipos = combined_df[combined_df['category'] == 'Closed'].sort_values('Close', ascending=False)

        closed_main = closed_ipos[closed_ipos['IPO Type'] == 'Main'].head(3)
        closed_sme = closed_ipos[closed_ipos['IPO Type'] == 'SME'].head(3)
        closed_ipos = pd.concat([closed_main, closed_sme], ignore_index=True)

        result = {
            'upcoming': upcoming_ipos,
            'current': current_ipos,
            'closed': closed_ipos
        }
        logger.info(f"Returning fresh data: Upcoming: {len(result['upcoming'])}, Current: {len(result['current'])}, Closed: {len(result['closed'])}")
        return result
    except Exception as e:
        logger.error(f"Error fetching and storing IPO data: {str(e)}")
        raise


def fetch_ipo_data(ipo_type='mainboard'):
    logger.info(f"Fetching IPO data for type: {ipo_type}")
    if ipo_type == 'mainboard':
        url = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp"
    elif ipo_type == 'sme':
        url = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp?a=sme"
    else:
        raise ValueError("Invalid IPO type. Choose 'mainboard' or 'sme'.")

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', class_='table table-sm table-striped')

        if not table:
            return pd.DataFrame()

        headers = ['Company Name', 'Open', 'Close', 'Status']
        rows = []
        for tr in table.find_all('tr')[1:]:  # Skip the header row
            tds = tr.find_all('td')
            if len(tds) >= 4:
                company_name = tds[0].text.strip()
                open_date = tds[1].text.strip()
                close_date = tds[2].text.strip()
                status = tds[3].text.strip()
                rows.append([company_name, open_date, close_date, status])

        df = pd.DataFrame(rows, columns=headers)
        df['IPO Type'] = 'Main' if ipo_type == 'mainboard' else 'SME'

        return df
    except Exception as e:
        print(f"Error fetching IPO data: {e}")
        return pd.DataFrame()

def categorize_ipo(row):
    try:
        open_date = pd.to_datetime(row['Open'], format='%b %d', errors='coerce')
        close_date = pd.to_datetime(row['Close'], format='%b %d', errors='coerce')
        now = pd.Timestamp.now()

        if pd.isnull(open_date) or pd.isnull(close_date):
            return row['Status']
        
        current_year = datetime.now().year
        open_date = open_date.replace(year=current_year)
        close_date = close_date.replace(year=current_year)

        if open_date > now:
            return 'Upcoming'
        elif open_date <= now <= close_date:
            return 'Current'
        else:
            return 'Closed'
    except Exception as e:
        print(f"Error categorizing IPO: {e}")
        return row['Status']


def fetch_ipo_details(company_name, ipo_type):
    logger.info(f"Fetching IPO details for {company_name} ({ipo_type})")
    # This function would fetch detailed financial information for a specific IPO
    # You might need to implement web scraping or use an API to get this data
    # For now, we'll return a dummy dictionary with different structures for mainboard and SME IPOs
    if ipo_type == 'Main':
        return {
            "company_name": company_name,
            "issue_size": "₹1000 Cr",
            "price_band": "₹300 - ₹350",
            "lot_size": 40,
            "subscription_dates": "15 Sep 2024 - 18 Sep 2024",
            "revenue": "₹500 Cr",
            "net_profit": "₹50 Cr",
            "pe_ratio": "25.5",
            "roce": "18.2%",
            "debt_to_equity": "0.8",
        }
    elif ipo_type == 'SME':
        return {
            "company_name": company_name,
            "issue_size": "₹50 Cr",
            "price_band": "₹50 - ₹60",
            "lot_size": 2000,
            "subscription_dates": "20 Sep 2024 - 22 Sep 2024",
            "revenue": "₹20 Cr",
            "net_profit": "₹2 Cr",
            "pe_ratio": "15.5",
            "roce": "12.5%",
            "debt_to_equity": "0.5",
            "sector": "IT Services",
            "promoter_holding": "65%",
        }