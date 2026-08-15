from playwright.sync_api import sync_playwright, Page

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry, wait_for_items
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, TextIO
import json


class RougueScrapper:
    @staticmethod
    def get_event(url: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        title: str = page.locator(".display_title_1").first.inner_text()
        date_string: str = page.locator(".col-md-9").first.inner_text().split("\n")[2].split(",")[0]
        info_texts: List[str] = page.locator(".gig-guide-side-bar").first.inner_text().split("\n")
        time = "1:01AM"
        found_gig_start = False
        for text in info_texts:
            if "GIG STARTS" in text:
                found_gig_start = True
            elif found_gig_start:
                time = text
                break
        parts = date_string.split(" ")
        date = parser.parse(f"{parts[1]} {parts[2]} {time}")
        image_url: str = page.locator(".img-responsive").first.evaluate("img => img.src") or ""
        venue = "The Rogue & Vagabond"
        description: str = page.locator(".description").first.inner_text()
        return EventInfo(name=title,
                         dates=[date],
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScraperName.ROGUE_AND_VAGABOND,
                         event_type="Music",
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO) -> Set[str]:
        urls_file.write("[\n")
        event_urls: Set[str] = set()
        goto_with_retry(page, "https://rogueandvagabond.co.nz/", wait_until="networkidle")
        # Wait for the event list to render before reading it — .all() takes a snapshot and would
        # silently return nothing if the listing hasn't loaded yet.
        wait_for_items(page.locator(".vevent"))
        titles = page.locator(".vevent").all()
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
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.ROGUE_AND_VAGABOND)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.ROGUE_AND_VAGABOND)))
        events: List[EventInfo] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            event_urls = RougueScrapper.get_urls(page, previous_urls, urls_file)
            out_file.write("[\n")
            for url in event_urls:
                Logger.info(f"url: {url}")
                try:
                    event = RougueScrapper.get_event(url, page)
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
                        raise e
                Logger.divider()
            out_file.write("]\n")
            browser.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(RougueScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
