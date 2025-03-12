from time import sleep
from datetime import datetime
from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from selenium import webdriver
import re


# import json

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
                title = event.find_element(By.CLASS_NAME, 'tile-content__title').text
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

                    startDate = datetime.strptime(startDateString, '%d %B %Y')
                    dateStamps = [DateFormatting.formatDateStamp(startDate), DateFormatting.formatDateStamp(endDate)]
                    endDate = datetime.strptime(endDateString, '%d %B %Y')
                    displayDate = DateFormatting.formatDisplayDate(
                        startDate) + " to " + DateFormatting.formatDisplayDate(endDate)
                elif re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):
                    match = re.match(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = datetime.strptime(startDateString, '%d %B')
                    endDate = datetime.strptime(endDateString, '%d %B %Y')
                    dateStamps = [DateFormatting.formatDateStamp(startDate),
                                  DateFormatting.formatDateStamp(endDate)]
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
                                      source="wellingtonNZ",
                                      eventType="Other")
                events[title] = eventInfo

    @staticmethod
    def fetch_events() -> [EventInfo]:
        driver = webdriver.Chrome()
        driver.get('https://www.wellingtonnz.com/visit/events?mode=list')
        sleep(3)
        numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
        numberOfEvents = re.findall("\d+", numberOfEvents.text)
        page = 1
        while numberOfEvents[0] != numberOfEvents[1]:
            driver.get(f'https://www.wellingtonnz.com/visit/events?mode=list&page={page}')
            sleep(3)
            numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
            numberOfEvents = re.findall("\d+", numberOfEvents.text)
            page += 1
        eventsInfo = WellingtonNZScrapper.slow_scroll_to_bottom(driver, 400)
        return list(eventsInfo)
