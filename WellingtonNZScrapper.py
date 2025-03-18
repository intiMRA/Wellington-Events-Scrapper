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
                dateStamps = []
                if not title:
                    continue
                try:
                    venue = event.find_element(By.CLASS_NAME, 'event-content__info').text
                except:
                    venue = "not listed"
                # print(venue)
                dateString = event.find_element(By.CLASS_NAME, 'event-content__date').text
                if re.match(r"\d+ – \d+", dateString):
                    splitDateString = dateString.split(" – ")
                    date = datetime.strptime(splitDateString[-1], '%d %B %Y')
                    dateStamps = [DateFormatting.formatDateStamp(date)]
                    displayDate = DateFormatting.formatDisplayDate(date)
                elif re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):
                    match = re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = parser.parse(startDateString)
                    endDate = parser.parse(endDateString)

                    range = pandas.date_range(startDate, endDate - timedelta(days=1))

                    dateStamps = list(map(lambda x: DateFormatting.formatDateStamp(x), range))
                    displayDate = DateFormatting.formatDisplayDate(
                        startDate) + " to " + DateFormatting.formatDisplayDate(endDate)
                elif re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):
                    match = re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = parser.parse(startDateString)
                    endDate = parser.parse(endDateString)

                    range = pandas.date_range(startDate, endDate - timedelta(days=1))

                    dateStamps = list(map(lambda x: DateFormatting.formatDateStamp(x), range))
                    displayDate = DateFormatting.formatDisplayDate(
                        startDate) + " to " + DateFormatting.formatDisplayDate(endDate)
                elif dateString:
                    try:
                        date = datetime.strptime(dateString, '%d %B %Y')
                        dateStamps = [DateFormatting.formatDateStamp(date)]
                        displayDate = DateFormatting.formatDisplayDate(date)
                    except:
                        print(title)
                        print(dateString)
                        date = datetime.strptime(dateString, '%d %B %Y')
                        dateStamps = [DateFormatting.formatDateStamp(date)]
                        displayDate = DateFormatting.formatDisplayDate(date)
                else:
                    displayDate = "not listed"
                imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                # print(imageUrl)
                eventUrl = event.find_element(By.TAG_NAME, 'a').get_attribute('href')
                # print(eventUrl)

                eventInfo = EventInfo(name=title,
                                      image=imageUrl,
                                      venue=venue,
                                      dates=dateStamps,
                                      displayDate=displayDate,
                                      url=eventUrl,
                                      source="wellington nz",
                                      eventType="Other")
                events[cleanTitle] = eventInfo

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
            driver.implicitly_wait(2)
            numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
            numberOfEvents = re.findall("\d+", numberOfEvents.text)
            page += 1
        eventsInfo = WellingtonNZScrapper.slow_scroll_to_bottom(driver, 400)
        return list(eventsInfo)
# events = list(map(lambda x: x.to_dict(), sorted(WellingtonNZScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)