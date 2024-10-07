from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging
import os
from pymongo import MongoClient
import datetime

logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['stock_data']
collection = db['detailed_financials']

def process_result_card(card, driver):
    try:
        company_name = card.select_one('h3 a').text.strip() if card.select_one('h3 a') else None
        if not company_name:
            logger.warning("Skipping card due to missing company name.")
            return

        stock_link = card.select_one('h3 a')['href']
        if not stock_link:
            logger.warning(f"Skipping {company_name} due to missing stock link.")
            return

        logger.info(f"Processing stock: {company_name}")

        # Check if the company already has financial data for the current quarter
        financial_data = extract_financial_data(card)
        existing_company = collection.find_one({"company_name": company_name})
        if existing_company:
            existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
            if financial_data['quarter'] in existing_quarters:
                logger.info(f"{company_name} already has data for {financial_data['quarter']}. Skipping.")
                return  # Skip processing if data for the quarter already exists

        additional_metrics, symbol = scrape_financial_metrics(driver, stock_link)
        
        if additional_metrics:
            financial_data.update(additional_metrics)

        # Insert or update the financial data in the database
        if existing_company:
            logger.info(f"Adding new data for {company_name} - {financial_data['quarter']}")
            collection.update_one(
                {"company_name": company_name},
                {"$push": {"financial_metrics": financial_data}}
            )
        else:
            logger.info(f"Creating new entry for {company_name}")
            stock_data = {
                "company_name": company_name,
                "symbol": symbol,
                "financial_metrics": [financial_data],
                "timestamp": datetime.datetime.utcnow()
            }
            collection.insert_one(stock_data)

        logger.info(f"Data for {company_name} (quarter {financial_data['quarter']}) processed successfully.")

    except Exception as e:
        logger.error(f"Error processing {company_name}: {str(e)}")

def extract_financial_data(card):
    return {
        "cmp": card.select_one('p.rapidResCardWeb_priceTxt___5MvY').text.strip() if card.select_one('p.rapidResCardWeb_priceTxt___5MvY') else None,
        "revenue": card.select_one('tr:nth-child(1) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(1) td:nth-child(2)') else None,
        "gross_profit": card.select_one('tr:nth-child(2) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(2) td:nth-child(2)') else None,
        "net_profit": card.select_one('tr:nth-child(3) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(3) td:nth-child(2)') else None,
        "net_profit_growth": card.select_one('tr:nth-child(3) td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(3) td:nth-child(4)') else None,
        "gross_profit_growth": card.select_one('tr:nth-child(2) td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(2) td:nth-child(4)') else None,
        "revenue_growth": card.select_one('tr:nth-child(1) td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(1) td:nth-child(4)') else None,
        "quarter": card.select_one('tr th:nth-child(1)').text.strip() if card.select_one('tr th:nth-child(1)') else None,
        "result_date": card.select_one('p.rapidResCardWeb_gryTxtOne__mEhU_').text.strip() if card.select_one('p.rapidResCardWeb_gryTxtOne__mEhU_') else None,
        "report_type": card.select_one('p.rapidResCardWeb_bottomText__p8YzI').text.strip() if card.select_one('p.rapidResCardWeb_bottomText__p8YzI') else None,
    }

def scrape_financial_metrics(driver, stock_link):
    try:
        driver.execute_script(f"window.open('{stock_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        
        detailed_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        metrics = {
            "market_cap": detailed_soup.select_one('tr:nth-child(7) td.nsemktcap.bsemktcap').text.strip() if detailed_soup.select_one('tr:nth-child(7) td.nsemktcap.bsemktcap') else None,
            "face_value": detailed_soup.select_one('tr:nth-child(7) td.nsefv.bsefv').text.strip() if detailed_soup.select_one('tr:nth-child(7) td.nsefv.bsefv') else None,
            "book_value": detailed_soup.select_one('tr:nth-child(5) td.nsebv.bsebv').text.strip() if detailed_soup.select_one('tr:nth-child(5) td.nsebv.bsebv') else None,
            "dividend_yield": detailed_soup.select_one('tr:nth-child(6) td.nsedy.bsedy').text.strip() if detailed_soup.select_one('tr:nth-child(6) td.nsedy.bsedy') else None,
            "ttm_eps": detailed_soup.select_one('tr:nth-child(1) td:nth-child(2) span.nseceps.bseceps').text.strip() if detailed_soup.select_one('tr:nth-child(1) td:nth-child(2) span.nseceps.bseceps') else None,
            "ttm_pe": detailed_soup.select_one('tr:nth-child(2) td:nth-child(2) span.nsepe.bsepe').text.strip() if detailed_soup.select_one('tr:nth-child(2) td:nth-child(2) span.nsepe.bsepe') else None,
            "pb_ratio": detailed_soup.select_one('tr:nth-child(3) td:nth-child(2) span.nsepb.bsepb').text.strip() if detailed_soup.select_one('tr:nth-child(3) td:nth-child(2) span.nsepb.bsepb') else None,
            "sector_pe": detailed_soup.select_one('tr:nth-child(4) td.nsesc_ttm.bsesc_ttm').text.strip() if detailed_soup.select_one('tr:nth-child(4) td.nsesc_ttm.bsesc_ttm') else None,
            "piotroski_score": detailed_soup.select_one('div:nth-child(2) div.fpioi div.nof').text.strip() if detailed_soup.select_one('div:nth-child(2) div.fpioi div.nof') else None,
            "revenue_growth_3yr_cagr": detailed_soup.select_one('tr:-soup-contains("Revenue") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:-soup-contains("Revenue") td:nth-child(2)') else None,
            "net_profit_growth_3yr_cagr": detailed_soup.select_one('tr:-soup-contains("NetProfit") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:-soup-contains("NetProfit") td:nth-child(2)') else None,
            "operating_profit_growth_3yr_cagr": detailed_soup.select_one('tr:-soup-contains("OperatingProfit") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:-soup-contains("OperatingProfit") td:nth-child(2)') else None,
            "strengths": detailed_soup.select_one('#swot_ls > a > strong').text.strip() if detailed_soup.select_one('#swot_ls > a > strong') else None,
            "weaknesses": detailed_soup.select_one('#swot_lw > a > strong').text.strip() if detailed_soup.select_one('#swot_lw > a > strong') else None,
            "technicals_trend": detailed_soup.select_one('#techAnalysis a[style*="flex"]').text.strip() if detailed_soup.select_one('#techAnalysis a[style*="flex"]') else None,
            "fundamental_insights": detailed_soup.select_one('#mc_essenclick > div.bx_mceti.mc_insght > div > div').text.strip() if detailed_soup.select_one('#mc_essenclick > div.bx_mceti.mc_insght > div > div') else None,
            "fundamental_insights_description": detailed_soup.select_one('#insight_class').text.strip() if detailed_soup.select_one('#insight_class') else None
        }

        symbol = detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p').text.strip() if detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p') else None

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return metrics, symbol
    except Exception as e:
        logger.error(f"Error scraping financial metrics: {str(e)}")
        return None, None
