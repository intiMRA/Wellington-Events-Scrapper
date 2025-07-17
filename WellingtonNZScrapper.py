from datetime import datetime
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import FileNames
import ScrapperNames
from DateFormatting import DateFormatting
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil import parser
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from typing import List, Set, Optional
import json


class WellingtonNZScrapper:
    @staticmethod
    def get_dates(date_string: str) -> List[datetime]:
        dates = []
        try:
            string_parts: List[str] = date_string.split(" – ")
            hour = "1:01AM"
            if len(string_parts) > 1:
                if len(string_parts[0]) > 2:
                    start_day = string_parts[0]
                    month_parts = string_parts[1].split(" ")
                    end_day = month_parts[0]
                    month_year = " ".join(month_parts[1:])
                    start_date = f"{start_day} {hour}"
                    end_date = f"{end_day} {month_year} {hour}"
                else:
                    start_day = string_parts[0]
                    month_parts = string_parts[1].split(" ")
                    end_day = month_parts[0]
                    month_year = " ".join(month_parts[1:])
                    start_date = f"{start_day} {month_year} {hour}"
                    end_date = f"{end_day} {month_year} {hour}"

                dates = DateFormatting.create_range(parser.parse(start_date), parser.parse(end_date))
            else:
                dates.append(parser.parse(f"{date_string} {hour}"))
        except Exception as e:
            print(e)
        return dates

    @staticmethod
    def get_event(url: str, category: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(1)
        count = 0
        while True:
            try:
                image_url: str = driver.find_element(By.XPATH,
                                                     "//img[contains(@class, 'site-picture__img')]").get_attribute(
                    "src")
                break
            except:
                if count >= 10:
                    raise Exception(f"no image found {url}")
                sleep(1)
                count += 1
        driver.execute_script(f"window.scrollBy(0, {500});")
        sleep(1)
        count = 0
        while True:
            try:
                title: str = driver.find_element(By.XPATH, "//h1[contains(@class, 'image-header__title')]").text
                break
            except:
                if count >= 10:
                    raise Exception(f"no title found {url}")
                driver.execute_script(f"window.scrollBy(0, {500});")
                sleep(1)
                count += 1
        header_section: WebElement = driver.find_element(By.XPATH,
                                                         "//section[contains(@class, 'image-header__details--layout-listing')]")
        header_section_text = header_section.text
        text_parts = header_section_text.split("\n")
        date_string = ""
        found_date_title = False
        venue_string = ""
        found_venue_title = False
        for text_part in text_parts:
            if "DATE" in text_part:
                found_date_title = True
            elif found_date_title and not date_string:
                date_string = text_part
            elif "VENUE" in text_part or "LOCATION" in text_parts:
                found_venue_title = True
            elif found_venue_title and not venue_string:
                venue_string = text_part
            else:
                print(text_part)
        if venue_string and "wellington" not in venue_string.lower():
            venue_string += ", Wellington, New Zealand"
        print(f"date string {date_string} venue string {venue_string}")
        dates = WellingtonNZScrapper.get_dates(date_string)
        description: str = driver.find_element(By.CLASS_NAME, "typography").text
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue_string,
                         dates=dates,
                         url=url,
                         source=ScrapperNames.WELLINGTON_NZ,
                         event_type=category,
                         description=description)

    @staticmethod
    def slow_scroll_to_bottom(driver, category: str, previous_urls: Set[str], urls_file, out_file) -> List[EventInfo]:
        events = []
        height = driver.execute_script("return document.body.scrollHeight")
        scrolled_amount = 0
        event_urls: Set[tuple[str, str]] = set()
        while True:
            if scrolled_amount > height:
                break
            driver.execute_script(f"window.scrollBy(0, {400});")
            scrolled_amount += 400
            raw_events = driver.find_elements(By.CLASS_NAME, 'grid-item')
            for event in raw_events:
                event_url = event.find_element(By.TAG_NAME, 'a').get_attribute('href')
                if event_url in previous_urls:
                    continue
                previous_urls.add(event_url)
                event_urls.add((event_url, category))
        json.dump(list(event_urls), urls_file, indent=2)
        for part in event_urls:
            print(f"category: {part[1]} url: {part[0]}")
            try:
                event = WellingtonNZScrapper.get_event(part[0], part[1], driver)
                if event:
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("-" * 100)
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str]) -> List[EventInfo]:
        driver = webdriver.Chrome()
        urls_file = open(FileNames.WELLINGTON_NZ_URLS, mode="w")
        out_file = open(FileNames.WELLINGTON_NZ_EVENTS, mode="w")
        out_file.write("[\n")
        driver.get('https://www.wellingtonnz.com/visit/events?mode=list')
        driver.switch_to.window(driver.current_window_handle)
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(ec.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
        categories = driver.find_elements(By.CLASS_NAME, 'search-button-filter')

        categories = [(cat.text.replace("&", "+%26+").replace(" ", "").split("\n")[0], cat.text.split("\n")[1]) for cat
                      in categories]
        number_of_events = driver.find_element(By.CLASS_NAME, "pagination__position")
        number_of_events = re.findall("\d+", number_of_events.text)
        events_info = []
        for cat in categories:
            cat = cat[0]
            page = 1
            while number_of_events[0] != number_of_events[1]:
                driver.get(f'https://www.wellingtonnz.com/visit/events?mode=list&page={page}&categories={cat}')
                _ = wait.until(ec.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
                number_of_events = driver.find_element(By.CLASS_NAME, "pagination__position")
                number_of_events = re.findall("\d+", number_of_events.text)
                page += 1
            number_of_events = [0, 1]
            events_info += WellingtonNZScrapper.slow_scroll_to_bottom(driver, cat, previous_urls, urls_file, out_file)
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        driver.close()
        return events_info

# events = list(map(lambda x: x.to_dict(), sorted(WellingtonNZScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
