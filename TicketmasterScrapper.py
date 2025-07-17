import json
import re
import subprocess
from time import sleep

import requests
from selenium.webdriver.remote.webelement import WebElement

import FileNames
import ScrapperNames
from EventInfo import EventInfo
from enum import Enum
from dateutil import parser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import pytz
from typing import List, Optional

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
    def get_image_url_with_timeout(driver, url: str, timeout=10):
        start_time = time.time()
        while True:
            try:
                if "moshtix" in url:
                    image_url = (driver
                                 .find_element(By.CLASS_NAME, "page_headleftimage")
                                 .find_element(By.TAG_NAME, "img")
                                 .get_attribute("src"))
                    if "https:" not in image_url:
                        image_url = "https:" + image_url
                else:
                    sleep(2)
                    image_urls = driver.find_elements(By.TAG_NAME, "img")
                    image_url = ""
                    for loop_url in image_urls:
                        loop_url = loop_url.get_attribute("src")
                        if "EVENT_DETAIL_PAGE" in loop_url:
                            image_url = loop_url
                return image_url
            except:
                if time.time() - start_time > timeout:
                    print("Timeout reached. Image element not found.")
                    return None
                time.sleep(10)

    @staticmethod
    def get_description(div: WebElement) -> Optional[str]:
        sub_divs = div.find_elements(By.TAG_NAME, "div")
        if not sub_divs:
            text = div.get_attribute("textContent")
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
    def get_event(url: str, category: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(1)
        if "ticketmaster.co.nz" in url:
            start_time = time.time()
            info_button = None
            while True:
                try:
                    info_button = driver.find_element(By.XPATH, "//button[contains(., 'More Info')]")
                    break
                except:
                    if time.time() - start_time > 10:
                        break
                    time.sleep(10)
            image_url = TicketmasterScrapper.get_image_url_with_timeout(driver, url)
            print("ticketmaster.co.nz")
            if not info_button:
                print(f"no info button for: {url}")
                raise Exception("")
            while True:
                info_button.click()
                deets = driver.find_elements(By.XPATH, "//section[@data-testid='panel']")
                if deets:
                    event_details = deets[0]
                    break
                sleep(1)
            divs = event_details.find_elements(By.TAG_NAME, "div")
            title = None
            date_string = None
            venue = None
            description = TicketmasterScrapper.get_description(event_details)
            for div in divs:
                text = div.get_attribute("textContent")
                if not venue and "Venue" in text:
                    text = re.sub("BackEvent Info", "", text)
                    text = re.sub("Date", ";", text)
                    text = re.sub("Venue", ";", text)
                    text = text.split("Please")[0]
                    parts = text.split(";")
                    title = parts[0]
                    date_string = re.findall(r"\d{1,2}\s[aA-zZ]{3,4}\s\d{4},\s[0-9:]*\s[aAmMpP]{2}", parts[1])[0]
                    venue = parts[2]
                    break
            dates = [parser.parse(date_string)]
            if not title or not venue:
                return None
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source="Ticket Master",
                             event_type=category,
                             description=description)
        elif "universe.com" in url:
            print("universe.com")
            content = driver.find_element(By.XPATH, "//div[contains(@class, 'content')]")
            title = content.find_element(By.XPATH, "//h2[contains(@class, 'heading')]").text
            image_url = driver.find_element(By.XPATH, "//*[contains(@class, 'heroImage')]").get_attribute("style")
            image_url = re.findall(r'url\("([^"]+)"\)', image_url)[0]
            date_string, venue = content.find_elements(By.XPATH, "//span[contains(@class, 'location')]")
            venue = venue.text
            description = driver.find_element(By.XPATH, "//div[contains(@class, 'description')]").text
            date_string = date_string.text
            dates = []
            if "Multiple" in date_string:
                driver.execute_script(f"window.scrollBy(0, 1000);")
                sleep(5)
                iframe_element = driver.find_element(By.XPATH, "//iframe[@title='Event Dates Calendar']")
                driver.switch_to.frame(iframe_element)
                days = driver.find_elements(By.XPATH, "//td[@aria-disabled='false']")
                for day in days:
                    ds = day.get_attribute("aria-label")
                    parts = ds.split(",")
                    ds = f"{parts[1]} {parts[2]} 1:01AM"
                    dates.append(parser.parse(ds))
            else:
                print(f"new date format found for{url}")
            print(image_url)
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source=ScrapperNames.TICKET_MASTER,
                             event_type=category,
                             description=description)
        elif "moshtix.co" in url:
            print("moshtix.co")
            title = driver.find_element(By.ID, "event-summary-title").text
            image_url = (driver
                         .find_element(By.CLASS_NAME, "page_headleftimage")
                         .find_element(By.TAG_NAME, "img")
                         .get_attribute("src"))
            if "https:" not in image_url:
                image_url = "https:" + image_url
            venue = driver.find_element(By.CLASS_NAME, "event-venue").text
            date_string = driver.find_element(By.CLASS_NAME, "event-date").text
            date_matches = re.findall(r"\d{1,2}:\d{2}[amp]{2},\s[aA-zZ]{3}\s\d{1,2}\s[aA-zZ]*,\s\d{4}", date_string)
            dates = []
            for date_match in date_matches:
                date_parts = date_match.split(",")
                date_day = " ".join(date_parts[1].split(" ")[1:])
                date_string = f"{date_day}{date_parts[-1]} {date_parts[0]}"
                print(date_string)
                dates.append(parser.parse(date_string))
            #  4:00pm, Sat 6 September, 2025 - 3:00am, Sun 7 September, 2025
            details = driver.find_element(By.ID, "event-details-section")
            description = details.find_element(By.XPATH, "//div[contains(@class, 'moduleseparator')]").text
            return EventInfo(name=title,
                             image=image_url,
                             venue=venue,
                             dates=dates,
                             url=url,
                             source="Ticket Master",
                             event_type=category,
                             description=description)
        return None

    @staticmethod
    def fetch_events(previous_urls: set) -> List[EventInfo]:
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

        events: List[EventInfo] = []
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
        # 1. First kill all Chrome processes
        subprocess.run(['pkill', '-f', 'Google Chrome'])
        options = Options()
        options.add_argument("--profile-directory=Profile 2")  # Specify profile name only

        # For Apple Silicon Macs
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        driver = webdriver.Chrome(options=options)

        event_urls: List[tuple[str, str]] = []
        while True:
            print(f"fetching page {page}")
            api_url = f'https://www.ticketmaster.co.nz/api/search/events?q=wellington&region=750&sort=date&page={page}'
            r = requests.get(url=api_url, headers=headers)
            if r.status_code != 200:
                driver.close()
                return events
            try:
                data = r.json()
                if not data[PossibleKeys.events]:
                    driver.close()
                    return events

                cat = data["events"][0]["majorCategory"]["id"]
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
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    event_urls.append((event_url, category_name))
                if count >= data[PossibleKeys.total]:
                    break
                page += 1
            except Exception as e:
                print("ticket master error")
                print(e)
                count += 1
        with open(FileNames.TICKET_MASTER_URLS, mode="w") as f:
            json.dump(event_urls, f, indent=2)
        out_file = open(FileNames.TICKET_MASTER_EVENTS, mode="w")
        out_file.write("[\n")
        for part in event_urls:
            print(f"category: {part[1]} url: {part[0]}")
            try:
                event = TicketmasterScrapper.get_event(part[0], part[1], driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
                else:
                    print("no event returned")
            except Exception as e:
                print(e)
            print("-"*100)
        out_file.write("]\n")
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(TicketmasterScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
