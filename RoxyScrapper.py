import json

from future.backports.datetime import timedelta
from numpy.core.defchararray import title
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import CurrentFestivals
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, Dict
from time import sleep

class RoxyScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(3)
        title = driver.find_element(By.CLASS_NAME, "single-movie__title").text
        sticky_wrapper: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'sticky-inner-wrapper')]")
        image_url = sticky_wrapper.find_element(By.TAG_NAME, "img").get_attribute("src")
        time_elements = driver.find_elements(By.CLASS_NAME, "single-session")
        dates = []
        for time_element in time_elements:
            date_string: str = time_element.find_element(By.CLASS_NAME, "single-session__date").text
            date_string = date_string.split(" | ")[-1]
            dates.append(parser.parse(date_string))
        description = driver.find_element(By.CLASS_NAME, "single-movie__description").text
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue="The Roxy Cinema, 5 Park Road, Miramar, Wellington",
                         source=ScrapperNames.ROXY,
                         event_type="Film & Media",
                         description=description)

    @staticmethod
    def get_event_fom_page(url: str, driver: webdriver, previous_urls) -> Optional[EventInfo]:
        driver.get(url)
        sleep(3)
        event_url = driver.find_element(By.CLASS_NAME, "poster-portrait-link").get_attribute("href")
        if event_url in previous_urls:
            return None
        return RoxyScrapper.get_event(event_url, driver)

    @staticmethod
    def get_festival_urls(url: str, driver: webdriver) -> Set[str]:
        driver.get(url)
        sleep(3)
        driver.execute_script(f"window.scrollBy(0, {400});")
        height = driver.execute_script("return document.body.scrollHeight")

        scrolled_amount = 0
        while True:
            if scrolled_amount > height:
                break
            driver.execute_script(f"window.scrollBy(0, {400});")
            scrolled_amount += 400
            sleep(1)
        films = driver.find_elements(By.CLASS_NAME, "poster-portrait-link")
        return set([film.get_attribute("href") for film in films])

    @staticmethod
    def get_events(films_urls: Set[str], driver: webdriver, previous_urls: Set[str], out_file) -> List[EventInfo]:
        events = []
        for films_url in films_urls:
            print(f"url: {films_url}")
            try:
                event = RoxyScrapper.get_event_fom_page(films_url, driver, previous_urls)
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
            print("-" * 100)
        return events

    @staticmethod
    def get_festivals(festivals: List[Dict[str, str]], driver: webdriver):
        for festivals in festivals:
            festival_name = festivals['name']
            festival_name = festival_name.lower()
            festival_name = festival_name.title()
            file_festival_name = festival_name.lower().replace(" ", "-")
            festival_url = festivals['url']
            print(f"festival: {festival_name}")
            CurrentFestivals.CURRENT_FESTIVALS.append("RoxyFestival")
            CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
                "id": "RoxyFestival",
                "name": festival_name,
                "icon": "movie",
                f"url": f"https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/{file_festival_name}.json"
            })

            festival_file = open(f"{file_festival_name}.json", mode="w")
            event_urls = RoxyScrapper.get_festival_urls(festival_url, driver)
            events = []
            for event_url in event_urls:
                print(f"fetching: {event_url}")
                try:
                    event = RoxyScrapper.get_event(event_url, driver)
                    if event:
                        events.append(event.to_dict())
                except Exception as e:
                    if "No dates found for" in str(e):
                        print("-" * 100)
                        print(e)
                    else:
                        print("-" * 100)
                        raise e
                print("-" * 100)
            json.dump({"events": events}, festival_file, indent=2)
            festival_file.close()
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.ROXY)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.ROXY)))
        driver = webdriver.Chrome()
        driver.get("https://www.roxycinema.co.nz/")
        sleep(3)
        more_button = driver.find_element(By.XPATH, "//button[contains(@class, 'primary-menu__link--more')]")
        more_button.click()
        festivals_urls: List[Dict[str, str]] = []
        films_urls = set()
        values_to_extract = ["EAT THE FILM", "FEAST YOUR EYES"]
        navs = driver.find_elements(By.XPATH, "//a[contains(@class, 'menu__link')]")
        processed = set()
        for nav in navs:
            text = nav.text
            url = nav.get_attribute("href")
            if text in processed:
                continue
            if "festival" in text.lower():
                festivals_urls.append({"name": text, "url": url})
            elif text in values_to_extract:
                films_urls.add(url)
            processed.add(text)
        out_file.write("[\n")
        events = RoxyScrapper.get_events(films_urls, driver, previous_urls, out_file)
        out_file.write("]\n")
        RoxyScrapper.get_festivals(festivals_urls, driver)
        driver.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

events = list(map(lambda x: x.to_dict(), sorted(RoxyScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))