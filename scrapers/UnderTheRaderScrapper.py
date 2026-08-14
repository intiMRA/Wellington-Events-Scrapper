import json

from util import FileUtils
from util.PlaywrightUtils import new_context, goto_with_retry
from util.Logger import Logger
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, TextIO
from playwright.sync_api import sync_playwright, Page, Locator


class UnderTheRaderScrapper:
    @staticmethod
    def get_event(url: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        title: str = page.locator(".display_title_1").first.inner_text()
        header = page.locator(".col-md-9").first.inner_text().split("\n")
        info_texts = page.locator(".gig-guide-side-bar").first.inner_text().split("\n")
        time = None
        found_gig_start = False
        doors_open = "1:01AM"
        found_doors_open = False
        for text in info_texts:
            if "GIG STARTS" in text:
                found_gig_start = True
            elif found_gig_start:
                time = text
                break
            if "Doors open" in text:
                found_doors_open = True
            elif found_doors_open:
                doors_open = text
        date_string = header[2].split(",")[0]
        parts = date_string.split(" ")
        time = time if time else doors_open
        date = parser.parse(f"{parts[1]} {parts[2]} {time}")
        image_url = page.locator(".img-responsive").first.evaluate("img => img.src") or ""
        venue = header[4]
        description = page.locator(".description").first.inner_text()
        return EventInfo(name=title,
                         dates=[date],
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScraperName.UNDER_THE_RADAR,
                         event_type="Music",
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], from_file: bool, urls_file: TextIO) -> List[str]:
        event_urls: List[str] = []
        if from_file:
            return FileUtils.load_from_files(ScraperName.UNDER_THE_RADAR)[1]

        while True:
            load_more = page.get_by_text("Load More")
            if not load_more.count():
                break
            load_more.first.click()
            page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(200, 500)")
        page.locator(".vevent").first.wait_for()
        html = page.locator(".vevent").all()
        for event in html:
            title: Locator = event.locator(".gig-title").first
            url = title.locator("a").first.evaluate("a => a.href")
            if url in previous_urls or url in event_urls:
                continue
            event_urls.append(url)
            json.dump(url, urls_file, indent=2)
            urls_file.write(",\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.UNDER_THE_RADAR)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.UNDER_THE_RADAR)))
        events: List[EventInfo] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            goto_with_retry(page, "https://www.undertheradar.co.nz/utr/gigRegion/Wellington")
            event_urls = UnderTheRaderScrapper.get_urls(page, previous_urls, False, urls_file)
            out_file.write("[\n")
            for url in event_urls:
                Logger.info(f"url: {url}")
                try:
                    event = UnderTheRaderScrapper.get_event(url, page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        json.dump(url, banned_file, indent=2)
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

# events = list(map(lambda x: x.to_dict(), sorted(UnderTheRaderScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
