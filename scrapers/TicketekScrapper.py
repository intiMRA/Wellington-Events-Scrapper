import json
import random

from datetime import datetime
from time import sleep
from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from dateutil import parser
from typing import List, Optional, Set, Tuple, TextIO
from playwright.sync_api import sync_playwright, Page, BrowserContext
from util.PlaywrightUtils import goto_with_retry, launch_stealth, human_delay
from util.Logger import Logger

class TicketekScrapper:
    @staticmethod
    def extract_date(page: Page) -> List[datetime]:
        dates: List[datetime] = []
        sleep(random.uniform(1, 2))
        date_lines = page.locator(".selectDateBlock").first.inner_text().split("\n")
        date_string: str = date_lines[1] if len(date_lines) > 1 else date_lines[0]
        matches: List[str] = re.findall(r"\d{1,2}\s*[aA-zZ]{3,4}\s*\d{0,4}", date_string)
        hours: List[str] = re.findall(r"\d{1,2}\s*:\s*\d{1,2}[aAmMpP]{0,2}", date_string)
        hour = "1:01AM"
        if hours:
            hour = hours[0]
        for match in matches:
            dates.append(parser.parse(f"{match} {hour}"))
        return dates

    @staticmethod
    def get_event(url: str, category: str, page: Page, browser: BrowserContext, previous_urls: Set[str], banned_file: TextIO) -> Optional[
        List[EventInfo]]:
        if url in previous_urls:
            return []
        goto_with_retry(page, url)
        human_delay(page, 2, 3)
        sub_events = page.locator(".event-item").all()
        if sub_events:
            Logger.info("fetching sub events: ")
            sub_events_urls = []

            for event in sub_events:
                venue_text: str = event.locator(".event-venue-dates").first.inner_text()
                sub_url: str = (event.locator(".event-buttons").first
                                .locator("a").first.evaluate("a => a.href"))
                if sub_url in previous_urls:
                    continue
                if "wellington" in venue_text.lower():
                    sub_events_urls.append(sub_url)
                else:
                    Logger.warning(f"banning {sub_url} because not in wellington")
                    json.dump(sub_url, banned_file, indent=2)
                    banned_file.write(",\n")
            if not sub_events_urls:
                Logger.warning(f"banning {url} because not urls found")
                json.dump(url, banned_file, indent=2)
                banned_file.write(",\n")
                return []
            sub_page = browser.new_page()
            events_info: List[EventInfo] = []
            for sub_url in sub_events_urls:
                Logger.info(f"sub event url: {sub_url}")
                parsed_events = TicketekScrapper.get_event(sub_url, category, sub_page, browser, previous_urls, banned_file)
                if parsed_events:
                    for parsed_event in parsed_events:
                        events_info.append(parsed_event)
            sub_page.close()
            if not events_info:
                json.dump(url, banned_file, indent=2)
                banned_file.write(",\n")
                Logger.warning(f"banning {url} because none in wellington")
            return events_info
        if page.locator("[class*='alert-warning']").count():
            alert = page.locator("[class*='alert-warning']").first.inner_text()
            if "unavailable" in alert:
                return None
        title: str = page.locator(".sectionHeading").first.inner_text()
        if url in previous_urls:
            Logger.warning(f"banning {url} because event was already fetched")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            return []
        previous_urls.add(url)
        dates = TicketekScrapper.extract_date(page)
        image_url: str = page.locator(".desktop-tablet-banner").first.evaluate("banner => banner.src") or ""
        venue_lines = page.locator(".selectVenueBlock").first.inner_text().split("\n")
        venue: str = venue_lines[1] if len(venue_lines) > 1 else venue_lines[0]
        description: str = page.locator(".info-details").first.inner_text()
        Logger.info(f"title: {title}")
        human_delay(page, 1, 3)
        Logger.info(f"description: {description}")
        return [EventInfo(name=title,
                          dates=dates,
                          image=image_url,
                          url=url,
                          venue=venue,
                          source=ScraperName.TICKETEK,
                          event_type=category,
                          description=description)]

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO) -> Set[Tuple[str, str]]:
        goto_with_retry(page, "https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington")
        cats = page.locator(".cat-nav-item").all()
        cats = [(cat.inner_text(), cat.evaluate("a => a.href").split("c=")[-1]) for cat in cats if
                len(cat.evaluate("a => a.href").split("c=")) > 1 and len(cat.inner_text()) > 0]
        cats.append(("Other", "Other"))
        event_urls: Set[Tuple[str, str]] = set()
        for categoryName, categoryTag in cats:
            Logger.debug(f"urls for categoryName: {categoryName}, categoryTag: {categoryTag}")
            page_counter = 1
            while True:
                goto_with_retry(page, f"https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington&page={page_counter}&c={categoryTag}")
                buttons = page.locator(".resultBuyNow").all()
                content_events = page.locator(".contentEvent").all()
                for button, content_event in zip(buttons, content_events):
                    event_url = button.locator("a").first.evaluate("a => a.href")
                    if event_url in previous_urls:
                        continue
                    event_urls.add((event_url, categoryName))
                    json.dump((event_url, categoryName), urls_file, indent=2)
                    urls_file.write(",\n")
                page_counter += 1
                page.evaluate(f"window.scrollTo({random.randint(0, 300)}, {random.randint(300, 700)});")
                human_delay(page, 2, 3)
                if page.locator(".noResultsMessage").count():
                    break
                pagination = page.locator(".paginationResults").first.inner_text().split("-")[1]
                start, end = pagination.split(" of ")
                if start == end:
                    break
        human_delay(page, 2, 3)
        return event_urls
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        fetch_urls = True
        event_urls = set()
        if not fetch_urls:
            event_urls = FileUtils.load_from_files(ScraperName.TICKETEK)[1]
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.TICKETEK)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.TICKETEK)))
        events_info: List[EventInfo] = []
        with sync_playwright() as playwright:
            context = launch_stealth(playwright, headless=False)
            page = context.new_page()
            if fetch_urls:
                event_urls = TicketekScrapper.get_urls(page, previous_urls, urls_file)
            else:
                json.dump(list(event_urls), urls_file, indent=2)
            out_file.write("[\n")
            for part in event_urls:
                Logger.info(f"category: {part[1]} url: {part[0]}")
                if part[0] in previous_urls:
                    continue
                try:
                    events = TicketekScrapper.get_event(part[0], part[1], page, context, previous_urls, banned_file)
                    if not events:
                        continue
                    for event in events:
                        if event:
                            events_info.append(event)
                            json.dump(event.to_dict(), out_file, indent=2)
                            out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        Logger.warning(f"banning {part[0]} because no date was found")
                        json.dump(part[0], banned_file, indent=2)
                        banned_file.write(",\n")
                        Logger.warning(str(e))
                    else:
                        Logger.divider()
                        Logger.warning(str(e))
                human_delay(page, 1, 3)
                Logger.divider()
            out_file.write("]\n")
        out_file.close()
        banned_file.close()
        urls_file.close()
        return events_info

# events = list(map(lambda x: x.to_dict(), sorted(TicketekScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
