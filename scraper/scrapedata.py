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

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['stock_data']
collection = db['detailed_financials']

def setup_webdriver():
    service = Service('/usr/bin/chromedriver')
    options = webdriver.ChromeOptions()
    return webdriver.Chrome(service=service, options=options)

def login_to_moneycontrol(driver, url):
    try:
        login_url = f"https://m.moneycontrol.com/login.php?cpurl={url}"
        driver.get(login_url)
        
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "login_frame"))
        )
        
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_log_otp_pre > div.loginwithTab > ul > li.signup_ctc'))
        ).click()

        email_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(1) > div > input[type=text]'))
        )
        password_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(2) > div > input[type=password]'))
        )

        email_input.send_keys(os.getenv('MONEYCONTROL_USERNAME'))
        password_input.send_keys(os.getenv('MONEYCONTROL_PASSWORD'))

        login_button = driver.find_element(By.CSS_SELECTOR, '#mc_login > form > button.continue.login_verify_btn')
        login_button.click()

        continue_without_credit_score_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_login > form > button.continue.login_btn'))
        )
        continue_without_credit_score_button.click()

        logger.info("Successfully logged in to MoneyControl")
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

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
            "revenue_growth_3yr_cagr": detailed_soup.select_one('tr:contains("Revenue") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:contains("Revenue") td:nth-child(2)') else None,
            "net_profit_growth_3yr_cagr": detailed_soup.select_one('tr:contains("NetProfit") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:contains("NetProfit") td:nth-child(2)') else None,
            "operating_profit_growth_3yr_cagr": detailed_soup.select_one('tr:contains("OperatingProfit") td:nth-child(2)').text.strip() if detailed_soup.select_one('tr:contains("OperatingProfit") td:nth-child(2)') else None,
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

        financial_data = extract_financial_data(card)
        additional_metrics, symbol = scrape_financial_metrics(driver, stock_link)
        
        if additional_metrics:
            financial_data.update(additional_metrics)

        existing_company = collection.find_one({"company_name": company_name})
        if existing_company:
            existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
            if financial_data['quarter'] in existing_quarters:
                logger.info(f"{company_name} already has data for {financial_data['quarter']}. Skipping.")
                return
            else:
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
    try:
        login_to_moneycontrol(driver, url)
        logger.info(f"Opening page: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#estVsAct > div > ul > li:nth-child(1)'))
        )   
        logger.info("Page opened successfully")

        last_card_count = 0
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