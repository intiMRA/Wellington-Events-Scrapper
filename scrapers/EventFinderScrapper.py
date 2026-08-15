import random
from time import sleep

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from util.DateFormatting import DateFormatting
from dateutil import parser
from dateutil.relativedelta import relativedelta
from typing import List, Set, Optional, Tuple, TextIO
import json
from playwright.sync_api import sync_playwright, Page, Locator
from util.PlaywrightUtils import goto_with_retry, new_context
from util.Logger import Logger

class EventFinderScrapper:
    @staticmethod
    def get_time_from_string(time_string: str) -> Optional[datetime]:
        # Get the current date
        today = datetime.now()

        # Check if the string mentions "Tomorrow" or "Today"
        if "Tomorrow" in time_string:
            target_date = today + timedelta(days=1)  # Add one day for tomorrow
        elif "Today" in time_string:
            target_date = today  # Use today's date
        else:
            return None  # If the string doesn't contain "Today" or "Tomorrow"

        # Extract the time (e.g., 6:30pm)
        time_match = re.search(r'(\d{1,2}):(\d{2})(am|pm)', time_string, re.IGNORECASE)

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = time_match.group(3).lower()

            # Convert to 24-hour format if in PM
            if am_pm == "pm" and hour != 12:
                hour += 12
            if am_pm == "am" and hour == 12:
                hour = 0

            # Combine the target date with the time
            target_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return target_time
        return None

    @staticmethod
    def get_event(url: str, category: Optional[str], page: Page) -> Optional[EventInfo]:
        if page.get_by_text("HTTP").count():
            goto_with_retry(page, url)
        sleep(random.uniform(1, 2))
        goto_with_retry(page, url)
        # Existence-check with .count() (instant) instead of try/except on an action, which
        # would auto-wait the full timeout before failing.
        title_locator = page.locator(".value-title")
        if not title_locator.count():
            return None
        title: str = title_locator.first.inner_text()
        venue_locator = page.locator(".venue")
        venue: str = venue_locator.first.inner_text() if venue_locator.count() else ""
        dates = EventFinderScrapper.get_all_event_dates(url, page)
        description_locator = page.locator(".description")
        description: str = description_locator.first.inner_text() if description_locator.count() else ""
        image_locator = page.locator(".photo")
        image_url: str = image_locator.first.evaluate("photo => photo.src") if image_locator.count() else ""
        if not image_url:
            Logger.warning(f"no image for {url}")
        return EventInfo(
            name=title,
            dates=dates,
            image=image_url,
            url=url,
            venue=venue,
            source=ScraperName.EVENT_FINDER,
            event_type=category if category else "Other",
            description=description)

    @staticmethod
    def get_all_event_dates(url: str, page: Page) -> List[datetime]:
        date_objects: List[datetime] = []
        if page.get_by_text("HTTP").count():
            sleep(2)
            goto_with_retry(page, url)
        show_more = page.locator(".show-more")
        if show_more.count():
            show_more.first.click()
        date_table = page.locator(".sessions-info")
        for _ in range(3):
            if date_table.count():
                break
            sleep(1)
        if not date_table.count():
            return date_objects
        dates: List[Locator] = date_table.first.locator("time").all()
        for date in dates:
            date_string = date.get_attribute("datetime")
            if not date_string:
                continue
            try:
                # datetime 2024-08-01, 09:00–13:00
                full_string = date_string
                date_string = date_string.split(",")[0]
                if len(date_string.split("–")) > 1:
                    start, last = date_string.split("–")
                    hour = full_string.split(",")[-1].split("–")[0]
                    start += " " + hour
                    last += " " + hour
                    Logger.debug(f"start: {start} end: {last}")
                    start_date_obj = parser.parse(start)
                    end_date_obj = parser.parse(last)

                    start_date_obj = DateFormatting.replace_year(start_date_obj)

                    end_date_obj = DateFormatting.replace_year(end_date_obj)
                    date_objects = list(DateFormatting.create_range(start_date_obj, end_date_obj))
                else:
                    date_string = date_string + " " + full_string.split(",")[-1].split("–")[0]
                    date_obj = parser.parse(date_string)
                    date_obj = DateFormatting.replace_year(date_obj)
                    date_objects.append(date_obj)
            except Exception as e:
                Logger.error(f"date parse failed for {url}: {e}")
        return date_objects

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str], urls_file: TextIO) -> Set[Tuple[str, str]]:
        urls = set()
        start_date = datetime.now()
        end_date = start_date + relativedelta(days=30)

        wellington_region_url = f"https://www.eventfinda.co.nz/whatson/events/wellington-region/date/to-month/{end_date.month}/to-day/{end_date.day}"

        wellington_url = f"https://www.eventfinda.co.nz/whatson/events/wellington/date/to-month/{end_date.month}/to-day/{end_date.day}"
        fetch_urls = [wellington_region_url, wellington_url]
        urls_file.write("[\n")
        for url in fetch_urls:
            Logger.divider()
            Logger.info(f"fetching listing: {url}")
            goto_with_retry(page, url + f'/page/{2}')
            last_page = 1
            pagination = page.locator('.lead')
            if pagination.count():
                last_page = int(re.sub(r'\W+', ' ', pagination.first.inner_text()).strip().split("of")[-1])
            else:
                Logger.error(f"pagination not found for {url}")
            Logger.info(f"{last_page} page(s) to fetch")
            current_page = 1
            while current_page <= last_page:
                page_url = url + f'/page/{current_page}'
                goto_with_retry(page, page_url)
                cards = page.locator('.listings-events').first.locator('.card')
                for _ in range(10):
                    if cards.count():
                        break
                    sleep(1)
                Logger.info(f"page {current_page}/{last_page}: {cards.count()} cards ({len(urls)} urls collected)")
                for event in cards.all():
                    link = event.locator(".card-title").first.locator("a").first
                    if not link.count():
                        Logger.warning("invalid event card, skipping")
                        continue
                    event_url = link.evaluate("a => a.href")
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    category_locator = event.locator('.category')
                    category: Optional[str] = category_locator.first.inner_text() if category_locator.count() else None
                    url_tuple = (event_url, category if category else "Other")
                    urls.add(url_tuple)
                    json.dump(url_tuple, urls_file, indent=2)
                    urls_file.write(",\n")
                current_page += 1
        urls_file.write("]\n")
        return urls


    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            fetch_urls = False
            urls = set()
            if not fetch_urls:
                urls = FileUtils.load_from_files(ScraperName.EVENT_FINDER)[1]
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.EVENT_FINDER)
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.EVENT_FINDER)))
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            page.set_default_timeout(15000)
            if fetch_urls:
                urls = EventFinderScrapper.get_urls(page, previous_urls, urls_file)
            else:
                json.dump(list(urls), urls_file, indent=2)
            events: List[EventInfo] = []
            out_file.write("[\n")
            for parts in urls:
                if (not fetch_urls) and parts[0] in previous_urls:
                    continue
                url = parts[0]
                category = parts[1]
                Logger.info(f"[{category}] {url}")
                try:
                    event = EventFinderScrapper.get_event(url, category, page)
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
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(EventFinderScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
