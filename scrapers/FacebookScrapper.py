import json
import random

from dotenv import load_dotenv
from time import sleep
from dateutil import parser

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Set, Tuple, TextIO
from playwright.sync_api import sync_playwright, Page
from util.PlaywrightUtils import goto_with_retry, launch_stealth, human_delay
from util.Logger import Logger

dotenv_path = Path('venv/.env')
load_dotenv(dotenv_path=dotenv_path)


class FacebookScrapper:
    @staticmethod
    def parse_day_of_week(day_string: str) -> Optional[str]:
        """Parses a day of the week string into a datetime object representing the next occurrence of that day."""
        try:
            today = datetime.now()
            target_day = parser.parse(day_string).weekday()  # 0=Monday, 6=Sunday

            days_until_target = (target_day - today.weekday()) % 7
            next_occurrence = today + timedelta(days=days_until_target)
            return next_occurrence.strftime("%d %b")
        except Exception as e:
            Logger.error(f"failed to parse day of week {day_string} {e}")
            return None

    @staticmethod
    def parse_date(date: str, verbose: bool = True) -> List[datetime]:
        if verbose:
            Logger.debug(f"date: {date}")
        week_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
        today = datetime.now()
        hour = " 1:01AM"
        if re.findall(r"\d{1,2}:\d{1,2}", date):
            hour: str = re.findall(r"\d{1,2}:\d{1,2}", date)[0]
        today_string = today.strftime("%d %b")
        today = parser.parse(f"{today_string} {hour}")
        if verbose:
            Logger.debug(f"hour: {hour}")
        if "Tomorrow" in date:
            target_date = today + timedelta(days=1)
            return [target_date]
        elif "Today" in date:
            return [today]
        regex = r"\d{1,2}\s\w+\d{0,4}"
        matches = re.findall(regex, date)
        if matches:
            dates = []
            for match in matches:
                try:
                    dates.append(parser.parse(f"{match} {hour}"))
                except Exception as e:
                    Logger.debug(f"missing hour {e}")
                    pass
            if verbose:
                Logger.debug(f"date: {matches[0]} {hour}")
            return dates
        for day_of_the_week in week_days:
            matches = re.findall(fr"{day_of_the_week}", date)
            if matches:
                day = FacebookScrapper.parse_day_of_week(matches[0])
                if verbose:
                    Logger.debug(f"day: {day}")
                return [parser.parse(f"{day} {hour}")]
        if verbose:
            Logger.debug(f"facebook: {date}")
        return []

    @staticmethod
    def get_event(url: str, category: str, page: Page, banned_file: TextIO) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(random.randint(1, 3))
        info = page.locator("[aria-label='Event permalink']").first
        spans = info.locator("span").all()
        texts = []
        for span in spans:
            text = span.inner_text()
            if text in texts:
                continue
            texts.append(text)
        page.evaluate(f"window.scrollBy(0, 200)")
        sleep(random.randint(1, 3))
        if info.get_by_role("button", name="See more").count():
            info.get_by_role("button", name="See more").first.click()
        else:
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            raise Exception("No see more button")
        sleep(1)
        if info.get_by_role("button", name="See more").count():
            info.get_by_role("button", name="See more").first.click()
        human_delay(page)
        if info.get_by_text("See less").count():
            long_desc = info.get_by_text("See less").first.inner_text()
        else:
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            raise Exception("No see less button")

        if "..." in long_desc:
            long_desc = "\n".join(long_desc.split("\n")[0:-2])
        else:
            long_desc = re.sub(r"See less", "", long_desc)
        address = info.locator("[aria-label='Location information for this event']")
        venue = address.first.inner_text().split("\n")[-1] if address.count() else ""
        image_url = page.locator("[data-imgperflogname='profileCoverPhoto']").first.evaluate(
            "img => img.src")
        dates = FacebookScrapper.parse_date(texts[0])
        title = texts[1]
        Logger.info(title)
        Logger.info(venue)
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=url,
                         source=ScraperName.FACEBOOK,
                         event_type=category,
                         description=long_desc)

    @staticmethod
    def slow_scroll_to_bottom_other(page: Page, previous_urls: Set[str], out_urls_file: TextIO, scroll_increment=300) -> Set[
        Tuple[str, str]]:
        event_urls: Set[Tuple[str, str]] = set()
        html = page.locator('a').all()
        old_length = len(html)
        while len(html) < 500:
            page.evaluate(f"window.scrollBy(0, {scroll_increment});")
            sleep(random.uniform(2, 3))
            html = page.locator('a').all()

            if old_length == len(html):
                break
            else:
                old_length = len(html)

        Logger.info(f"facebook finished finding html {len(html)}")
        for event in html:
            try:
                date_string = event.inner_text().split("\n")[0]
                ev_dates = FacebookScrapper.parse_date(date_string, False)
                if ev_dates[-1] < datetime.now():
                    Logger.debug(f"skipping date: {date_string}")
                    continue
                event_url = event.evaluate('a => a.href')
                regex = r'https://www.facebook.com/events/\d+'
                event_url = re.findall(regex, event_url)[0]
                if event_url in previous_urls:
                    continue
                previous_urls.add(event_url)
                event_urls.add((event_url, "Other"))
                json.dump((event_url, "Other"), out_urls_file, indent=2)
                out_urls_file.write(",\n")
            except Exception as e:
                Logger.debug(f"skipping event: {e}")
                continue
        return event_urls

    @staticmethod
    def get_urls(urls_file: TextIO, page: Page, start_date_string: str, end_date_string: str, previous_urls: Set[str], category_urls: Set[Tuple[str, str]]) -> Set[
        Tuple[str, str]]:
        urls_file.write("[\n")
        # Facebook removed the category-filter UI, so we just scrape the location-filtered event
        # listings (date range + location come from the URL params, not in-page filters).
        for location_id in ("1590021457900572", "114912541853133"):
            goto_with_retry(page,
                            f"https://www.facebook.com/events/?"
                            f"date_filter_option=CUSTOM_DATE_RANGE"
                            f"&discover_tab=CUSTOM"
                            f"&location_id={location_id}"
                            f"&start_date={start_date_string}"
                            f"&end_date={end_date_string}")
            sleep(1)
            category_urls = category_urls.union(
                FacebookScrapper.slow_scroll_to_bottom_other(page, previous_urls, urls_file, scroll_increment=5000))
        urls_file.write("]\n")
        return category_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        # Persistent Chrome profile keeps the Facebook login across runs; run headed + stealth.
        # In-project Chrome profile (the literal "~" folder in the repo root, gitignored via "~/")
        # — it holds the logged-in Facebook session. NOT expanded to $HOME (that's a fresh profile).
        profile_path = "~/ChromeTestProfile"
        start_date = datetime.now()
        start_date_string = start_date.strftime("%Y-%m-%d") + "T05%3A00%3A00.000Z"
        end_date = start_date + relativedelta(days=15)
        end_date_string = end_date.strftime("%Y-%m-%d") + "T05%3A00%3A00.000Z"
        fetch_urls = True
        category_urls = set()
        if not fetch_urls:
            category_urls = FileUtils.load_from_files(ScraperName.FACEBOOK)[1]
        events = []
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.FACEBOOK)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.FACEBOOK)))
        with sync_playwright() as playwright:
            context = launch_stealth(playwright, headless=False, user_data_dir=profile_path)
            # A persistent context already has a default page open — reuse it instead of
            # opening a second window with new_page().
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(15000)
            if fetch_urls:
                category_urls = FacebookScrapper.get_urls(urls_file, page, start_date_string, end_date_string,
                                                          previous_urls, category_urls)
            else:
                json.dump(list(category_urls), urls_file, indent=2)
            num_events = len(category_urls)
            Logger.info(f"fetching: {num_events}")
            count = 1
            out_file.write("[\n")
            for part in category_urls:
                Logger.info(f"category: {part[1]} url: {part[0]}")
                if (not fetch_urls) and part[0] in previous_urls:
                    continue
                try:
                    event = FacebookScrapper.get_event(part[0], part[1], page, banned_file)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                    human_delay(page, 2, 4)
                except Exception as e:
                    Logger.warning(str(e))
                    human_delay(page, 2, 4)
                Logger.info(f"{count} out of {num_events}")
                count += 1
                Logger.divider()
            out_file.write("]\n")
            context.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(FacebookScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
