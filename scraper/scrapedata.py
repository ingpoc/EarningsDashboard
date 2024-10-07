import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne
import datetime
import time
import logging
from dotenv import load_dotenv
from scraper_login import setup_webdriver, login_to_moneycontrol
from scrape_estimates import process_estimate_card, update_or_insert_company_data, scrape_estimates_vs_actuals
from scrape_metrics import extract_financial_data, scrape_financial_metrics, process_result_card


# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['stock_data']
collection = db['detailed_financials']


def scrape_moneycontrol_earnings(url):
    driver = setup_webdriver()
    try:
        login_to_moneycontrol(driver, url)
        logger.info(f"Opening page: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#latestRes > div > ul > li:nth-child(1)'))
        )   
        logger.info("Page opened successfully")

        scroll_page(driver)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        result_cards = soup.select('li.rapidResCardWeb_gryCard__hQigs')
        logger.info(f"Found {len(result_cards)} result cards to process")

        for card in result_cards:
            process_result_card(card, driver)

    except TimeoutException:
        logger.error("Timeout waiting for page to load")
    except WebDriverException as e:
        logger.error(f"WebDriver error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {str(e)}")
    finally:
        driver.quit()


def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height








def main():
    if len(sys.argv) != 3:
        logger.error("Usage: python3 scrapedata.py <url> <scrape_type>")
        logger.error("scrape_type options: earnings, estimates")
        sys.exit(1)

    url = sys.argv[1]
    scrape_type = sys.argv[2]

    try:
        if scrape_type == 'earnings':
            scrape_moneycontrol_earnings(url)
        elif scrape_type == 'estimates':
            scrape_estimates_vs_actuals(url)
        else:
            logger.error("Invalid scrape_type. Choose either 'earnings' or 'estimates'.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during scraping: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()