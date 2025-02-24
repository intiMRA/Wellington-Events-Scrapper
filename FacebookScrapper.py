from dotenv import load_dotenv
import time
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime
import os
from pathlib import Path
dotenv_path = Path('./.venv/.env')
load_dotenv(dotenv_path=dotenv_path)

class FacebookScrapper:
    @staticmethod
    def slow_scroll_to_bottom(driver, loadedDriver, scroll_increment=300) -> [EventInfo]:
        events = {}
        oldEventTitles = {}
        newEventTitles = {}
        while True:
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            sleep(1)
            html = driver.find_elements(By.CLASS_NAME, 'x1xmf6yo')
            for event in html:
                try:
                    info =  event.find_elements(By.CLASS_NAME, "xu06os2")
                    title = info[1]
                    venue = info[2]
                    date = info[0]
                    print(date.text)
                    eventUrl = event.find_elements(By.TAG_NAME, 'a')
                    imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    print(imageUrl)
                    newEventTitles[title] = EventInfo(name=title,
                                        date=date,
                                        displayDate=date,
                                        image=imageUrl,
                                        url=eventUrl[0].get_attribute('href'),
                                        venue=venue,
                                        source="facebook")
                except:
                    continue

            if oldEventTitles == newEventTitles:
                driver.close()
                print(len(newEventTitles))
                return newEventTitles.values()
            oldEventTitles = newEventTitles

    @staticmethod
    def fetch_events() -> [EventInfo]:
        driver = webdriver.Chrome()
        driver.get("https://www.facebook.com/events/?date_filter_option=ANY_DATE&discover_tab=CUSTOM&location_id=114912541853133")
        email = os.getenv("EMAIL")
        password = os.getenv("EMAIL_PASSWORD")
        loadedDriver = WebDriverWait(driver, 30)

        close_button = loadedDriver.until(EC.visibility_of_element_located((By.CLASS_NAME, "x92rtbv")))
        email_field = loadedDriver.until(EC.visibility_of_element_located((By.NAME, 'email')))
        pass_field = loadedDriver.until(EC.visibility_of_element_located((By.NAME, 'pass')))

        close_button.click()
        email_field.send_keys(email)
        pass_field.send_keys(password)
        pass_field.send_keys(Keys.RETURN)
        sleep(10)
        return list(FacebookScrapper.slow_scroll_to_bottom(driver, loadedDriver, scroll_increment=5000))

FacebookScrapper.fetch_events()