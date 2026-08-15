import random
from time import sleep

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, Tuple, TextIO
import json
from datetime import timedelta
from playwright.sync_api import sync_playwright, Page, Locator
from util.PlaywrightUtils import goto_with_retry, launch_stealth, stealth_page, wait_for_items
from util.Logger import Logger
class AllEventsInScrapper:
    @staticmethod
    def get_event(url: str, category: Optional[str], page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(random.uniform(2, 3))
        if page.get_by_text("Event Ended").count():
            return None
        if not page.locator(".eps-heading-1").all():
            return None
        title = page.locator(".eps-heading-1").first.inner_text()
        image_url = page.locator(".event-banner").first.evaluate("img => img.src")
        venue_texts = [event_text.inner_text() for event_text in page.locator("[class*='event-location']").all()]
        if len(venue_texts) > 1 and venue_texts[0] in venue_texts[1]:
            venue_texts = [venue_texts[0]]
        venue = ",".join(venue_texts)
        Logger.debug(f"venue: {venue}")
        if not page.locator("[class*='event-time-label']").all():
            return None
        date_strings = page.locator("[class*='event-time-label']").first.inner_text().split(" - ")
        dates = []
        for date_string in date_strings:
            date_string = " ".join(date_string.split(",")[1:])
            original_date_string = date_string
            date_string = date_string.split(" (")[0]
            date_string = date_string.split(" to")[0]
            date_string = date_string.replace(" • ", " ")
            try:
                date = parser.parse(date_string)
            except Exception as e:
                Logger.error(f"Error parsing date {date_string} {e}")
                return None
            if "nzst" in original_date_string.lower():
                date = date + timedelta(hours=10)
            dates.append(date)
        if not dates:
            return None
        if not page.locator("[class*='event-description']").all():
            Logger.error(f"Event description {title} not found")
            return None
        description = page.locator("[class*='event-description']").first.inner_text()
        Logger.info(f"event cat {category}")
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScraperName.ALL_EVENTS_IN,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls_for_category(category_url: str, page: Page, previous_urls: Set[str], previous_titles: Set[str], category_name: str, urls_file: TextIO) -> Set[Tuple[str, str]]:
        event_urls = set()
        goto_with_retry(page, category_url)
        sleep(random.uniform(2, 3))
        if page.locator(".cat-not-found-section").all():
            return set()

        container: Locator = page.locator("[class*='eventlist-container']").first
        height = container.evaluate("document.body.scrollHeight")
        scrolled_amount = 0
        more_count = 0
        height = max(height, 800)
        while True:
            if scrolled_amount > height or more_count > 1:
                Logger.debug("finished scroll")
                break
            page.evaluate(f"window.scrollBy(0, {400});")
            scrolled_amount += 400
            sleep(1)
            if page.locator("[class*='eventlist-container']").all():
                container: Locator = page.locator("[class*='eventlist-container']").first
                height = container.evaluate("document.body.scrollHeight")
            if page.locator("#show_more_events").all():
                page.locator("#show_more_events").first.click()
                container: Locator = page.locator("[class*='eventlist-container']").first
                height = container.evaluate("document.body.scrollHeight")
                sleep(2)
                more_count += 1
                Logger.info("loaded more")
        sleep(2)
        container: Locator = page.locator("[class*='eventlist-container']").first
        wait_for_items(container.locator("[class*='link']"))
        events = container.locator("[class*='link']").all()
        Logger.info(f"event count: {len(events)}")
        for event in events:
            event_url = event.get_attribute("data-link")
            if not event_url:
                continue
            title = event.locator(".title").first.inner_text()
            if event_url in previous_urls or title in previous_titles:
                continue
            previous_titles.add(title)
            previous_urls.add(event_url)
            event_tuple = (category_name, event_url)
            event_urls.add(event_tuple)
            json.dump(event_tuple, urls_file)
            urls_file.write(",\n")
        return event_urls
    @staticmethod
    def get_urls(city_url: str, previous_urls: Set[str], previous_titles: Set[str], categories: Set[Tuple[str, str]], urls_file, page: Page) -> Set[Tuple[str, str]]:
        event_urls = set()
        cat_count = len(categories)
        current_cat = 1
        for category in sorted(categories):
            category_name = category[0]
            category_url = category[1]
            Logger.info(f"fetching: {category_name} for {city_url} {current_cat} of {cat_count}")
            current_cat += 1
            event_urls = event_urls.union(AllEventsInScrapper.get_urls_for_category(category_url, page, previous_urls, previous_titles, category_name, urls_file))
        return event_urls

    @staticmethod
    def get_categories(url: str, page: Page) -> Set[Tuple[str, str]]:
        Logger.info(f"getting: {url}")
        categories = set()
        goto_with_retry(page, url)
        sleep(2)
        if page.locator("#login-top").count():
            page.locator("#login-top").first.click()
            sleep(2)
            if page.get_by_text("Continue with Facebook").all():
                with page.expect_popup() as popup_info:
                    page.get_by_text("Continue with Facebook").first.click()
                new_page = popup_info.value
                new_page.wait_for_load_state()
                new_page.get_by_text("Continue as Peter").first.click()
                sleep(10)
        sleep(1)
        if page.locator(".remaining-cat-count").count():
            page.locator(".remaining-cat-count").first.click()
        sleep(1)
        wait_for_items(page.locator("[class*='cat-item']"))
        category_items: List[Locator] = page.locator("[class*='cat-item']").all()
        for category_item in category_items:
            category_name = category_item.inner_text()
            category_url = category_item.evaluate("a => a.href").split("?")[0]
            categories.add((category_name, category_url))
        return categories
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            fetch_urls = True
            event_urls = set()
            if not fetch_urls:
                event_urls = FileUtils.load_from_files(ScraperName.ALL_EVENTS_IN)[1]
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.ALL_EVENTS_IN)
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.ALL_EVENTS_IN)))
            city_urls = [
                "https://allevents.in/wellington",
                "https://allevents.in/lower-hutt",
                "https://allevents.in/upper-hutt",
                "https://allevents.in/porirua",
                "https://allevents.in/waikanae",
                "https://allevents.in/paraparaumu",
            ]
            # Shared stealth Chrome profile (persistent — keeps the AllEventsIn login across runs).
            context = launch_stealth(playwright, headless=False)
            page = stealth_page(context)
            if fetch_urls:
                urls_file.write("[\n")
                for city_url in city_urls:
                    categories = AllEventsInScrapper.get_categories(city_url, page)
                    event_urls = event_urls.union(
                        AllEventsInScrapper.get_urls(city_url, previous_urls, previous_titles, categories, urls_file, page))
                    # Reset the session between cities (a user_data_dir can only be held by one
                    # context at a time), mirroring the old driver.close() + reopen.
                    context.close()
                    context = launch_stealth(playwright, headless=False)
                    page = stealth_page(context)
                urls_file.write("]\n")
            else:
                json.dump(list(event_urls), urls_file, indent=2)
            Logger.info("done fetching urls")

            out_file.write("[\n")
            events = []
            for event_urlParts in event_urls:
                category_name = event_urlParts[0]
                event_url = event_urlParts[1]
                if not fetch_urls and event_url in previous_urls:
                    continue
                Logger.info(f"category: {category_name} url: {event_url}")
                try:
                    event = AllEventsInScrapper.get_event(event_url, category_name, page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.warning(str(e))
                    else:
                        raise e
                Logger.divider()
            out_file.write("]\n")
            context.close()
        out_file.close()
        banned_file.close()
        urls_file.close()
        return []

# events = list(map(lambda x: x.to_dict(), sorted(AllEventsInScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
