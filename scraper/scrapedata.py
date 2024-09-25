#scraper/scrapedata.py
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException,StaleElementReferenceException, TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
import time



# Setup Selenium WebDriver
service = Service('/usr/bin/chromedriver')
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['stock_data']
collection = db['detailed_financials']

def login_to_moneycontrol(url):
    # Navigate to the login page
    login_url = f"https://m.moneycontrol.com/login.php?cpurl={url}"
    driver.get(login_url)
    
    
    # Switch to the iframe containing the login form
    iframe = WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "login_frame"))
        )
        
    # Wait for the page to load and locate the "Login with Password" button
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_log_otp_pre > div.loginwithTab > ul > li.signup_ctc'))
    ).click()

    # After clicking "Login with Password," wait for the login fields to appear
    email_input = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(1) > div > input[type=text]'))
    )
    password_input = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(2) > div > input[type=password]'))
    )

    # Enter email/mobile number and password
    email_input.send_keys('gurusharan3107')
    password_input.send_keys('Rekha@0708')

     # Click the login button with the correct selector
    login_button = driver.find_element(By.CSS_SELECTOR, '#mc_login > form > button.continue.login_verify_btn')
    login_button.click()

    # Wait for the "Continue Without Credit Score" button to appear
    continue_without_credit_score_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_login > form > button.continue.login_btn'))
    )
    
    # Click the "Continue Without Credit Score" button
    continue_without_credit_score_button.click()


def scrape_moneycontrol_earnings(url):
    try:
        print(f"Opening page: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#latestRes > div > ul > li:nth-child(1)'))
        )   
        print("Page opened successfully")

        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(scroll_pause_time)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached end of page or no more content to load.")
                break
            last_height = new_height

            # Get page source and parse
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            result_cards = soup.select('li.rapidResCardWeb_gryCard__hQigs')
            print(f"Found {len(result_cards)} result cards to process")

            for card in result_cards:
                try:
                    company_name = card.select_one('h3 a').text.strip() if card.select_one('h3 a') else None
                    if not company_name:
                        print("Skipping card due to missing company name.")
                        continue

                    stock_link = card.select_one('h3 a')['href']
                    if not stock_link:
                        print(f"Skipping {company_name} due to missing stock link.")
                        continue

                    print(f"Processing stock: {company_name}")

                    # Extract data from the card
                    financial_data = extract_financial_data(card)
                    
                    # Check if the company already has data for this quarter
                    existing_company = collection.find_one({"company_name": company_name})
                    if existing_company:
                        existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
                        if financial_data['quarter'] in existing_quarters:
                            print(f"{company_name} already has data for {financial_data['quarter']}. Skipping.")
                            continue  # Skip to the next iteration of the loop
                        else:
                            print(f"Adding new data for {company_name} - {financial_data['quarter']}")
                            add_new_quarter_data(company_name, financial_data)
                    else:
                        print(f"Creating new entry for {company_name}")
                        create_new_company_entry(company_name, financial_data, stock_link)

                    print(f"Data for {company_name} (quarter {financial_data['quarter']}) processed successfully.")

                except Exception as e:
                    print(f"Error processing {company_name}: {str(e)}")

    except TimeoutException:
        print("Timeout waiting for page to load")
    except WebDriverException as e:
        print(f"WebDriver error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error during scraping: {str(e)}")
    finally:
        driver.quit()

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

def update_existing_data(company_name, financial_data):
    collection.update_one(
        {"company_name": company_name, "financial_metrics.quarter": financial_data['quarter']},
        {"$set": {f"financial_metrics.$.{k}": v for k, v in financial_data.items() if v is not None}}
    )

def add_new_quarter_data(company_name, financial_data):
    collection.update_one(
        {"company_name": company_name},
        {"$push": {"financial_metrics": financial_data}}
    )

def create_new_company_entry(company_name, financial_data, stock_link):
    # Scrape additional financial metrics
    additional_metrics, symbol = scrape_financial_metrics(stock_link)
    if additional_metrics:
        financial_data.update(additional_metrics)
    
    stock_data = {
        "company_name": company_name,
        "symbol": symbol,
        "financial_metrics": [financial_data],
        "timestamp": datetime.datetime.utcnow()
    }
    collection.insert_one(stock_data)

def scrape_financial_metrics(stock_link):
    try:
        # Open the stock link in a new tab
        driver.execute_script(f"window.open('{stock_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        
        detailed_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract metrics (your existing extraction logic here)
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

        # Extract symbol
        symbol = detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p').text.strip() if detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p') else None

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return metrics, symbol
    
    except Exception as e:
        print(f"Error scraping financial metrics: {str(e)}")
        return None, None


def scrape_estimates_vs_actuals(url):
    try:
        print(f"Opening page: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#estVsAct > div > ul > li:nth-child(1)'))
        )   
        print("Page opened successfully")

        last_card_count = 0
        scroll_pause_time = 1
        no_new_content_count = 0
        max_no_new_content = 3

        while True:
            estimate_cards = driver.find_elements(By.CSS_SELECTOR, '#estVsAct > div > ul > li')
            
            if len(estimate_cards) == last_card_count:
                no_new_content_count += 1
                if no_new_content_count >= max_no_new_content:
                    print(f"No new content after {max_no_new_content} scrolls. Ending scrape.")
                    break
            else:
                no_new_content_count = 0
       
            for card in estimate_cards[last_card_count:]:
                try:
                    company_name = card.find_element(By.CSS_SELECTOR, 'h3 a').text.strip()
                    quarter = card.find_element(By.CSS_SELECTOR, 'tr th:nth-child(1)').text.strip()
                    estimates_line = card.find_element(By.CSS_SELECTOR, 'div.EastimateCard_botTxtCen__VpdiR').text.strip()
                    cmp =  card.find_element(By.CSS_SELECTOR, 'p.EastimateCard_priceTxt__8EImd').text.strip()
                    result_date =  card.find_element(By.CSS_SELECTOR, 'p.EastimateCard_gryTxtOne__jmUR2').text.strip()
                    print(f"Processing: {company_name}, Quarter: {quarter}, Estimates: {estimates_line}")

                    # Prepare default financial data
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

                    existing_company = collection.find_one({"company_name": company_name})
                    if existing_company:
                        existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
                        if quarter in existing_quarters:
                            collection.update_one(
                                {"company_name": company_name, "financial_metrics.quarter": quarter},
                                {"$set": {"financial_metrics.$.estimates": estimates_line}}
                            )
                            print(f"Updated estimates for {company_name} - {quarter}")
                        else:
                            collection.update_one(
                                {"company_name": company_name},
                                {"$push": {"financial_metrics": default_financial_data}}
                            )
                            print(f"Added new quarter data for {company_name} - {quarter}")
                    else:
                        new_company = {
                            "company_name": company_name,
                            "symbol": "NA",
                            "financial_metrics": [default_financial_data],
                            "timestamp": datetime.datetime.utcnow()
                        }
                        collection.insert_one(new_company)
                        print(f"Created new entry for {company_name}")

                except StaleElementReferenceException:
                    print("Stale element encountered. Skipping this card.")
                except Exception as e:
                    print(f"Error processing estimates: {e}")

            last_card_count = len(estimate_cards)
            driver.execute_script("arguments[0].scrollIntoView();", estimate_cards[-1])
            time.sleep(scroll_pause_time)

            print(f"Processed {last_card_count} cards so far.")

    except Exception as e:
        print(f"Error during estimates scraping: {e}")
    finally:
        print(f"Processed a total of {last_card_count} cards.")
        driver.quit()


# Main function
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scrapedata.py <url> <scrape_type>")
        print("scrape_type options: earnings, estimates")
        sys.exit(1)

    url = sys.argv[1]
    scrape_type = sys.argv[2]

    # Execute the login function
    login_to_moneycontrol(url)

    # After login, continue with scraping based on the scrape_type
    if scrape_type == 'earnings':
        scrape_moneycontrol_earnings(url)
    elif scrape_type == 'estimates':
        scrape_estimates_vs_actuals(url)
    else:
        print("Invalid scrape_type. Choose either 'earnings' or 'estimates'.")

    # Quit the driver when done
    driver.quit()
