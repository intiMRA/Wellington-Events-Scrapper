import json

from util import CurrentFestivals
from util.DateFormatting import DateFormatting
from util import FileUtils
from util import paths
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, Dict, Tuple, TextIO
from time import sleep
from playwright.sync_api import sync_playwright, Page, Locator
from util.PlaywrightUtils import goto_with_retry, new_context
from util.Logger import Logger

class RoxyScrapper:
    @staticmethod
    def get_event(url: str, page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(3)
        if not page.locator(".single-movie__title").all():
            return None

        title = page.locator(".single-movie__title").first.inner_text()
        sticky_wrapper: Locator = page.locator("[class*='sticky-inner-wrapper']").first
        image_url = sticky_wrapper.locator("img").evaluate("img => img.src")
        time_elements = page.locator(".single-session").all()
        dates = []
        for time_element in time_elements:
            date_string: str = time_element.locator(".single-session__date").first.inner_text()
            date_string = date_string.split(" | ")[-1]
            date_time = page.locator(".time-slot__time").first.inner_text()
            dates.append(parser.parse(f"{date_string} {date_time}"))
        description = page.locator(".single-movie__description").first.inner_text()
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue="The Roxy Cinema, 5 Park Road, Miramar, Wellington",
                         source=ScraperName.ROXY,
                         event_type="Film & Media",
                         description=description)

    @staticmethod
    def get_event_fom_page(url: str, page: Page, previous_urls: Set[str]) -> Optional[EventInfo]:
        goto_with_retry(page, url)
        sleep(3)
        if not page.locator(".poster-portrait-link").count():
            return None
        event_url = page.locator(".poster-portrait-link").first.evaluate("p => p.href")
        if event_url in previous_urls:
            return None
        return RoxyScrapper.get_event(event_url, page)

    @staticmethod
    def get_festival_urls(url: str, page: Page) -> Set[Tuple[str, str]]:
        if "doc-edge-film-festival" in url:
            return RoxyScrapper.get_festival_urls_doc_edge(url, page)
        goto_with_retry(page, url)
        sleep(3)
        page.evaluate(f"window.scrollBy(0, {400});")
        height = page.evaluate("document.body.scrollHeight")

        scrolled_amount = 0
        while True:
            if scrolled_amount > height:
                break
            page.evaluate(f"window.scrollBy(0, {400});")
            scrolled_amount += 400
            sleep(1)
        films = page.locator(".poster-portrait-link").all()
        return set([(film.evaluate("f => f.href"), "") for film in films])

    @staticmethod
    def get_festival_urls_doc_edge(url: str, page: Page)-> Set[Tuple[str, str]]:
        goto_with_retry(page, url)
        sleep(3)
        links = page.locator('a').all()
        event_urls = set()
        for link in links:
            image_element: List[Locator] = link.locator('img').all()
            if not image_element:
                continue
            image_url = image_element[0].evaluate('img => img.src')
            text = link.evaluate("a => a.href")
            if "docedge.nz" in text:
                event_urls.add((text, image_url))
        return event_urls

    @staticmethod
    def get_event_doc_edge(url: Tuple[str, str], page: Page) -> Optional[EventInfo]:
        goto_with_retry(page, url[0])
        sleep(3)
        title = page.locator("[class*='elementor-heading-title']").first.inner_text()
        description = page.locator("[class*='elementor-widget-text-editor']").first.inner_text()
        image_url = url[-1]
        date_elements = page.locator("[class*='timeRow']").all()
        dates = []
        for date_element in date_elements:
            text = date_element.inner_text()
            if "The Roxy" not in text:
                continue
            date_string = text.split("\n")[0]
            if "to" in date_string:
                start_string, end_string = date_string.split(" to ")
                Logger.info(date_string)
                Logger.info(f"{url}")
                dates = list(DateFormatting.create_range(parser.parse(start_string), parser.parse(end_string)))
            else:
                try:
                    dates.append(parser.parse(date_string))
                except Exception as e:
                    Logger.info(f"failed to parse date {date_string} {e}")
                    continue
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url[0],
                         venue="The Roxy Cinema, 5 Park Road, Miramar, Wellington",
                         source=ScraperName.ROXY,
                         event_type="Film & Media",
                         description=description)

    @staticmethod
    def get_events(films_urls: Set[str], page: Page, previous_urls: Set[str], out_file) -> List[EventInfo]:
        events = []
        for films_url in films_urls:
            Logger.info(f"url: {films_url}")
            try:
                event = RoxyScrapper.get_event_fom_page(films_url, page, previous_urls)
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
        return events

    @staticmethod
    def get_festivals(festivals: List[Dict[str, str]], page: Page):
        for festivals in festivals:
            festival_name = festivals['name']
            festival_name = festival_name.lower()
            festival_name = festival_name.title()
            file_festival_name = festival_name.lower().replace(" ", "-")
            festival_url = festivals['url']
            Logger.info(f"festival: {festival_name}")
            CurrentFestivals.CURRENT_FESTIVALS.append("RoxyFestival")
            CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
                "id": "RoxyFestival",
                "name": festival_name,
                "icon": "movie",
                f"url": f"https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/{file_festival_name}.json"
            })

            festival_file = open(paths.root_path(f"{file_festival_name}.json"), mode="w")
            event_urls = RoxyScrapper.get_festival_urls(festival_url, page)
            events = []
            for event_url in event_urls:
                Logger.info(f"fetching: {event_url}")
                try:
                    if "docedge.nz" in event_url[0]:
                        event = RoxyScrapper.get_event_doc_edge(event_url, page)
                    else:
                        event = RoxyScrapper.get_event(event_url[0], page)
                    if event:
                        events.append(event.to_dict())
                except Exception as e:
                    if "No dates found for" in str(e):
                        Logger.divider()
                        Logger.warning(str(e))
                    else:
                        Logger.divider()
                        raise e
                Logger.divider()
            json.dump({"events": sorted(events, key=lambda evt: evt["name"])}, festival_file, indent=2)
            festival_file.close()
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        with sync_playwright() as playwright:
            out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.ROXY)
            previous_urls = previous_urls.union(set(FileUtils.load_banned(ScraperName.ROXY)))
            browser = playwright.chromium.launch(headless=True)
            context = new_context(browser)
            page = context.new_page()
            goto_with_retry(page, "https://www.roxycinema.co.nz/")
            sleep(3)
            more_button = page.locator("[class*='primary-menu__link--more']").first
            more_button.click()
            festivals_urls: List[Dict[str, str]] = []
            films_urls = set()
            values_to_extract = ["eat the film", "feast your eyes", "roxy retro", "tea time talkies"]
            navs = page.locator("[class*='menu__link']").all()
            processed = set()
            for nav in navs:
                text = nav.inner_text()
                url = nav.evaluate("a => a.href")
                if text in processed:
                    continue
                if "festival" in text.lower():
                    festivals_urls.append({"name": text, "url": url})
                elif text.lower() in values_to_extract:
                    films_urls.add(url)
                processed.add(text)
            out_file.write("[\n")
            events = RoxyScrapper.get_events(films_urls, page, previous_urls, out_file)
            out_file.write("]\n")
            RoxyScrapper.get_festivals(festivals_urls, page)
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(RoxyScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))