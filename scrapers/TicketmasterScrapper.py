import json
import re
from time import sleep
import random
import requests

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from enum import Enum
from dateutil import parser
import time
import pytz
from typing import List, Optional, Set, Tuple, TextIO
from playwright.sync_api import sync_playwright, Page, Locator
from util.PlaywrightUtils import goto_with_retry, launch_stealth, human_delay
from util.Logger import Logger

nz_timezone = pytz.timezone('Pacific/Auckland')
majorCats = {
    "MusicEvent": ["1", "2", "3", "4", "5", "52", "60", "171", "200", "201", "1001", "1002", "1012", "1201", "1202",
                   "1220", "1221", "1229", "1230", "1231", "1232", "1233", "1234", "1235", "1236", "1237", "1238",
                   "1258",
                   "1259", "1262", "10001", "10006", "10103", "10104"],
    "ComedyEvent": ["39", "264", "1013", "10102"],
    "ChildrensEvent": ["55", "209", "1114", "1115", "1212", "1214", "1240", "1260"],
    "ExhibitionEvent": ["14", "54", "1014", "1213", "1245", "1249", "1250", "1251", "1253", "1254", "10008"],
    "Festival": ["203", "1004", "1005", "1006", "1007", "1123", "1216", "1217", "1218", "1219", "1228", "10101"],
    "FoodEvent": ["1122", "1242"],
    "LiteraryEvent": ["1222"],
    "ScreeningEvent": ["1015"],
    "SportsEvent": ["7", "8", "9", "10", "11", "25", "27", "30", "31", "33", "36", "102", "204", "206", "693", "771",
                    "773", "831", "833", "1102", "1103", "1104", "1105", "1106", "1107", "1109", "1110", "1124", "1204",
                    "1206", "1210", "1211", "1226", "1227", "1239", "10004", "10105"],
    "TheaterEvent": ["12", "13", "22", "23", "32", "207", "1003", "1111", "1116", "1117", "1118", "1241", "10002",
                     "10106"]
}
minorCats = {
    "MusicEvent": ["1", "2", "3", "4", "5", "50", "52", "60", "107", "200", "201", "202", "203", "542", "764", "766",
                   "839", "10001", "KnvZfZ7vAvv", "KnvZfZ7vAve", "KnvZfZ7vAvd", "KnvZfZ7vAvA", "KnvZfZ7vAvk",
                   "KnvZfZ7vAeJ", "KnvZfZ7vAv6", "KnvZfZ7vAvF", "KnvZfZ7vAva", "KnvZfZ7vAv1", "KnvZfZ7vAvJ",
                   "KnvZfZ7vAvE", "KnvZfZ7vAJ6", "KnvZfZ7vAvI", "KnvZfZ7vAvt", "KnvZfZ7vAvn", "KnvZfZ7vAvl",
                   "KnvZfZ7vAev", "KnvZfZ7vAee", "KnvZfZ7vAed", "KnvZfZ7vAe7", "KnvZfZ7vAeA", "KnvZfZ7vAeF",
                   "KZFzniwnSyZfZ7v7nJ", "KZazBEonSMnZfZ7vkE1"],
    "ChildrensEvent": ["29", "KnvZfZ7v7lF", "KnvZfZ7v7lI", "KnvZfZ7v7lv", "KnvZfZ7v7n1", "KnvZfZ7v7na", "KnvZfZ7vAea",
                       "KnvZfZ7vAeE", "KZazBEonSMnZfZ7vFdE", "KnvZfZ7vA1n", "KnvZfZ7vAkF", "KnvZfZ7vAvk"],
    "ComedyEvent": ["51"],
    "EducationEvent": ["104"],
    "ExhibitionEvent": ["14", "105", "218", "514", "514", "592", "754"],
    "Festival": ["54"],
    "ScreeningEvent": ["59"],
    "SportsEvent": ["7", "8", "9", "11", "25", "27", "30", "31", "33", "102", "205", "206", "225", "582", "676", "677",
                    "693", "694", "695", "711", "713", "716", "718", "729", "742", "765", "830", "10004", "KnvZfZ7vAeI",
                    "KnvZfZ7vAet", "KnvZfZ7vAen", "KnvZfZ7vAel", "KnvZfZ7vAdv", "KnvZfZ7vAde", "KnvZfZ7vAdd",
                    "KnvZfZ7vAd7", "KnvZfZ7vAdA", "KnvZfZ7vAdk", "KnvZfZ7vAdF", "KnvZfZ7vAda", "KnvZfZ7vAd1",
                    "KnvZfZ7vAJF", "KnvZfZ7vAdJ", "KnvZfZ7vAJv", "KnvZfZ7vAJ7", "KnvZfZ7vA1l", "KnvZfZ7vAdE",
                    "KnvZfZ7vAdt", "KnvZfZ7vAdn", "KnvZfZ7vAdl", "KnvZfZ7vAdI", "KnvZfZ7vA7v", "KnvZfZ7vA7e",
                    "KnvZfZ7vA77", "KnvZfZ7vA7d", "KnvZfZ7vA7A", "KnvZfZ7vA7k", "KnvZfZ7vA76", "KnvZfZ7vAea",
                    "KnvZfZ7vAJA", "KnvZfZ7vA7a", "KnvZfZ7vA71", "KnvZfZ7vA7J", "KnvZfZ7vAd6", "KnvZfZ7vA7E",
                    "KnvZfZ7vAJd", "KnvZfZ7vA7I", "KnvZfZ7vA7t", "KnvZfZ7vA7n", "KnvZfZ7vA7l", "KnvZfZ7vAAv",
                    "KnvZfZ7vAAe", "KnvZfZ7vAAd", "KnvZfZ7vAA7", "KnvZfZ7vAAA", "KnvZfZ7vAAk", "KZFzniwnSyZfZ7v7nE"],
    "TheaterEvent": ["12", "13", "22", "23", "32", "207", "209", "509", "558", "10002", "KnvZfZ7v7nt", "KnvZfZ7v7na",
                     "KnvZfZ7v7n1", "KnvZfZ7v7nl", "KnvZfZ7v7le", "KnvZfZ7v7lF", "KnvZfZ7v7l1", "KnvZfZ7v7nJ",
                     "KnvZfZ7vAe1", "KnvZfZ7v7nE", "KnvZfZ7v7nI", "KnvZfZ7v7nn", "KnvZfZ7v7lv", "KnvZfZ7v7ld",
                     "KnvZfZ7v7l7", "KnvZfZ7v7lA", "KnvZfZ7v7lk", "KnvZfZ7v7l6", "KnvZfZ7v7la", "KnvZfZ7v7lJ",
                     "KZFzniwnSyZfZ7v7na"]
}


class TicketmasterScrapper:
    @staticmethod
    def convert_to_nz_time(datetime_str):
        dt = parser.isoparse(datetime_str)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        nz_dt = dt.astimezone(nz_timezone)
        return nz_dt

    @staticmethod
    def get_image_url_with_timeout(page: Page, timeout=10):
        start_time = time.time()
        while True:
            try:
                sleep(random.uniform(2, 3))
                image_urls = page.locator("img").all()
                image_url = ""
                for loop_url in image_urls:
                    loop_url = loop_url.evaluate("img => img.src")
                    if "EVENT_DETAIL_PAGE" in loop_url:
                        image_url = loop_url
                return image_url.split(",")[0]
            except Exception:
                if time.time() - start_time > timeout:
                    Logger.warning("Timeout reached. Image element not found.")
                    return None
                sleep(random.uniform(7, 12))

    @staticmethod
    def get_description(div: Locator) -> Optional[str]:
        sub_divs = div.locator("div").all()
        if not sub_divs:
            text = div.text_content() or ""
            if "Event Info" in text:
                return text
            else:
                return None
        else:
            for sub_div in sub_divs:
                sub_text = TicketmasterScrapper.get_description(sub_div)
                if sub_text:
                    return re.sub(r"Event Info", "", sub_text)
            return None

    @staticmethod
    def get_event(url: str, category: str, page: Page) -> Optional[EventInfo]:
        sleep(random.uniform(1, 3))
        goto_with_retry(page, url)
        sleep(random.uniform(1, 3))
        if "ticketmaster.co.nz" in url:
            start_time = time.time()
            info_button: Optional[Locator] = None
            while True:
                if page.get_by_text("More Info").count():
                    info_button = page.get_by_text("More Info").first
                    break
                else:
                    if time.time() - start_time > 10:
                        break
                    sleep(random.uniform(7, 12))
            image_url = TicketmasterScrapper.get_image_url_with_timeout(page)
            Logger.debug("ticketmaster.co.nz")
            if not info_button:
                Logger.warning(f"no info button for: {url}")
                return []
            deets_count = 0
            while True:
                # "More Info" is often covered by an overlay/sticky bar (Playwright reports the
                # click "intercepts pointer events"); dispatch the event directly so it isn't
                # blocked by the actionability check.
                if info_button.count():
                    info_button.dispatch_event("click")
                sleep(random.uniform(1, 3))
                deets = page.locator("[data-testid='panel']").all()
                if not deets:
                    deets = page.locator("[class*='SidePanel__StyledContent']").all()
                if deets:
                    event_details = deets[0]
                    break
                if deets_count >= 3:
                    return []
                deets_count += 1
            divs = event_details.locator("div").all()
            title = None
            venue = None
            description = TicketmasterScrapper.get_description(event_details)
            dates = []
            for div in divs:
                text = div.text_content() or ""
                if not venue and "Venue" in text:
                    text = re.sub("BackEvent Info", "", text)
                    text = re.sub("Date", ";", text)
                    text = re.sub("Venue", ";", text)
                    text = text.split("Please")[0]
                    parts = text.split(";")
                    title = None
                    for part in parts:
                        if parts and not title:
                            title = part
                        matches = re.findall(r"\d{1,2}\s*[aA-zZ]{3,4}\s*\d{4},\s*[0-9:]*\s*[aAmMpP]{2}", part)
                        for match in matches:
                            try:
                                dates.append(parser.parse(match))
                            except Exception:
                                Logger.debug("no parts")
                                Logger.debug(part)
                        venue = parts[-1]
                    Logger.debug(venue)
                    Logger.debug(dates)
                    break
            if not title or not venue:
                Logger.warning("no title")
                return None
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source=ScraperName.TICKET_MASTER,
                             event_type=category,
                             description=description)
        elif "universe.com" in url:
            Logger.debug("universe.com")
            content = page.locator("[class*='content']").first
            title = content.locator("[class*='heading']").first.inner_text()
            image_url = page.locator("[class*='heroImage']").first.evaluate("a => a.style.cssText")
            image_url = re.findall(r'url\("([^"]+)"\)', image_url)[0]
            date_string, venue = content.locator("[class*='location']").all()
            venue = venue.inner_text()
            description = page.locator("[id*='escription']").first.inner_text()
            date_string = date_string.inner_text()
            dates = []
            if "Multiple" in date_string:
                page.evaluate("window.scrollBy(0, 1000)")
                sleep(random.uniform(3, 7))
                frame = page.frame_locator("iframe[title='Event Dates Calendar']")
                days = frame.locator("[aria-disabled='false']").all()
                for day in days:
                    ds = day.get_attribute("aria-label")
                    parts = ds.split(",")
                    ds = f"{parts[1]} {parts[2]} 1:01AM"
                    dates.append(parser.parse(ds))
                frame.locator("#x").click()
            else:
                Logger.warning(f"new date format found for{url}")
            Logger.debug(image_url)
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source=ScraperName.TICKET_MASTER,
                             event_type=category,
                             description=description)
        elif "moshtix.co" in url:
            Logger.debug("moshtix.co")
            title = page.locator("#event-summary-title").first.inner_text()
            image_url = (page
                         .locator(".page_headleftimage").first
                         .locator("img").first
                         .evaluate("img => img.src"))
            if "https:" not in image_url:
                image_url = "https:" + image_url
            venue = page.locator(".event-venue").first.inner_text()
            date_string = page.locator(".event-date").first.inner_text()
            date_matches = re.findall(r"\d{1,2}:\d{2}[amp]{2},\s[aA-zZ]{3}\s\d{1,2}\s[aA-zZ]*,\s\d{4}", date_string)
            dates = []
            for date_match in date_matches:
                date_parts = date_match.split(",")
                date_day = " ".join(date_parts[1].split(" ")[1:])
                date_string = f"{date_day}{date_parts[-1]} {date_parts[0]}"
                Logger.debug(date_string)
                dates.append(parser.parse(date_string))
            #  4:00pm, Sat 6 September, 2025 - 3:00am, Sun 7 September, 2025
            details = page.locator("#event-details-section").first
            description = details.locator("[class*='moduleseparator']").first.inner_text()
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source=ScraperName.TICKET_MASTER,
                             event_type=category,
                             description=description)
        return None

    @staticmethod
    def get_urls(previous_urls: set, previous_titles: set, from_file: bool, urls_file: TextIO) -> List[Tuple[str, str]]:
        event_urls: List[Tuple[str, str]] = []
        if from_file:
            return FileUtils.load_from_files(ScraperName.TICKET_MASTER)[1]
        urls_file.write("[\n")

        class PossibleKeys(str, Enum):
            id = 'id'
            total = 'total'
            title = 'title'
            discoveryId = 'discoveryId'
            dates = 'dates'
            presaleDates = 'presaleDates'
            url = 'url'
            partnerEvent = 'partnerEvent'
            isPartner = 'isPartner'
            showTmButton = 'showTmButton'
            venue = 'venue'
            timeZone = 'timeZone'
            cancelled = 'cancelled'
            postponed = 'postponed'
            rescheduled = 'rescheduled'
            tba = 'tba'
            local = 'local'
            sameRegion = 'sameRegion'
            soldOut = 'soldOut'
            limitedAvailability = 'limitedAvailability'
            ticketingStatus = 'ticketingStatus'
            eventChangeStatus = 'eventChangeStatus'
            virtual = 'virtual'
            artists = 'artists'
            price = 'price'
            startDate = 'startDate'
            endDate = 'endDate'
            name = 'name'
            events = 'events'
            city = 'city'

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "priority": "u=1, i",
            "referer": "https://www.ticketmaster.co.nz/search?q=wellington",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "x-tmregion": "750",
            "Cache-Control": "no-cache",
            "Host": "www.ticketmaster.co.nz",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        page = 0
        count = 0
        while True:
            Logger.info(f"fetching page {page}")
            api_url = f'https://www.ticketmaster.co.nz/api/search/events?q=wellington&region=750&sort=date&page={page}'
            r = requests.get(url=api_url, headers=headers)
            if r.status_code != 200:
                return []
            try:
                data = r.json()
                if not data[PossibleKeys.events]:
                    return []
                index = 0
                cat = ""
                mcat = data["events"][0]["majorCategory"]
                while index < 10:
                    if "id" in mcat.keys():
                        cat = mcat["id"]
                        break
                    else:
                        mcat = data["events"][index]["majorCategory"]
                        index += 1

                category_name = None
                for m in majorCats.keys():
                    key, value = m, majorCats[m]
                    if cat in value:
                        category_name = key
                        break
                if not category_name:
                    for m in minorCats.keys():
                        key, value = m, minorCats[m]
                        if cat in value:
                            category_name = key
                            break
                category_name = category_name if category_name else "Other"

                count += len(data[PossibleKeys.events])
                for event in data[PossibleKeys.events]:
                    event_url = event[PossibleKeys.url]
                    title = event[PossibleKeys.title]
                    if event_url in previous_urls or title in previous_titles:
                        continue
                    previous_titles.add(title)
                    previous_urls.add(event_url)
                    event_urls.append((event_url, category_name))
                    json.dump((event_url, category_name), urls_file, indent=2)
                    urls_file.write(",\n")
                if count >= data[PossibleKeys.total]:
                    break
                page += 1
            except Exception as e:
                Logger.warning("ticket master error")
                Logger.warning(str(e))
                count += 1
        urls_file.write("]\n")
        return event_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.TICKET_MASTER)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.TICKET_MASTER)))
        events: List[EventInfo] = []
        # get_urls is the requests-based Ticketmaster API — no browser needed for it.
        event_urls = TicketmasterScrapper.get_urls(previous_urls, previous_titles, False, urls_file)
        with sync_playwright() as playwright:
            # Event detail pages (ticketmaster.co.nz / universe.com / moshtix) are bot-protected.
            context = launch_stealth(playwright, headless=False)
            page = context.new_page()
            out_file.write("[\n")
            for part in event_urls:
                Logger.info(f"category: {part[1]} url: {part[0]}")
                try:
                    event = TicketmasterScrapper.get_event(part[0], part[1], page)
                    if event:
                        events.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
                    else:
                        Logger.debug("no event returned")
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.warning(str(e))
                        json.dump(part[0], banned_file, indent=2)
                        banned_file.write(",\n")
                    else:
                        raise e
                Logger.divider()
            out_file.write("]\n")
            context.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(TicketmasterScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
