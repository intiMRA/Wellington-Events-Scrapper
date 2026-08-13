import json
import random
import re
from playwright.sync_api import sync_playwright, Page, Locator

from util import CurrentFestivals
from util.DateFormatting import DateFormatting
from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry
from util.Logger import Logger
from util import paths
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, TextIO
from time import sleep

class FringeScrapper:
    @staticmethod
    def get_event(url: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(random.uniform(1,3))
        title = page.locator("[class*='primary-color']").first.inner_text()

        image_element = page.locator("[class*='event-image-square']").first
        image_url = image_element.evaluate("img => img.src") or ""

        venue = page.locator("[class*='addres-pin']").first.inner_text()
        schedule: Locator = page.locator(".schedule")
        schedule_elements = schedule.locator("li").all()
        dates = schedule_elements[2].inner_text()
        time = None
        for element in schedule_elements:
            m = re.findall(r"\d{1,2}:\d{1,2}", element.inner_text())
            if m:
                time = m[0]
        if not time:
            time = "1:01AM"
        date_text = dates.split(" ")
        Logger.debug(f"{time} time")
        Logger.debug(f"{dates} dates")
        Logger.debug(f"{date_text} date text")
        if len(date_text) > 3:
            start_date_obj, end_date_obj = dates.split("-")
            start_date, end_date = parser.parse(start_date_obj + " " + time), parser.parse(end_date_obj + " " + time)
            dates = list(DateFormatting.create_range(start_date, end_date))
        else:
            days = date_text[0].split("-")
            if len(days) > 1:
                month = date_text[1]
                start_day, end_day = days
                start_date, end_date = parser.parse(start_day + " " + month + " " + time), parser.parse(end_day + " " + month + " " + time)
                dates = list(DateFormatting.create_range(start_date, end_date))
            else:
                dates = [parser.parse(dates + " " + time)]
        content: Locator = page.locator("[class*='content']")
        paragraphs = content.locator("p").all()
        description = ""
        for paragraph in paragraphs:
            description += paragraph.inner_text() + "\n"
        return EventInfo(
            name=title,
            dates=dates,
            image=image_url,
            url=url,
            venue=venue,
            source=ScraperName.FRINGE,
            event_type="Arts & Theatre",
            description=description
        )

    @staticmethod
    def get_festival_urls(url: str, page: Page) -> Set[str]:
        goto_with_retry(page, url)
        sleep(3)

        # Scroll to load all events
        height = page.evaluate("document.body.scrollHeight")
        scrolled_amount = 0
        while scrolled_amount < height:
            page.evaluate(f"window.scrollBy(0, {1200})")
            scrolled_amount += 1200
            sleep(0.5)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height > height:
                height = new_height

        hrefs = page.locator("a").evaluate_all("links => links.map(link => link.href)")
        return {href for href in hrefs if href and "/event/" in href}

    @staticmethod
    def get_events(event_urls: Set[str], page: Page, previous_urls: Set[str], out_file: TextIO) -> List[EventInfo]:
        events = []
        for event_url in event_urls:
            if event_url in previous_urls:
                continue
            Logger.info(f"url: {event_url}")
            try:
                event = FringeScrapper.get_event(event_url, page)
                if event:
                    Logger.debug(f"Title: {event.name}")
                    Logger.debug(f"Dates: {event.dates}")
                    Logger.debug(f"Venue: {event.venue}")
                    Logger.debug(f"Image: {event.image}")
                    Logger.debug(f"Description: {event.description[:100]}..." if len(event.description) > 100 else f"Description: {event.description}")
                    Logger.debug(f"Event Type: {event.eventType}")
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    Logger.divider()
                    Logger.warning(str(e))
                else:
                    Logger.divider()
                    Logger.info(f"Error fetching {event_url}: {e}")
            Logger.divider()
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:

        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.FRINGE)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.FRINGE)))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()

            # Get all event URLs from the main page
            event_urls = FringeScrapper.get_festival_urls("https://tickets.fringe.co.nz/events/", page)
            Logger.info(f"Found {len(event_urls)} event URLs")

            # Only add to current festivals if we found events

            out_file.write("[\n")
            events = FringeScrapper.get_events(event_urls, page, set(), out_file)
            out_file.write("]\n")

            if events:
                CurrentFestivals.CURRENT_FESTIVALS.append("WellingtonFringe")
                CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
                    "id": "WellingtonFringe",
                    "name": "Wellington Fringe Festival",
                    "icon": "theater",
                    "url": "https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/wellington-fringe.json"
                })

            festival_file = open(paths.root_path("wellington-fringe.json"), mode="w")
            events_dicts = [event.to_dict() for event in events]
            json.dump({"events": sorted(events_dicts, key=lambda evt: evt["name"])}, festival_file, indent=2)
        festival_file.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return []

# events = list(map(lambda x: x.to_dict(), sorted(FringeScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
