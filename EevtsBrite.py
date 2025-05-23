# https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/
from datetime import datetime
from time import sleep

from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil import parser
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.relativedelta import relativedelta
class EventbriteScrapper:

    @staticmethod
    def getCategories(driver: webdriver) -> [(str, str)]:
        categories = []
        driver.find_element(By.CLASS_NAME, "filter-toggle").click()
        filters = driver.find_element(By.CLASS_NAME, "filter-choice-items")
        cats = filters.find_elements(By.TAG_NAME, "li")
        for cat in cats:
            link = cat.find_element(By.TAG_NAME, "a").get_attribute("href")
            category = (cat.text, link)
            categories.append(category)
        return categories

    @staticmethod
    def getEvents(driver: webdriver, titles: set, category: str) -> [EventInfo]:
        curentPage = 1
        while True:
            nextUrl = re.sub(r"page=\d+", f"page={curentPage}", driver.current_url)
            driver.get(nextUrl)
            try:
                pagination = driver.find_element(By.XPATH, "//li[@data-testid='pagination-parent']")
                lastPage = int(pagination.text.split(" of ")[-1])
                if curentPage > lastPage:
                    break
            except:
                pass
            curentPage += 1
            #search-event
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='search-event']")
            for card in cards:
                imageUrl = card.find_element(By.CLASS_NAME, "event-card-image").get_attribute("src")
                titleTag = card.find_element(By.CLASS_NAME, "event-card-link ")
                eventLink = titleTag.get_attribute("href")
                texts = card.text.split("\n")
                if texts[0] == "Sales end soon":
                    texts = texts[1:]
                title = texts[0]
                dateString = texts[1]
                venue = texts[2]

                print("imageUrl:", imageUrl)
                print("title:", title)
                print("date:", dateString)
                print("venue:", venue)
                print("eventLink:", eventLink)

    @staticmethod
    def fetch_events(previousTitles: set) -> [EventInfo]:
        driver = webdriver.Chrome()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        cats = EventbriteScrapper.getCategories(driver)
        for cat in cats:
            catName, link = cat
            print(link)
            driver.get(link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            #&start_date=2025-05-23&end_date=2025-06-29
            new_url = (driver.current_url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            driver.get(new_url)
            EventbriteScrapper.getEvents(driver, previousTitles, cat)

        return []
events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
with open('wellys.json', 'w') as outfile:
    json.dump(events, outfile)