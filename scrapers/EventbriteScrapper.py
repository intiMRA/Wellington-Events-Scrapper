from datetime import datetime

from util import FileUtils

from scrapers.ScrapperNames import ScraperName
from util.DateFormatting import DateFormatting

from model.EventInfo import EventInfo
import re
from dateutil.relativedelta import relativedelta
from dateutil import parser
import json
from time import sleep
from typing import List, Tuple, Set, Optional, TextIO
from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError

from util.PlaywrightUtils import goto_with_retry, new_context, normalize_text, wait_for_items
from util.Logger import Logger


class EventbriteScrapper:
    @staticmethod
    def get_all_dates(page: Page) -> List[datetime]:
        sleep(1)
        dates = []
        if page.get_by_text("looking for was not found").count():
            return []
        datetime_locator = page.locator("[data-testid='event-datetime']")
        if not datetime_locator.count():
            return []
        date_div_text: str = normalize_text(datetime_locator.first.inner_text())
        if "Multiple dates" in date_div_text:
            return EventbriteScrapper.parse_multiple_dates(page)
        date_div_text_comma_count = len(date_div_text.split(","))
        bar_count = len(date_div_text.split("-"))
        Logger.debug(date_div_text)
        if date_div_text_comma_count < 3 and bar_count <= 2:
            Logger.debug("type 1")
            date_text = date_div_text.replace("  •  ", " ").split(" - ")[0]
            if date_text:
                try:
                    dates.append(DateFormatting.replace_year(parser.parse(date_text.replace(" at ", " ").replace(" Starts", " "))))
                    return dates
                except (ValueError, OverflowError):
                    pass
        if date_div_text_comma_count == 3:
            Logger.debug("type 2")
            parts = date_div_text.split("  •  ")
            time_part = parts[1].split("-")[0].strip() if len(parts) > 1 else ""
            date_parts = parts[0].split("-")
            for dp in date_parts:
                date_str = dp.split(",", 1)[1].strip()
                date_text = f"{date_str} {time_part}".strip()
                date_text = date_text.replace("Starts at ", "")
                dates.append(DateFormatting.replace_year(parser.parse(date_text)))
            return dates
        if bar_count > 2:
            Logger.debug("type 3")
            parts = date_div_text.split("-")
            first_date, second_date, _ = parts
            second_date, time_string = second_date.split("  •  ")
            dates.append(parser.parse(f"{first_date} {time_string}"))
            dates.append(parser.parse(f"{second_date} {time_string}"))
        return dates

    @staticmethod
    def parse_multiple_dates(page: Page) -> List[datetime]:
        if page.locator("[data-testid='explore-similar-events-button']").count():
            return []
        dates = []
        checkout = page.locator("[data-testid='conversion-bar-checkout-button']")
        if not checkout.count():
            return []
        checkout.first.click()
        sleep(3)
        frame = page.frame_locator("iframe[id*='eventbrite-widget-modal']")
        calendar_containers = frame.locator("[data-testid='calendar-container']").all()
        if calendar_containers:
            month_sections = calendar_containers[0].locator("[class*='Stack_root']").all()
            current_month = ""
            for section in month_sections:
                month_elements = section.locator("[class*='CompactCalendar-module__monthName']").all()
                if month_elements:
                    current_month = month_elements[0].inner_text()
                day_elements = section.locator("[class*='CompactCalendar-module__dateText']").all()
                time_elements = section.locator("[class*='CompactCalendar-module__timeSlotText']").all()
                if day_elements and current_month:
                    day = day_elements[0].inner_text()
                    time_text = time_elements[0].inner_text() if time_elements else ""
                    date_str = normalize_text(f"{current_month} {day} {time_text}").strip()
                    dates.append(DateFormatting.replace_year(parser.parse(date_str)))
        else:
            try:
                date_text = frame.locator("[class*='EventInfoCard-module__dateWrapper']").first.inner_text()
                time_elements = frame.locator("[class*='TimeSlotList_sessionText']").all()
                time_text = time_elements[0].inner_text().split(" - ")[0].strip() if time_elements else ""
                date_str = normalize_text(f"{date_text} {time_text}").strip()
                dates.append(DateFormatting.replace_year(parser.parse(date_str)))
            except (ValueError, OverflowError, PlaywrightError):
                pass
        return dates

    @staticmethod
    def get_categories(page: Page) -> List[Tuple[str, str]]:
        categories = []
        sleep(1)
        view_more_button = page.locator("[aria-controls='view-more-category']").first
        view_more_button.click()
        sleep(2)
        cat_list = page.locator("#view-more-category").first
        wait_for_items(cat_list.locator("li"))
        cats = cat_list.locator("li").all()
        for cat in cats:
            link = cat.locator("a").first.evaluate("a => a.href")
            category = (cat.inner_text(), link)
            categories.append(category)
        return categories

    @staticmethod
    def get_event(url: str, page: Page, category: str, banned_file: TextIO) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(1)
        # Optional elements are checked with .count() (instant) rather than try/except on an
        # action: a missing locator would otherwise auto-wait the full timeout before failing.
        bar = page.locator("[class*='EventSignalsBar_signals']")
        if bar.count() and "sales ended" in bar.first.inner_text().lower():
            return None
        venue_locator = page.locator("[data-testid*='event-venue']")
        if not venue_locator.count():
            return None
        location_text: str = venue_locator.first.inner_text()
        if "leadflake" in location_text.lower():
            Logger.info(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            return None
        venue = location_text
        title_locator = page.locator("[data-testid*='event-title']")
        if not title_locator.count():
            raise Exception("no title")
        title: str = title_locator.first.inner_text()
        image_locator = page.locator("[data-testid='hero-img']")
        image_url = image_locator.first.evaluate("img => img.src") if image_locator.count() else ""
        event_link: str = url
        view_details = page.locator("[class*='ViewDetailsButton_button']")
        if view_details.count():
            view_details.first.click()
            sleep(1)
        read_more = page.locator("[data-heap-id*='Listings - Description - Read more - Click']")
        if read_more.count():
            read_more.first.click()
            sleep(1)
        for desc_selector in ("[class*='AboutThisEventEmbedded_container']",
                              "[data-testid*='section-wrapper-overview']",
                              "[class*='Overview_summary']"):
            desc_locator = page.locator(desc_selector)
            if desc_locator.count():
                description: str = desc_locator.first.inner_text()
                break
        else:
            raise Exception("no description")
        dates: List[datetime] = EventbriteScrapper.get_all_dates(page)
        if not dates:
            date_matches = re.findall(r"\d{1,2}\s\w+\d{0,4}", title)
            hour = "1:01AM"
            hour_matches = re.findall(r"\d{1,2}\s:\d{2}[aAmMpP]{0,2}", title)
            if hour_matches:
                hour = hour_matches[0]
            for date_match in date_matches:
                try:
                    dates.append(parser.parse(f"{date_match} {hour}"))
                except (ValueError, OverflowError):
                    continue

        if "copyright" in description:
            Logger.info(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            return None
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=event_link,
                         source=ScraperName.EVENT_BRITE,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls(page: Page, previous_urls: Set[str]) -> Set[Tuple[str, str]]:
        urls: Set[Tuple[str, str]] = set()
        goto_with_retry(page, 'https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        categories = EventbriteScrapper.get_categories(page)
        total_cats = len(categories)
        cat_count = 1
        for category in categories:
            cat_name, link = category
            Logger.info(f"fetching: {cat_name}, {cat_count} out of {total_cats}")
            cat_count += 1
            Logger.divider()
            goto_with_retry(page, link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            new_url = (page.url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            goto_with_retry(page, new_url)
            current_page = 1
            tries = 0
            while True:
                next_url = re.sub(r"page=\d+", f"page={current_page}", page.url)
                goto_with_retry(page, next_url)
                try:
                    sleep(1)
                    pagination = page.locator("[data-testid='pagination-parent']").first
                    first_page, last_page = pagination.inner_text().split(" of ")
                    first_page = int(first_page)
                    last_page = int(last_page)
                    if first_page > last_page:
                        break
                except Exception as e:
                    Logger.info(f"error finding pagination: {e}")
                    if tries >= 3:
                        break
                    tries += 1
                current_page += 1
                sleep(2)
                # New page navigated — wait for its event cards to render before snapshotting.
                wait_for_items(page.locator("[data-testid='search-event']"))
                cards = page.locator("[data-testid='search-event']").all()
                Logger.debug(f"len cards: {len(cards)}")
                for card in cards:
                    event_url = card.locator(".event-card-link").first.evaluate("a => a.href")
                    texts = card.inner_text().split("\n")

                    tags = [
                        "Sales end soon",
                        "Selling quickly",
                        "Nearly full",
                        "Just added",
                        "Not Yet On Sale"
                    ]

                    sold_tags = [
                        "Sold Out",
                        "Sales Ended",
                        "Unavailable",
                        "Sales ended"
                    ]
                    if texts[0] in sold_tags:
                        continue
                    if texts[0] in tags:
                        texts = texts[1:]
                    if len(texts) < 3:
                        continue
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    url_tuple = (event_url, cat_name)
                    urls.add(url_tuple)
                Logger.debug(f"len urls: {len(urls)}")
        return urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            fetch_urls = True
            categories = set()
            if not fetch_urls:
                categories = FileUtils.load_from_files(ScraperName.EVENT_BRITE)[1]
            events = []
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.EVENT_BRITE)))
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            page.set_default_timeout(15000)
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.EVENT_BRITE)
            if fetch_urls:
                categories = EventbriteScrapper.get_urls(page, previous_urls)
            json.dump(list(categories), urls_file, indent=2)
            urls_file.close()
            out_file.write("[\n")
            for category in categories:
                if (not fetch_urls) and category[0] in previous_urls:
                    continue
                url, category_name = category
                Logger.info(f"category: {category_name} url: {url}")
                try:
                    event: Optional[EventInfo] = EventbriteScrapper.get_event(url, page, category_name, banned_file)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                except Exception as e:
                    if "No dates found for" in str(e):
                        json.dump(url, banned_file, indent=2)
                        banned_file.write(",\n")
                        Logger.divider()
                        Logger.warning(str(e))
                    else:
                        Logger.divider()
                        raise e
                Logger.divider()
            out_file.write("]\n")
        out_file.close()
        banned_file.close()
        return events

# previous_events = FileUtils.load_from_files(ScraperName.EVENT_BRITE)[0]
# previous_urls = set(e["url"] for e in previous_events)
# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
