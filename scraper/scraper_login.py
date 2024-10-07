import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
import time

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_webdriver():
    try:
        service = Service('/usr/bin/chromedriver')
        options = webdriver.ChromeOptions()
        # Example: disable images to speed up loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {str(e)}")
        raise


def login_to_moneycontrol(driver, url):
    try:
        login_url = f"https://m.moneycontrol.com/login.php?cpurl={url}"
        driver.get(login_url)
        
        # Switch to the login iframe
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "login_frame"))
        )
        
        # Click on the password login tab
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_log_otp_pre > div.loginwithTab > ul > li.signup_ctc'))
        ).click()

        # Fill in email and password
        email_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(1) > div > input[type=text]'))
        )
        password_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#mc_login > form > div:nth-child(2) > div > input[type=password]'))
        )
        email_input.send_keys(os.getenv('MONEYCONTROL_USERNAME'))
        password_input.send_keys(os.getenv('MONEYCONTROL_PASSWORD'))

        # Click on login button
        login_button = driver.find_element(By.CSS_SELECTOR, '#mc_login > form > button.continue.login_verify_btn')
        login_button.click()

        # Explicitly click "Continue Without Credit Insights"
        continue_without_credit_score_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mc_login > form > button.get_otp_signup.without_insights_btn'))
        )
        continue_without_credit_score_button.click()
        # Sleep for 4 seconds after clicking the button
        time.sleep(4)
        logger.info("Successfully logged in to MoneyControl")
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise