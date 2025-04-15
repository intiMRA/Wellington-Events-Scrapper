from time import sleep
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil import parser
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import pandas

class WellingtonNZScrapper:
    @staticmethod
    def slow_scroll_to_bottom(driver, scroll_increment=300) -> [EventInfo]:
        events = {}
        height = driver.execute_script("return document.body.scrollHeight")
        scrolledAmount = 0
        while True:
            if scrolledAmount > height:
                driver.close()
                return events.values()
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")

            scrolledAmount += scroll_increment
            rawEvents = driver.find_elements(By.CLASS_NAME, 'grid-item')
            for event in rawEvents:
                title = event.find_element(By.TAG_NAME, 'h2').text
                cleanTitle = re.match(r'[aA-zZ0-9]+', title)
                if cleanTitle in events.keys():
                    continue
                dateObjects = []
                if not title:
                    continue
                try:
                    venue = event.find_element(By.CLASS_NAME, 'event-content__info').text
                except:
                    venue = "not listed"
                dateString = event.find_element(By.CLASS_NAME, 'event-content__date').text
                if not dateString:
                    continue
                if re.match(r"\d+ – \d+", dateString):
                    first, rest = dateString.split(" – ")
                    if len(rest) > 2:
                        rest = rest.split(" ")
                        last = rest[0]
                        months = " ".join(rest[1:])
                        date1 = parser.parse(first + " " + months)
                        date2 = parser.parse(last + " " + months)
                        dateObjects = list(DateFormatting.createRange(date1, date2))
                    else:
                        splitDateString = dateString.split(" – ")
                        date = datetime.strptime(splitDateString[-1], '%d %B %Y')
                        dateObjects = [date]
                elif re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):

                    match = re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = parser.parse(startDateString)
                    endDate = parser.parse(endDateString)

                    dateObjects = list(DateFormatting.createRange(startDate, endDate))

                elif re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):

                    match = re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = parser.parse(startDateString)
                    endDate = parser.parse(endDateString)

                    dateObjects = list(DateFormatting.createRange(startDate, endDate))
                elif dateString:
                    date = parser.parse(dateString)
                    dateObjects = [date]
                else:
                    print(f"WellingtonNz failed to load: {event.text}")
                if not dateObjects:
                    print(dateString)
                    raise Exception(f"WellingtonNz failed to load: {event.text}")
                imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                eventUrl = event.find_element(By.TAG_NAME, 'a').get_attribute('href')
                try:
                    eventInfo = EventInfo(name=title,
                                          image=imageUrl,
                                          venue=venue,
                                          dates=dateObjects,
                                          url=eventUrl,
                                          source="wellington nz",
                                          eventType="Other")
                    events[cleanTitle] = eventInfo
                except Exception as e:
                    print(f"WellingtonNz: {e}")
                    pass

    @staticmethod
    def fetch_events() -> [EventInfo]:
        driver = webdriver.Chrome()
        driver.get('https://www.wellingtonnz.com/visit/events?mode=list')
        driver.switch_to.window(driver.current_window_handle)
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
        numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
        numberOfEvents = re.findall("\d+", numberOfEvents.text)
        page = 1
        while numberOfEvents[0] != numberOfEvents[1]:
            driver.get(f'https://www.wellingtonnz.com/visit/events?mode=list&page={page}')
            _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
            numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
            numberOfEvents = re.findall("\d+", numberOfEvents.text)
            page += 1
        eventsInfo = WellingtonNZScrapper.slow_scroll_to_bottom(driver, 400)
        return list(eventsInfo)
# events = list(map(lambda x: x.to_dict(), sorted(WellingtonNZScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)