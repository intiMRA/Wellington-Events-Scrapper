from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By

import FileNames
import ScrapperNames
from EventInfo import EventInfo
import re
from datetime import datetime
from dateutil import parser
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from typing import List, Optional, Set
import json

class HumanitixScrapper:

    @staticmethod
    def get_dates_from_event(driver: webdriver, multiple_dates: bool)-> List[datetime]:
        dates: List[datetime] = []
        driver.maximize_window()
        driver.execute_script("window.scrollTo(200, 500);")
        if multiple_dates:
            while True:
                try:
                    element = driver.find_element(By.XPATH, "//button[contains(., 'more dates')]")
                    element.click()
                    break
                except:
                    driver.execute_script("window.scrollTo(200, 500);")
                    sleep(1)
            form = driver.find_element(By.TAG_NAME, "form")
            list_elements = form.find_elements(By.TAG_NAME, "li")
            for element in list_elements:
                reg = r"(\d{1,2}\s[aA-zZ]{3},\s[aA-zZ0-9:]*[AMPamp]{2})"
                matches = re.findall(reg, element.text)
                if len(matches) > 1:
                    for match in matches:
                        dates.append(parser.parse(match.replace(",", "")))
                elif len(matches) == 1:
                    date = parser.parse(matches[0])
                    dates.append(date)
                else:
                    print("multiple dates: ", element.text)
            return dates
        else:
            date_string = driver.find_element(By.CLASS_NAME, "datetime").text.split("\n")[0]
            reg = r"(\d{1,2}\s[aA-zZ]{3}\s*[0-9]*,\s[aA-zZ0-9:]*[AMPamp]{2})"
            matches = re.findall(reg, date_string)
            if len(matches) > 1:
                for match in matches:
                    dates.append(parser.parse(match.replace(",", "")))
            elif len(matches) == 1:
                date = parser.parse(matches[0])
                dates.append(date)
            else:
                print("single date: ", date_string)
            return dates
    @staticmethod
    def format_input(input_string):
        if not input_string:
            return input_string
        input_string = input_string.replace("&", "And").replace(" ", "").replace(",", "")
        return input_string[0].lower() + input_string[1:]

    @staticmethod
    def get_event(url: str, category: str, multiple_dates: bool, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "titlewrapper").text.split("\n")[0]
        try:
            image_url: str = driver.find_element(By.CLASS_NAME, "banner").find_element(By.TAG_NAME, "img").get_attribute('src')
        except:
            image_url = ""
        try:
            location = driver.find_element(By.CLASS_NAME, "EventLocation").find_element(By.CLASS_NAME, "address").text
            venue: str = location.split("\n")[1]
        except:
            venue: str = driver.find_element(By.CLASS_NAME, "address").text
        venue = venue.split("  ·  ")[0]
        print(f"venue: {venue}")
        dates: List[datetime] = HumanitixScrapper.get_dates_from_event(driver, multiple_dates)
        description: str = driver.find_element(By.CLASS_NAME, "RichContent").text
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=url,
                         source=ScrapperNames.HUMANITIX,
                         event_type=category,
                         description=description)

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        events: List[EventInfo] = []
        driver = webdriver.Chrome()
        driver.get('https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463')
        categories_button = driver.find_element(By.XPATH, "//button[contains(., 'Categories')]")
        categories_button.click()
        categories = driver.find_element(By.ID, "listbox-categories").find_elements(By.TAG_NAME, "li")
        categories = [(HumanitixScrapper.format_input(category.text), category.text) for category in categories]
        event_urls: List[tuple[str, str, bool]] = []
        for category, categoryName in categories:
            print("cat: ", category, " ", categoryName)
            page = 0
            while True:
                url = f'https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463&page={page}&categories={category}'
                driver.get(url)
                _ = WebDriverWait(driver, 10, poll_frequency=1).until(ec.presence_of_element_located((By.XPATH, f"//button[contains(., '{categoryName}')]")))
                height = driver.execute_script("return document.body.scrollHeight")
                scrolled_amount = 0
                while True:
                    if scrolled_amount > height:
                        break
                    driver.execute_script(f"window.scrollBy(0, {100});")

                    scrolled_amount += 100
                events_data = driver.find_elements(By.CLASS_NAME, 'test')
                if not events_data:
                    break
                for event in events_data:
                    event_url = event.get_attribute('href')
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    divs = [x.text for x in event.find_elements(By.TAG_NAME, 'div')]
                    multiple_dates = False
                    for date_string in divs:
                        if "more times" in date_string:
                            multiple_dates = True
                            break
                    event_urls.append((event_url, categoryName, multiple_dates))
                page += 1
        with open(FileNames.HUMANITIX_URLS, mode="w") as f:
            json.dump(event_urls, f, indent=2)

        out_file = open(FileNames.HUMANITIX_EVENTS, 'w')
        out_file.write("[\n")
        for part in event_urls:
            print(f"category: {part[0]} url: {part[1]}")
            try:
                event = HumanitixScrapper.get_event(part[0], part[1], part[2], driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("-"*100)
        out_file.write("]\n")
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(HumanitixScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
