import json

from playwright.sync_api import sync_playwright, Page, Locator

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, Tuple, TextIO
from datetime import datetime, timedelta


class ValhallaScrapper:
    @staticmethod
    def get_dates(page: Page) -> List[datetime]:
        page.locator(".event-date").first.wait_for()
        start_time = page.locator(".event-time-localized-start").all()
        if start_time:
            date = page.locator(".event-date").first.inner_text()
            start_time_text = start_time[0].inner_text()
            return [parser.parse(f"{date} {start_time_text}")]
        times = page.locator(".eventitem-meta-time").all()
        dates = page.locator(".event-date").all()
        start_time = parser.parse(f"{dates[0].inner_text()} {times[0].inner_text()}")
        end_time = parser.parse(f"{dates[1].inner_text()} {times[1].inner_text()}")
        if end_time.day != start_time.day and abs(end_time - start_time) > timedelta(hours=5):
            return [start_time, end_time]
        return [start_time]

    @staticmethod
    def get_event(url: str, image_url: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        info_column = page.locator(".eventitem-column-meta").first
        info_column.wait_for()
        title = info_column.locator("[class*='eventitem-title']").first.inner_text()
        dates = ValhallaScrapper.get_dates(page)
        page.evaluate("window.scrollBy(0, 1000)")
        venue = "Valhalla, Wellington"
        description = page.locator(".sqs-html-content").first.inner_text()
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScraperName.VALHALLA,
                         event_type="Music",
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO, scroll_increment: int = 300) -> Set[Tuple[str, str]]:
        goto_with_retry(page, "https://www.valhallatavern.com/events-1")
        height: int = page.evaluate("document.body.scrollHeight")
        scrolled_amount = 0
        event_urls: Set[Tuple[str, str]] = set()
        urls_file.write("[\n")
        while True:
            if scrolled_amount > height:
                break
            page.evaluate(f"window.scrollBy(0, {scroll_increment})")

            scrolled_amount += scroll_increment
            html = page.locator(".eventlist-event").all()
            for event in html:
                title_element: Locator = event.locator(".eventlist-title").first
                if not title_element.inner_text():
                    continue
                url = title_element.locator("a").first.evaluate("a => a.href")
                if not url or url in previous_urls:
                    continue
                previous_urls.add(url)
                images = event.locator("img")
                image_url = (images.first.evaluate("img => img.src") or "") if images.count() else ""
                event_urls.add((url, image_url))
                json.dump((url, image_url), urls_file, indent=2)
                urls_file.write(",\n")
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.VALHALLA)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.VALHALLA)))
        events: List[EventInfo] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            event_urls = ValhallaScrapper.get_urls(page, previous_urls, urls_file, 1000)
            out_file.write("[\n")
            for part in event_urls:
                Logger.info(f"url: {part[0]}")
                try:
                    event = ValhallaScrapper.get_event(part[0], part[1], page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        Logger.warning(str(e))
                        json.dump(part[0], banned_file, indent=2)
                        banned_file.write(",\n")
                    else:
                        Logger.divider()
                        raise e
                Logger.divider()
            out_file.write("]\n")
            browser.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(ValhallaScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
