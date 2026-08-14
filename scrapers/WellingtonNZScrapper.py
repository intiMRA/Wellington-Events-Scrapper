from datetime import datetime
from time import sleep

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from util.DateFormatting import DateFormatting
from model.EventInfo import EventInfo
import re
from dateutil import parser
from typing import List, Set, Optional, Tuple, TextIO
import json
from playwright.sync_api import sync_playwright, Page, Locator, Error as PlaywrightError


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
            Logger.warning(str(e))
        return dates

    @staticmethod
    def get_event(url: str, category: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(5)
        count = 0
        while True:
            try:
                image_url: str = page.locator("[class*='site-picture__img']").first.evaluate("img => img.src") or ""
                break
            except PlaywrightError:
                if count >= 10:
                    return None
                sleep(1)
                count += 1
        page.evaluate(f"window.scrollBy(0, {500})")
        sleep(1)
        count = 0
        while True:
            try:
                title: str = page.locator("[class*='image-header__title']").first.inner_text()
                break
            except PlaywrightError:
                if count >= 10:
                    raise Exception(f"no title found {url}")
                page.evaluate(f"window.scrollBy(0, {500})")
                sleep(1)
                count += 1
        header_section: Locator = page.locator("[class*='image-header__details--layout-listing']").first
        header_section_text = header_section.inner_text()
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
                Logger.debug(text_part)
        if venue_string and "wellington" not in venue_string.lower():
            venue_string += ", Wellington, New Zealand"
        Logger.debug(f"date string {date_string} venue string {venue_string}")
        dates = WellingtonNZScrapper.get_dates(date_string)
        try:
            description: str = page.locator(".typography").first.inner_text()
        except PlaywrightError:
            try:
                description = page.locator(".image-header__intro").first.inner_text()
            except PlaywrightError:
                description = title
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue_string,
                         dates=dates,
                         url=url,
                         source=ScraperName.WELLINGTON_NZ,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO) -> Set[Tuple[str, str]]:
        goto_with_retry(page, "https://www.wellingtonnz.com/visit/events?mode=list")
        page.locator(".pagination__position").first.wait_for(state="attached")
        sleep(1)
        page.evaluate("window.scrollBy(0, 1500)")
        sleep(1)
        button = page.locator("[class*='filters-button__icon']").all()[-1]
        button.click()
        sleep(1)
        categories = page.locator(".search-button-filter").all()
        new_categories = []
        for cat in categories:
            if len(cat.inner_text().split("\n")) > 1:
                new_categories.append((cat.inner_text().replace("&", "+%26+").replace(" ", "").split("\n")[0], cat.inner_text().split("\n")[1]))
        categories = new_categories
        count_locator = page.locator(".pagination__position").first
        number_of_events = re.findall(r"\d+", count_locator.text_content() or "")
        event_urls: Set[Tuple[str, str]] = set()
        urls_file.write("[\n")
        cat_count = 1
        for cat in categories:
            Logger.info(f"fetching: {cat[0]} {cat_count} out of {len(categories)}")
            category = cat[0]
            cat_count += 1
            page_num = 1
            while number_of_events[0] != number_of_events[1]:
                goto_with_retry(page, f"https://www.wellingtonnz.com/visit/events?mode=list&page={page_num}&categories={category}")
                count_locator = page.locator(".pagination__position").first
                count_locator.wait_for(state="attached")
                number_of_events = re.findall(r"\d+", count_locator.text_content() or "")
                page_num += 1
            number_of_events = [0, 1]
            # The &page=N URL is cumulative (page 2 = 50 items, page 3 = 75, ...), so the loop
            # above has now loaded every event for the category — collect them all.
            for event in page.locator(".grid-item").all():
                event_url = event.locator("a").first.evaluate("a => a.href")
                if event_url in previous_urls:
                    continue
                previous_urls.add(event_url)
                event_urls.add((event_url, category))
                json.dump((event_url, category), urls_file, indent=2)
                urls_file.write(",\n")
        urls_file.write("]\n")
        return event_urls
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.WELLINGTON_NZ)
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.WELLINGTON_NZ)))
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            events = []
            urls = WellingtonNZScrapper.get_urls(page, previous_urls, urls_file)
            out_file.write("[\n")
            for part in urls:
                Logger.info(f"category: {part[1]} url: {part[0]}")
                try:
                    event = WellingtonNZScrapper.get_event(part[0], part[1], page)
                    if event:
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        json.dump(part[0], banned_file, indent=2)
                        banned_file.write(",\n")
                        Logger.warning(str(e))
                    else:
                        Logger.divider()
                        raise e
                Logger.divider()
            out_file.write("]\n")
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(WellingtonNZScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
