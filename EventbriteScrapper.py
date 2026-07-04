from datetime import datetime
import FileUtils
from selenium.webdriver.remote.webelement import WebElement

import ScrapperNames
from DateFormatting import DateFormatting

from selenium.webdriver.common.by import By
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil.relativedelta import relativedelta
from dateutil import parser
import json
from time import sleep
from typing import List, Tuple, Set, Optional


class EventbriteScrapper:
    @staticmethod
    def get_all_dates(driver: webdriver) -> List[datetime]:
        sleep(1)
        dates = []
        try:
            driver.find_element(By.XPATH, "//div[contains(., 'looking for was not found')]")
            return []
        except:
            pass
        date_div_text: str = driver.find_element(By.XPATH, "//div[@data-testid='event-datetime']").text
        if "Multiple dates" in date_div_text:
            return EventbriteScrapper.parse_multiple_dates(driver)
        date_div_text_comma_count = len(date_div_text.split(",") )
        bar_count = len(date_div_text.split("-"))
        print(date_div_text)
        if date_div_text_comma_count < 3 and bar_count <= 2:
            print("type 1")
            date_text = date_div_text.replace("  •  ", " ").split(" - ")[0]
            if date_text:
                try:
                    dates.append(DateFormatting.replace_year(parser.parse(date_text.replace(" at ", " ").replace(" Starts", " "))))
                    return dates
                except:
                    pass
        if date_div_text_comma_count == 3:
            print("type 2")
            parts = date_div_text.split("  •  ")
            time_part = parts[1].split("-")[0].strip() if len(parts) > 1 else ""
            date_parts = parts[0].split("-")
            for dp in date_parts:
                date_str = dp.split(",", 1)[1].strip()
                date_text = f"{date_str} {time_part}".strip()
                dates.append(DateFormatting.replace_year(parser.parse(date_text)))
            return dates
        if bar_count > 2:
            print("type 3")
            parts = date_div_text.split("-")
            first_date, second_date, _ = parts
            second_date, time_string = second_date.split("  •  ")
            dates.append(parser.parse(f"{first_date} {time_string}"))
            dates.append(parser.parse(f"{second_date} {time_string}"))
        return dates

    @staticmethod
    def parse_multiple_dates(driver: webdriver) -> List[datetime]:
        try:
            driver.find_element(By.XPATH, "//button[@data-testid='explore-similar-events-button']")
            return []
        except:
            pass
        dates = []
        driver.find_element(By.XPATH, "//button[@data-testid='conversion-bar-checkout-button']").click()
        sleep(3)
        iframe_element = driver.find_element(By.XPATH, "//iframe[contains(@id, 'eventbrite-widget-modal')]")
        driver.switch_to.frame(iframe_element)
        calendar_containers = driver.find_elements(By.XPATH, "//div[@data-testid='calendar-container']")
        if calendar_containers:
            month_sections = calendar_containers[0].find_elements(By.XPATH, ".//div[contains(@class, 'Stack_root')]")
            current_month = ""
            for section in month_sections:
                month_elements = section.find_elements(By.XPATH, ".//p[contains(@class, 'CompactCalendar-module__monthName')]")
                if month_elements:
                    current_month = month_elements[0].text
                day_elements = section.find_elements(By.XPATH, ".//p[contains(@class, 'CompactCalendar-module__dateText')]")
                time_elements = section.find_elements(By.XPATH, ".//p[contains(@class, 'CompactCalendar-module__timeSlotText')]")
                if day_elements and current_month:
                    day = day_elements[0].text
                    time_text = time_elements[0].text if time_elements else ""
                    date_str = f"{current_month} {day} {time_text}".strip()
                    dates.append(DateFormatting.replace_year(parser.parse(date_str)))
        else:
            try:
                date_text = driver.find_element(By.XPATH, "//p[contains(@class, 'EventInfoCard-module__dateWrapper')]").text
                time_elements = driver.find_elements(By.XPATH, "//p[contains(@class, 'TimeSlotList_sessionText')]")
                time_text = time_elements[0].text.split(" - ")[0].strip() if time_elements else ""
                date_str = f"{date_text} {time_text}".strip()
                dates.append(DateFormatting.replace_year(parser.parse(date_str)))
            except:
                pass
        driver.switch_to.default_content()
        return dates

    @staticmethod
    def get_categories(driver: webdriver) -> List[Tuple[str, str]]:
        categories = []
        sleep(1)
        view_more_button = driver.find_element(By.XPATH, "//button[@aria-controls='view-more-category']")
        view_more_button.click()
        sleep(2)
        cat_list = driver.find_element(By.XPATH, "//ul[@id='view-more-category']")
        cats = cat_list.find_elements(By.TAG_NAME, "li")
        for cat in cats:
            link = cat.find_element(By.TAG_NAME, "a").get_attribute("href")
            category = (cat.text, link)
            categories.append(category)
        return categories

    @staticmethod
    def get_event(url: str, driver: webdriver, category: str, banned_file) -> Optional[EventInfo]:
        driver.get(url)
        sleep(1)
        try:
            bar = driver.find_element(By.XPATH, "//div[contains(@class, 'EventSignalsBar_signals')]")
            if "sales ended" in bar.text.lower():
                return None
        except:
            pass
        try:
            location_text: str = driver.find_element(By.XPATH, "//a[contains(@data-testid, 'event-venue')]").text
        except:
            return None
        if "leadflake" in location_text.lower():
            print(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            return None
        venue = location_text
        try:
            title: str = driver.find_element(By.XPATH, "//h1[contains(@data-testid, 'event-title')]").text
        except:
            raise Exception("no title")
        try:
            image_url = driver.find_element(By.XPATH, "//img[@data-testid='hero-img']").get_attribute("src")
        except:
            image_url = ""
        event_link: str = url
        try:
            driver.find_element(By.XPATH, "//button[contains(@calss, 'ViewDetailsButton_button')]").click()
            sleep(1)
        except:
            pass
        try:
            button: WebElement = driver.find_element(By.XPATH, "//button[contains(@data-heap-id, 'Listings - Description - Read more - Click')]")
            button.click()
            sleep(1)
            description: str = driver.find_element(By.XPATH, "//div[contains(@class,'AboutThisEventEmbedded_container')]").text
        except:
            try:
                description: str = driver.find_element(By.XPATH,
                                                       "//div[contains(@data-testid,'section-wrapper-overview')]").text
            except:
                try:
                    description: str = driver.find_element(By.XPATH,
                                                       "//div[contains(@class,'Overview_summary')]").text
                except:
                    raise Exception("no description")
        dates: List[datetime] = EventbriteScrapper.get_all_dates(driver)
        if not dates:
            date_matches = re.findall(r"\d{1,2}\s\w+\d{0,4}", title)
            hour = "1:01AM"
            hour_matches = re.findall(r"\d{1,2}\s:\d{2}[aAmMpP]{0,2}", title)
            if hour_matches:
                hour = hour_matches[0]
            for date_match in date_matches:
                try:
                    dates.append(parser.parse(f"{date_match} {hour}"))
                except:
                    continue

        if "copyright" in description:
            print(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            return None
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=event_link,
                         source=ScrapperNames.EVENT_BRITE,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls(driver: webdriver, previous_urls: Set[str]) -> Set[Tuple[str, str]]:
        urls = set()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        categories = EventbriteScrapper.get_categories(driver)
        total_cats = len(categories)
        cat_count = 1
        for category in categories:
            cat_name, link = category
            print(f"fetching: {cat_name}, {cat_count} out of {total_cats}")
            cat_count += 1
            print("_" * 100)
            driver.get(link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            # &start_date=2025-05-23&end_date=2025-06-29
            new_url = (driver.current_url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            driver.get(new_url)
            current_page = 1
            while True:
                next_url = re.sub(r"page=\d+", f"page={current_page}", driver.current_url)
                driver.get(next_url)
                try:
                    sleep(1)
                    pagination = driver.find_element(By.XPATH, "//li[@data-testid='pagination-parent']")
                    first_page, last_page = pagination.text.split(" of ")
                    first_page = int(first_page)
                    last_page = int(last_page)
                    if first_page > last_page:
                        break
                except Exception as e:
                    print(f"error finding paginstion: {e}")
                current_page += 1
                # search-event
                sleep(2)
                cards = driver.find_elements(By.XPATH, "//div[@data-testid='search-event']")
                print(f"len cards: {len(cards)}")
                for card in cards:
                    title_tag = card.find_element(By.CLASS_NAME, "event-card-link ")
                    event_url = title_tag.get_attribute("href")
                    texts = card.text.split("\n")

                    tags = [
                        "Sales end soon",
                        "Selling quickly",
                        "Nearly full",
                        "Just added",
                        "Not Yet On Sale"
                    ]

                    sold_tags = [
                        "Sold Out",
                        "Sales Ended",
                        "Unavailable",
                        "Sales ended"
                    ]
                    if texts[0] in sold_tags:
                        continue
                    if texts[0] in tags:
                        texts = texts[1:]
                    if len(texts) < 3:
                        continue
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    url_tuple = (event_url, cat_name)
                    urls.add(url_tuple)
                print(f"len cards: {len(urls)}")
        return urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        fetch_urls = True
        categories = set()
        if not fetch_urls:
            categories = FileUtils.load_from_files(ScrapperNames.EVENT_BRITE)[1]
        events = []
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.EVENT_BRITE)))
        driver = webdriver.Chrome()
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.EVENT_BRITE)
        if fetch_urls:
            categories = EventbriteScrapper.get_urls(driver, previous_urls)
        json.dump(list(categories), urls_file, indent=2)
        urls_file.close()
        out_file.write("[\n")
        for category in categories:
            if (not fetch_urls) and category[0] in previous_urls:
                continue
            url, category_name = category
            print(f"category: {category_name} url: {url}")
            try:
                event: Optional[EventInfo] = EventbriteScrapper.get_event(url, driver, category_name, banned_file)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    json.dump(url, banned_file, indent=2)
                    banned_file.write(",\n")
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("_" * 100)
        driver.close()
        out_file.write("]\n")
        out_file.close()
        return events

# previous_events = FileUtils.load_from_files(ScrapperNames.EVENT_BRITE)[0]
# previous_urls = set(e["url"] for e in previous_events)
# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.fetch_events(previous_urls, set()), key=lambda k: k.name.strip())))
