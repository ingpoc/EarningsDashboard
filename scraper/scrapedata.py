import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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


def scrape_financial_metrics(stock_link):
    try:
        # Open the stock link in a new tab
        driver.execute_script(f"window.open('{stock_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        
        detailed_soup = BeautifulSoup(driver.page_source, 'html.parser')

       
        
        # Extract initial metrics
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

        # Corrected symbol extraction
        symbol = detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p').text.strip() if detailed_soup.select_one('#company_info > ul > li:nth-child(5) > ul > li:nth-child(2) > p') else None

        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return metrics, symbol
    
    except Exception as e:
        print(f"Error scraping financial metrics: {e}")
        return None, None



def scrape_moneycontrol_earnings(url):
    try:
        print(f"Opening page: {url}")
     
        WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '#latestRes > div > ul > li:nth-child(1)'))
        )   
        print("Page opened successfully")

        while True:
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

                    stock_link = f"{stock_link}"
                    print(f"Processing stock: {company_name}")


                    # Extract data from the card
                    cmp = card.select_one('p.rapidResCardWeb_priceTxt___5MvY').text.strip() if card.select_one('p.rapidResCardWeb_priceTxt___5MvY') else None
                    revenue = card.select_one('tr:nth-child(1) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(1) td:nth-child(2)') else None
                    gross_profit = card.select_one('tr:nth-child(2) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(2) td:nth-child(2)') else None
                    net_profit = card.select_one('tr:nth-child(3) td:nth-child(2)').text.strip() if card.select_one('tr:nth-child(3) td:nth-child(2)') else None
                    net_profit_growth = card.select_one('tr:nth-child(3) td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(3) td:nth-child(4)') else None
                    gross_profit_growth = card.select_one('tr:nth-child(2) td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(2) td:nth-child(4)') else None
                    revenue_growth = card.select_one('tr:nth-child(1)  td:nth-child(4)').text.strip() if card.select_one('tr:nth-child(1)  td:nth-child(4)') else None
                    quarter = card.select_one('tr th:nth-child(1)').text.strip() if card.select_one('tr th:nth-child(1)') else None
                   
                    

                                     
                    result_date = card.select_one('p.rapidResCardWeb_gryTxtOne__mEhU_').text.strip() if card.select_one('p.rapidResCardWeb_gryTxtOne__mEhU_') else None
                    report_type = card.select_one('p.rapidResCardWeb_bottomText__p8YzI').text.strip() if card.select_one('p.rapidResCardWeb_bottomText__p8YzI') else None
                    # Check if the company already has data for this quarter
                    existing_company = collection.find_one({"company_name": company_name})
                    if existing_company:
                        existing_quarters = [metric['quarter'] for metric in existing_company['financial_metrics']]
                        if quarter in existing_quarters:
                            print(f"{company_name} already has data for {quarter}. Skipping.")
                            continue

                    # Scrape the financial metrics and symbol from the detailed page
                    financial_metrics, symbol = scrape_financial_metrics(stock_link)
                    financial_metrics.update({
                        "revenue": revenue,
                        "gross_profit": gross_profit,
                        "net_profit": net_profit,
                        "net_profit_growth": net_profit_growth,
                        "result_date": result_date,
                        "gross_profit_growth": gross_profit_growth,
                        "revenue_growth": revenue_growth,
                        "quarter": quarter,
                        "report_type": report_type,
                        "cmp": cmp
                    })

                    print(financial_metrics)
                    
                    # Update the database with the new quarter's data
                    if existing_company:
                        collection.update_one(
                            {"company_name": company_name},
                            {"$push": {"financial_metrics": financial_metrics}}
                        )
                    else:
                        stock_data = {
                            "company_name": company_name,
                            "symbol": symbol,  # Add symbol to the main document
                            "financial_metrics": [financial_metrics],
                            "timestamp": datetime.datetime.utcnow()
                        }
                        collection.insert_one(stock_data)

                    print(f"Data for {company_name} (quarter {quarter}) inserted/updated successfully.")

                except Exception as e:
                    print(f"Error processing {company_name}: {e}")

            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("No more content to load.")
                break

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

# Main function
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scrapedata.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    # Execute the login function
    login_to_moneycontrol(url)

    # After login, continue with scraping
    scrape_moneycontrol_earnings(url)

    # Quit the driver when done
    driver.quit()
