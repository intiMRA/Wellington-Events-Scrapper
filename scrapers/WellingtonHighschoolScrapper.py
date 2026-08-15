# https://www.cecwellington.ac.nz/w/courses/
from time import sleep
from playwright.sync_api import sync_playwright, Page, Locator

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry, wait_for_items
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from datetime import datetime
from dateutil import parser
from typing import List, Tuple, Set, Optional, TextIO
import json


class WellingtonHighschoolScrapper:
    @staticmethod
    def slow_scroll_to_bottom(page: Page):
        prev_height = 0
        while True:
            height = page.evaluate("document.body.scrollHeight")
            page.evaluate(f"window.scrollBy(0, {height})")
            sleep(1)
            if prev_height == height:
                break
            prev_height = height

    @staticmethod
    def get_all_event_dates(page: Page) -> List[datetime]:
        dates = []
        events_list: Locator = page.locator(".event-list")
        events = events_list.locator("[class*='event ']").all()
        for event in events:
            event_text = event.inner_text()
            regex = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            matches = re.search(regex, event_text)
            if not matches:
                continue
            date_day = matches.group(1)
            date_month = matches.group(2)
            matches = re.findall(r"\d{1,2}:\d{1,2}\s*[aAmMpP]{2}", event_text)
            if not matches:
                Logger.debug(event_text)
                continue
            hour = matches[0]
            dates.append(parser.parse(f"{date_day} {date_month} {hour}"))
            Logger.debug(f"day: {date_day} month: {date_month} hour: {hour}")

        return dates

    @staticmethod
    def get_event(url: str, category: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(1)
        title: str = page.locator(".page-title").first.inner_text()
        heros = page.locator(".image-hero")
        image_style = (heros.first.get_attribute("style") or "") if heros.count() else ""
        image_matches = re.findall(r'url\("([^"]+)"\)', image_style)
        image_url = image_matches[0] if image_matches else "no image"
        dates = WellingtonHighschoolScrapper.get_all_event_dates(page)
        description: str = page.locator(".content-field-text").first.inner_text()
        Logger.debug(dates)
        return EventInfo(name=title,
                         image=image_url,
                         venue="Wellington High School, 249 Taranaki Street, Te Aro, Wellington",
                         dates=dates,
                         url=url,
                         source=ScraperName.WELLINGTON_HIGH_SCHOOL,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls(previous_urls: Set[str], page: Page, urls_file: TextIO) -> Set[Tuple[str, str]]:
        urls_file.write("[\n")
        categories = WellingtonHighschoolScrapper.get_categories(page)
        event_urls: Set[Tuple[str, str]] = set()
        category_count = 1
        for category_parts in categories:
            category, url = category_parts
            Logger.info(f"fetching: {category} {category_count} of {len(categories)}")
            category_count += 1
            goto_with_retry(page, url)
            WellingtonHighschoolScrapper.slow_scroll_to_bottom(page)
            catalog = page.locator(".catalogue").first
            # New category page — wait for its items before snapshotting (scrolling alone doesn't
            # guarantee they've rendered).
            wait_for_items(catalog.locator(".catalogue-item"))
            elements = catalog.locator(".catalogue-item").all()
            for element in elements:
                event_url = element.locator("a").first.evaluate("a => a.href")
                if event_url in previous_urls:
                    continue
                previous_urls.add(event_url)
                url_tuple = (event_url, category)
                event_urls.add(url_tuple)
                json.dump(url_tuple, urls_file, indent=2)
                urls_file.write(",\n")
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def get_categories(page: Page) -> List[Tuple[str, str]]:
        goto_with_retry(page, "https://www.cecwellington.ac.nz/w/courses/")
        # Wait for the category filters to render — reading them too early would return no
        # categories, which silently drops every event.
        wait_for_items(page.locator(".radio-filter"))
        filters = page.locator(".radio-filter").all()
        categories: List[Tuple[str, str]] = []
        for f in filters:
            a_tag = f.locator("a").first
            categories.append((f.inner_text(), a_tag.evaluate("a => a.href")))
        return categories

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.WELLINGTON_HIGH_SCHOOL)
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.WELLINGTON_HIGH_SCHOOL)))
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            event_urls = WellingtonHighschoolScrapper.get_urls(previous_urls, page, urls_file)
            events: List[EventInfo] = []
            out_file.write("[\n")
            for parts in event_urls:
                event_url, category = parts
                Logger.info(f"category: {category} url: {event_url}")
                try:
                    event = WellingtonHighschoolScrapper.get_event(event_url, category, page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        Logger.warning(str(e))
                        json.dump(event_url, banned_file, indent=2)
                        banned_file.write(",\n")
                    else:
                        Logger.divider()
                        raise e
                Logger.divider()
            out_file.write("]\n")
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(WellingtonHighschoolScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
