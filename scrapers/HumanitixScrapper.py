import random
from time import sleep

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from datetime import datetime
from dateutil import parser
from typing import List, Optional, Set, Tuple, TextIO
import json
from playwright.sync_api import sync_playwright, Page
from util.PlaywrightUtils import goto_with_retry, launch_stealth
from util.Logger import Logger

class HumanitixScrapper:

    @staticmethod
    def get_dates_from_event(page: Page, multiple_dates: bool) -> List[datetime]:
        dates: List[datetime] = []
        page.evaluate("window.scrollTo(200, 500)")
        if multiple_dates:
            # Several "more dates" matches exist and .first is CSS-hidden (box=None, so
            # scroll_into_view can't help) — pick the one that's actually visible and click it.
            more_options = page.get_by_text("more dates")
            visible_more = next(
                (more_options.nth(i) for i in range(more_options.count()) if more_options.nth(i).is_visible()),
                None,
            )
            if visible_more is not None:
                visible_more.click()
                sleep(1)
                for element in page.locator("form").first.locator("li").all():
                    reg = r"(\d{1,2}\s[aA-zZ]{3},\s[aA-zZ0-9:]*[AMPamp]{2})"
                    matches = re.findall(reg, element.inner_text())
                    if len(matches) > 1:
                        for match in matches:
                            dates.append(parser.parse(match.replace(",", "")))
                    elif len(matches) == 1:
                        dates.append(parser.parse(matches[0]))
                    else:
                        Logger.debug(f"multiple dates: {element.inner_text()}")
                return dates
            Logger.warning("'more dates' control not visible; falling back to inline date")
        date_strings = page.locator(".datetime").all()
        if not date_strings:
            date_strings = page.locator("[class*='datetime']").all()
        if not date_strings:
            Logger.warning("no datetime element found")
            return dates
        date_string = date_strings[0].inner_text().split("\n")[0]
        reg = r"(\d{1,2}\s[aA-zZ]{3}\s*[0-9]*,\s[aA-zZ0-9:]*[AMPamp]{2})"
        matches = re.findall(reg, date_string)
        year = re.findall(r"\d{4}", date_string)
        if len(matches) > 1:
            for match in matches:
                if year:
                    match += f" {year[0]}"
                dates.append(parser.parse(match.replace(",", "")))
        elif len(matches) == 1:
            dates.append(parser.parse(matches[0]))
        else:
            Logger.debug(f"single date: {date_string}")
        return dates

    @staticmethod
    def format_input(input_string: str):
        if not input_string:
            return input_string
        input_string = input_string.replace("&", "And").replace(" ", "").replace(",", "")
        return input_string[0].lower() + input_string[1:]

    @staticmethod
    def get_event(url: str, category: str, multiple_dates: bool, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        title: str = page.locator(".titlewrapper").first.inner_text().split("\n")[0]
        image_url: str = page.locator(".banner").first.locator("img").evaluate('img => img.src') or ""
        address = page.locator(".EventLocation").first.locator(".address")
        if not address.count():
            address = page.locator(".address")
        if not address.count():
            Logger.warning(f"no venue: {title}")
            return None
        # Humanitix addresses are "<room/level>\n<street address>"; take the address line when
        # present, otherwise the single line (e.g. "To be announced").
        location_lines = address.first.inner_text().split("\n")
        venue: str = location_lines[1] if len(location_lines) > 1 else location_lines[0]
        venue = venue.split("  ·  ")[0]
        Logger.debug(f"venue: {venue}")
        dates: List[datetime] = HumanitixScrapper.get_dates_from_event(page, multiple_dates)
        description: str = ""
        if page.locator(".RichContent").all():
            description = page.locator(".RichContent").first.inner_text()
        else:
            Logger.warning(f"no description: {title}")
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=url,
                         source=ScraperName.HUMANITIX,
                         event_type=category,
                         description=description)
    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO ) -> Set[Tuple[str, str, bool]]:
        urls_file.write("[\n")
        goto_with_retry(page, 'https://humanitix.com/nz/events/nz--wellington-region--wellington')
        sleep(random.uniform(2, 4))
        categories_button = page.locator("#search-and-explore-dropdown")
        sleep(1)
        categories_button.click()
        categories = page.locator("[data-dropdown-option='true']").all()
        categories = [(HumanitixScrapper.format_input(category.inner_text()), category.inner_text()) for category in categories]
        event_urls: Set[Tuple[str, str, bool]] = set()
        for category, categoryName in categories:
            if category == "allCategories":
                continue
            url = f'https://humanitix.com/nz/events/nz--wellington-region--wellington/{category}'
            Logger.info(f"category name: {categoryName} {category} {url}")
            goto_with_retry(page, url)
            while True:
                sleep(random.uniform(1, 2))
                height = page.evaluate("document.body.scrollHeight")
                scrolled_amount = 0
                while True:
                    if scrolled_amount > height:
                        break
                    page.evaluate(f"window.scrollBy(0, {100})")

                    scrolled_amount += 100
                events_data = page.locator('.test').all()
                # Process this page's events BEFORE deciding to paginate — otherwise a category
                # with no "Show More" (a single page) breaks out having collected nothing.
                for event in events_data:
                    event_url = event.evaluate('event => event.href')
                    if not event_url or event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    divs = [x.inner_text() for x in event.locator('div').all()]
                    multiple_dates = any("more times" in date_string for date_string in divs)
                    url_tuple = (event_url, categoryName, multiple_dates)
                    event_urls.add(url_tuple)
                    json.dump(url_tuple, urls_file, indent=2)
                    urls_file.write(",\n")
                if page.get_by_text("Show More").count():
                    page.get_by_text("Show More").first.click()
                    sleep(1)
                else:
                    break
                sleep(random.uniform(1, 3))
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        fetch_urls = False
        event_urls = set()
        if not fetch_urls:
            event_urls = FileUtils.load_from_files(ScraperName.HUMANITIX)[1]
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.HUMANITIX)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.HUMANITIX)))
        events: List[EventInfo] = []
        with sync_playwright() as playwright:
            # Humanitix has bot protection — stealth launch (headed, real UA, automation flags
            # stripped, navigator.webdriver hidden) replaces the old undetected-chromedriver setup.
            context = launch_stealth(playwright, headless=False)
            page = context.new_page()
            if fetch_urls:
                event_urls = HumanitixScrapper.get_urls(page, previous_urls, urls_file)
            else:
                json.dump(list(event_urls), urls_file, indent=2)
            out_file.write("[\n")
            for part in event_urls:
                if (not fetch_urls) and part[0] in previous_urls:
                    continue
                Logger.info(f"category: {part[1]} url: {part[0]}")
                try:
                    event = HumanitixScrapper.get_event(part[0], part[1], part[2], page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        json.dump(part[0], banned_file, indent=2)
                        banned_file.write(",\n")
                        Logger.warning(str(e))
                    else:
                        raise e
                Logger.divider()
            out_file.write("]\n")
            context.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(HumanitixScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
