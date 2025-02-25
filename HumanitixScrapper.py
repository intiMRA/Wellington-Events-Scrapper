# https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463
# https://humanitix.com/_next/data/hze7h3WN8iE4RUuQho5-Z/nz/search.json?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463&page=0
from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re
from datetime import datetime
from DateFormatting import DateFormatting
import json

class HumanitixScrapper:
    @staticmethod
    def get_date(dateString: str) -> [datetime]:
        if re.findall(r"([A-Za-z]{3},\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[amp]+\s-\s\d+([:]*\d{1,2})?[amp]+\s[aA-zZ]*)", dateString):
            matchString = re.findall(r"([A-Za-z]{3},\s\d{1,2}\s[aA-zZ]{3})", dateString)[0]

            date = datetime.strptime(matchString, '%a, %d %b')
            return [date]
        elif re.findall(r"([A-Za-z]{3},\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[amp]+\s-\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[amp]+\s[aA-zZ]*)", dateString):
            startDateString = re.findall(r'([A-Za-z]{3},\s\d{1,2}\s[aA-zZ]{3})', dateString)[0]
            endDateString = re.findall(r'(\d{1,2}\s[aA-zZ]{3})', dateString)[-1]
            startDate = datetime.strptime(startDateString, '%a, %d %b')
            endDate = datetime.strptime(endDateString, '%d %b')
            return [startDate, endDate]
        else:
            print("fail")
            print(dateString)
            print("-" * 15)
            return []
    @staticmethod
    def fetch_events() -> [EventInfo]:
        events: [EventInfo] = []
        driver = webdriver.Chrome()
        page = 0
        while True:
            url = f'https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463&page={page}'
            driver.get(url)
            height = driver.execute_script("return document.body.scrollHeight")
            scrolledAmount = 0
            while True:
                if scrolledAmount > height:
                    break
                driver.execute_script(f"window.scrollBy(0, {100});")

                scrolledAmount += 100
            eventsData = driver.find_elements(By.CLASS_NAME, 'lbYPyp')
            if not eventsData:
                return events
            for event in eventsData:
                title = event.find_element(By.CLASS_NAME, 'PvMBQ').text
                dateString = event.find_element(By.CLASS_NAME, 'fMFwJG').text
                imageURL = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                venue = event.find_element(By.CLASS_NAME, 'cgLmvO').text
                eventUrl = event.get_attribute('href')
                dates = HumanitixScrapper.get_date(dateString)
                if len(dates) == 2:
                    startDate, endDate = dates
                    dateStamp = DateFormatting.formatDateStamp(startDate)
                    lastDateStamp = DateFormatting.formatDateStamp(endDate)
                    dateStamps = [dateStamp, lastDateStamp]
                    displayDate = DateFormatting.formatDisplayDate(startDate) + " to " + DateFormatting.formatDisplayDate(endDate)
                else:
                    date = dates[0]
                    dateStamps = [DateFormatting.formatDateStamp(date)]
                    displayDate = DateFormatting.formatDisplayDate(date)
                events.append(EventInfo(name=title,
                                        dates=dateStamps,
                                        displayDate=displayDate,
                                        image=imageURL,
                                        url=eventUrl,
                                        venue=venue,
                                        source="humanitix"))
            page += 1
        return events