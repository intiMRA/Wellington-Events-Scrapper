import random
import subprocess
from time import sleep
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import FileUtils
import ScrapperNames
from EventInfo import EventInfo
import re
from datetime import datetime
from dateutil import parser
import undetected_chromedriver as uc
from typing import List, Optional, Set, Tuple
import json


class HumanitixScrapper:

    @staticmethod
    def get_dates_from_event(driver: uc, multiple_dates: bool) -> List[datetime]:
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
            date_strings = driver.find_elements(By.CLASS_NAME, "datetime")
            if not date_strings:
                date_strings = driver.find_elements(By.XPATH, "//div[contains(@class, 'datetime')]")
            date_string = date_strings[0].text.split("\n")[0]
            reg = r"(\d{1,2}\s[aA-zZ]{3}\s*[0-9]*,\s[aA-zZ0-9:]*[AMPamp]{2})"
            matches = re.findall(reg, date_string)
            year = re.findall(r"\d{4}", date_string)
            if len(matches) > 1:
                for match in matches:
                    if year:
                        match += f" {year[0]}"
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
    def get_event(url: str, category: str, multiple_dates: bool, driver: uc) -> Optional[EventInfo]:
        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "titlewrapper").text.split("\n")[0]
        try:
            image_url: str = driver.find_element(By.CLASS_NAME, "banner").find_element(By.TAG_NAME,
                                                                                       "img").get_attribute('src')
        except:
            image_url = ""
        try:
            location = driver.find_element(By.CLASS_NAME, "EventLocation").find_element(By.CLASS_NAME, "address").text
            venue: str = location.split("\n")[1]
        except:
            try:
                venue: str = driver.find_element(By.CLASS_NAME, "address").text
            except:
                return  None
        venue = venue.split("  ·  ")[0]
        print(f"venue: {venue}")
        dates: List[datetime] = HumanitixScrapper.get_dates_from_event(driver, multiple_dates)
        description: str = ""
        try:
            description = driver.find_element(By.CLASS_NAME, "RichContent").text
        except:
            print("no description")
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=url,
                         source=ScrapperNames.HUMANITIX,
                         event_type=category,
                         description=description)
    @staticmethod
    def get_urls(driver: uc, previous_urls: Set[str], urls_file) -> Set[Tuple[str, str, bool]]:
        urls_file.write("[\n")
        driver.get('https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463')
        sleep(random.uniform(2, 4))
        categories_button = driver.find_element(By.XPATH, "//button[contains(., 'Categories')]")
        categories_button.click()
        categories = driver.find_element(By.ID, "listbox-categories").find_elements(By.TAG_NAME, "li")
        categories = [(HumanitixScrapper.format_input(category.text), category.text) for category in categories]
        event_urls: Set[Tuple[str, str, bool]] = set()
        for category, categoryName in categories:
            print("cat: ", category, " ", categoryName)
            page = 0
            while True:

                url = f'https://humanitix.com/nz/search/nz--wellington-region--wellington?countryAndLocation=nz--wellington-region--wellington&page={page}&categories={category}'
                driver.get(url)
                sleep(random.uniform(1, 2))
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
                    url_tuple = (event_url, categoryName, multiple_dates)
                    event_urls.add(url_tuple)
                    json.dump(url_tuple, urls_file, indent=2)
                    urls_file.write(",\n")
                page += 1
                sleep(random.uniform(1, 3))
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        fetch_urls = True
        event_urls = set()
        if not fetch_urls:
            event_urls = FileUtils.load_from_files(ScrapperNames.HUMANITIX)[1]
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.HUMANITIX)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.HUMANITIX)))
        events: List[EventInfo] = []
        subprocess.run(['pkill', '-f', 'Google Chrome'])
        options = uc.ChromeOptions()

        # Set up browser to appear more human-like
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        options.add_argument(
            f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 115)}.0.0.0 Safari/537.36")

        version = ChromeDriverManager().driver.get_browser_version_from_os()
        major_version = int(version.split('.')[0])

        driver = uc.Chrome(
            options=options,
            version_main=major_version,
            headless=False,  # Headless mode is more easily detected
            use_subprocess=True
        )
        if fetch_urls:
            event_urls = HumanitixScrapper.get_urls(driver, previous_urls, urls_file)
        else:
            json.dump(list(event_urls), urls_file, indent=2)
        out_file.write("[\n")
        for part in event_urls:
            if (not fetch_urls) and part[0] in previous_urls:
                continue
            print(f"category: {part[1]} url: {part[0]}")
            try:
                event = HumanitixScrapper.get_event(part[0], part[1], part[2], driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    json.dump(part[0], banned_file, indent=2)
                    banned_file.write(",\n")
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("-" * 100)
        out_file.write("]\n")
        urls_file.close()
        banned_file.close()
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(HumanitixScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
