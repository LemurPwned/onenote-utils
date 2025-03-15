from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import argparse
import time
import json

parse = argparse.ArgumentParser(
    description="Extract Kindle highlights from your Amazon account"
)
parse.add_argument("--email", type=str, required=True, help="Your Amazon email")
parse.add_argument("--password", type=str, required=True, help="Your Amazon password")
parse.add_argument(
    "--wait-time",
    type=int,
    required=False,
    default=3,
    help="Time to wait for the highlights to load",
)
url = "https://read.amazon.com/notebook"

if __name__ == "__main__":
    args = parse.parse_args()
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    
    # Wait for email field to be present and interact with it
    try:
        print("Waiting for login page to load...")
        email_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ap_email"))
        )
        email_el.clear()
        email_el.send_keys(args.email)
        print("Email entered")
        
        # Look for password field
        try:
            # Try to find the next button if it exists (Amazon sometimes has a two-step login)
            next_button = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "continue"))
            )
            next_button.click()
            print("Clicked continue button")
        except (TimeoutException, NoSuchElementException):
            print("No continue button found, assuming single-page login")
        
        # Now wait for password field
        pass_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ap_password"))
        )
        pass_el.clear()
        pass_el.send_keys(args.password)
        print("Password entered")
        
        # Click sign in button
        sigin_el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "signInSubmit"))
        )
        sigin_el.click()
        print("Sign in button clicked")
        
    except Exception as e:
        print(f"Error during login process: {e}")
        driver.save_screenshot("login_error.png")
        print(f"Current URL: {driver.current_url}")
        print("Page source snippet:")
        print(driver.page_source[:500] + "...")
        driver.quit()
        exit(1)
    
    # Rest of the login handling
    try:
        sec_challenge = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "single-input-box-otp"))
        )
        sec_challenge_input = input("Enter the security challenge: ")
        sec_challenge.send_keys(sec_challenge_input)
        elem = driver.find_element(By.CLASS_NAME, "a-button-input")
        elem.click()
    except TimeoutException:
        print("No security challenge detected")
    except Exception as e:
        print(f"Error during security challenge: {e}")

    # Continue with the rest of the code
    book_data = {}
    print("Waiting for highlights page to load...")
    time.sleep(5)  # Give some time for the highlights page to load
    
    for book in driver.find_elements(By.CLASS_NAME, "kp-notebook-library-each-book"):
        time.sleep(0.1)
        print("Extracting highlights for: " + book.text.split("\n")[0])
        book_title, book_author = book.text.split("\n")
        book_data[book_title] = []
        book_info = {
            "title": book_title,
            "author": book_author,
            "highlights": [],
        }
        book.click()
        # needs some sleep in order to load the highlights
        time.sleep(args.wait_time)
        try:
            for h in driver.find_elements(By.ID, "highlight"):
                book_info["highlights"].append(h.text)
        except Exception as e:
            print(f"could not extract highlights for: {book_title} - {e}")
        book_data[book_title] = book_info
    json.dump(
        book_data, open("kindle_highlights.json", "w"), indent=4, ensure_ascii=False
    )

    driver.quit()
