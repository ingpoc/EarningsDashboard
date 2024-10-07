from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
from pymongo import MongoClient
import datetime
from scraper_login import login_to_moneycontrol, setup_webdriver
logger = logging.getLogger(__name__)


client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['stock_data']
collection = db['detailed_financials']

def process_estimate_card(card):
    try:
        company_name = card.find_element(By.CSS_SELECTOR, 'h3 a').text.strip()
        quarter = card.find_element(By.CSS_SELECTOR, 'tr th:nth-child(1)').text.strip()
        estimates_line = card.find_element(By.CSS_SELECTOR, 'div.EastimateCard_botTxtCen__VpdiR').text.strip()
        cmp = card.find_element(By.CSS_SELECTOR, 'p.EastimateCard_priceTxt__8EImd').text.strip()
        result_date = card.find_element(By.CSS_SELECTOR, 'p.EastimateCard_gryTxtOne__jmUR2').text.strip()
        logger.info(f"Processing: {company_name}, Quarter: {quarter}, Estimates: {estimates_line}")

        default_financial_data = {
            "quarter": quarter,
            "estimates": estimates_line,
            "cmp": cmp,
            "revenue": "0",
            "gross_profit": "0",
            "net_profit": "0",
            "net_profit_growth": "0%",
            "gross_profit_growth": "0%",
            "revenue_growth": "0%",
            "result_date": result_date,
            "report_type": "NA",
            "market_cap": "NA",
            "face_value": "NA",
            "book_value": "NA",
            "dividend_yield": "NA",
            "ttm_eps": "NA",
            "ttm_pe": "NA",
            "pb_ratio": "NA",
            "sector_pe": "NA",
            "piotroski_score": "NA",
            "revenue_growth_3yr_cagr": "NA",
            "net_profit_growth_3yr_cagr": "NA",
            "operating_profit_growth_3yr_cagr": "NA",
            "strengths": "NA",
            "weaknesses": "NA",
            "technicals_trend": "NA",
            "fundamental_insights": "NA",
            "fundamental_insights_description": "NA"
        }
        update_or_insert_company_data(company_name, quarter, default_financial_data)

    except StaleElementReferenceException:
        logger.warning("Stale element encountered. Skipping this card.")
    except Exception as e:
        logger.error(f"Error processing estimates for {company_name}: {e}")

def update_or_insert_company_data(company_name, quarter, financial_data):
    existing_company = collection.find_one({"company_name": company_name})
    if existing_company:
        existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
        if quarter in existing_quarters:
            collection.update_one(
                {"company_name": company_name, "financial_metrics.quarter": quarter},
                {"$set": {"financial_metrics.$.estimates": financial_data['estimates']}}
            )
            logger.info(f"Updated estimates for {company_name} - {quarter}")
        else:
            collection.update_one(
                {"company_name": company_name},
                {"$push": {"financial_metrics": financial_data}}
            )
            logger.info(f"Added new quarter data for {company_name} - {quarter}")
    else:
        new_company = {
            "company_name": company_name,
            "symbol": "NA",
            "financial_metrics": [financial_data],
            "timestamp": datetime.datetime.utcnow()
        }
        collection.insert_one(new_company)
        logger.info(f"Created new entry for {company_name}")

def scrape_estimates_vs_actuals(url):
    driver = setup_webdriver()
    last_card_count = 0  # Initialize here to avoid referencing before assignment
    try:
        login_to_moneycontrol(driver, url)
        logger.info(f"Opening page: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#estVsAct > div > ul > li:nth-child(1)'))
        )   
        logger.info("Page opened successfully")

        no_new_content_count = 0
        max_no_new_content = 3

        while True:
            estimate_cards = driver.find_elements(By.CSS_SELECTOR, '#estVsAct > div > ul > li')
            
            if len(estimate_cards) == last_card_count:
                no_new_content_count += 1
                if no_new_content_count >= max_no_new_content:
                    logger.info(f"No new content after {max_no_new_content} scrolls. Ending scrape.")
                    break
            else:
                no_new_content_count = 0
       
            for card in estimate_cards[last_card_count:]:
                process_estimate_card(card)

            last_card_count = len(estimate_cards)
            driver.execute_script("arguments[0].scrollIntoView();", estimate_cards[-1])
            time.sleep(1)

            logger.info(f"Processed {last_card_count} cards so far.")

    except Exception as e:
        logger.error(f"Error during estimates scraping: {e}")
    finally:
        logger.info(f"Processed a total of {last_card_count} cards.")
        driver.quit()