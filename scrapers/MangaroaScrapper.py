from playwright.sync_api import sync_playwright, Page

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry, wait_for_items
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, TextIO
import json


class MangaroaScrapper:
    @staticmethod
    def get_event(url: str, page: Page) -> Optional[EventInfo]:
        if "mangaroa" not in url:
            return None
        goto_with_retry(page, url)
        title_texts = page.locator(".product__title").first.inner_text().split(" — ")
        title = title_texts[0]
        date_string, time_string = title_texts[1].split(" | ")
        hour = time_string.split("-")[0]
        date = parser.parse(date_string + " " + hour)
        img = page.locator(".product__media-gallery img").first
        image_url = img.evaluate("img => img.currentSrc || img.src")
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        description = page.locator(".product__description").first.inner_text()
        return EventInfo(name=title,
                         dates=[date],
                         image=image_url,
                         url=url,
                         venue="Mangaroa Farm, 98 Whitemans Valley Road, Te Awa Kairangi, Upper Hutt",
                         source=ScraperName.Mangaroa,
                         event_type="Music",
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO) -> Set[str]:
        urls_file.write("[\n")
        event_urls: Set[str] = set()
        goto_with_retry(page, "https://events.mangaroa.org/", wait_until="networkidle")
        # Wait for the event list to render before reading it — .all() takes a snapshot and would
        # silently return nothing if the listing hasn't loaded yet.
        wait_for_items(page.locator(".event-item"))
        titles = page.locator(".event-item").all()
        for title in titles:
            event_url = title.locator("a").first.evaluate("a => a.href")
            if event_url is None or event_url in previous_urls or event_url in event_urls:
                continue
            event_urls.add(event_url)
            json.dump(event_url, urls_file, indent=2)
            urls_file.write(",\n")
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.Mangaroa)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.Mangaroa)))
        events: List[EventInfo] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            event_urls = MangaroaScrapper.get_urls(page, previous_urls, urls_file)
            out_file.write("[\n")
            for url in event_urls:
                Logger.info(f"url: {url}")
                try:
                    event = MangaroaScrapper.get_event(url, page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        Logger.warning(str(e))
                    else:
                        Logger.divider()
                        Logger.info(f"Error fetching {url}: {e}")
                Logger.divider()
            out_file.write("]\n")
            browser.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(MangaroaScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
