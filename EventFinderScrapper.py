
from xmlrpc.client import DateTime

from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from DateFormatting import DateFormatting
from selenium.webdriver.ie.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pandas
import json

class EventFinderScrapper:
    @staticmethod
    def get_time_from_string(time_string: str):
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
    def getAllEventDates(url: str, title: str) -> ([str], str):
        dateStamps = []
        try:
            driver = webdriver.Chrome()
            driver.get(url)
            try:
                allDatesButton = driver.find_element(By.CLASS_NAME, "show-more")
                allDatesButton.click()
            except:
                pass
            dateTable = driver.find_element(By.CLASS_NAME, "sessions-info")
            dates = dateTable.find_elements(By.TAG_NAME, "time")
            startDate = None
            for date in dates:
                dateString = date.get_attribute("datetime")
                try:
                    # datetime 2024-08-01, 09:00–13:00
                    dateString = dateString.split(",")[0]
                    if len(dateString.split("–")) > 1:
                        start, last = dateString.split("–")
                        start_date_obj = datetime.strptime(start, "%Y-%m-%d")
                        end_date_obj = datetime.strptime(last, "%Y-%m-%d")
                        range = pandas.date_range(start_date_obj, end_date_obj - timedelta(days=1))
                        if startDate == None:
                            startDate = DateFormatting.formatDisplayDate(start_date_obj)
                        for date in range:
                            stamp = DateFormatting.formatDateStamp(date)
                            if stamp in dateStamps:
                                continue
                            dateStamps.append(stamp)
                    else:
                        date_obj = datetime.strptime(dateString, '%Y-%m-%d')
                        if date_obj >= datetime.now():
                            dateStamp = DateFormatting.formatDateStamp(date_obj)
                            if startDate is None:
                                startDate = DateFormatting.formatDisplayDate(date_obj)
                            dateStamps.append(dateStamp)
                except:
                    print("error: ", dateString, " title: ", title)
            driver.close()
        except:
            print("error: ", url, " title: ", title)
        return dateStamps, startDate


    @staticmethod
    def getEvents(url: str) -> [EventInfo]:
        events: [EventInfo] = []
        driver = webdriver.Chrome()
        driver.get(url)
        lastPage = 1
        try:
            pagination = driver.find_element(By.CLASS_NAME, 'pagination')
            lastPage = int(re.sub('\W+', ' ', pagination.text).strip().split(" ")[-1])
        except:
            pass

        currentPage = 1
        driver.close()
        while currentPage <= lastPage:
            driver = webdriver.Chrome()
            pageURL = url + f'/page/{currentPage}'
            driver.get(pageURL)
            html = driver.find_element(By.CLASS_NAME, 'listings-events').find_elements(By.CLASS_NAME, 'card')
            for event in html:
                date_obj = None
                imageURL = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                title = event.find_element(By.CLASS_NAME, 'card-title').text
                title_element = event.find_element(By.CLASS_NAME, "card-title").find_element(By.TAG_NAME, "a")
                eventURL = title_element.get_attribute("href")
                metaDate = event.find_element(By.CLASS_NAME, "meta-date").text
                date = event.find_element(By.CLASS_NAME, 'dtstart').text
                dataStamps = None
                if "more dates" in metaDate:
                    dataStamps, displayDate = EventFinderScrapper.getAllEventDates(eventURL, title)
                elif "Tomorrow" in date or "Today" in date:
                    dateObject = EventFinderScrapper.get_time_from_string(date)
                    displayDate = DateFormatting.formatDisplayDate(dateObject)
                    dateStamp = DateFormatting.formatDateStamp(dateObject)
                else:
                    cleaned_date_str = DateFormatting.cleanUpDate(date)
                    try:
                        date_obj = datetime.strptime(cleaned_date_str, '%a %d %b %I:%M%p')
                    except:
                        print("error: " + date)
                        print("title: " + event.find_element(By.CLASS_NAME, 'card-title').text)
                        if cleaned_date_str:
                            date_obj = datetime.strptime(cleaned_date_str, '%a %d %b %Y %I:%M%p')
                    if not date_obj:
                        date_obj = datetime.now()
                    displayDate = DateFormatting.formatDisplayDate(date_obj)
                    dateStamp = DateFormatting.formatDateStamp(date_obj)
                if not dataStamps:
                    dataStamps = [dateStamp]
                venue = event.find_element(By.CLASS_NAME, 'p-locality').text
                events.append(EventInfo(
                    name=title,
                    dates=dataStamps,
                    displayDate=displayDate,
                    image=imageURL,
                    url=eventURL,
                    venue=venue,
                    source="event finder"))
            driver.close()
            currentPage += 1

        return events

    @staticmethod
    def fetch_events() -> [EventInfo]:

        todaysEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/today"
        tomorrowsEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/tomorrow"
        thisWeekEndsEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/this-weekend"
        nextWeeksEventsUrl ="https://www.eventfinda.co.nz/whatson/events/wellington/next-week"

        todaysEvents = EventFinderScrapper.getEvents(todaysEventsUrl)
        tomorrowsEvents = EventFinderScrapper.getEvents(tomorrowsEventsUrl)
        thisWeekEndsEvents = EventFinderScrapper.getEvents(thisWeekEndsEventsUrl)
        nextWeeksEvents = EventFinderScrapper.getEvents(nextWeeksEventsUrl)
        events: [EventInfo] = todaysEvents + tomorrowsEvents + thisWeekEndsEvents + nextWeeksEvents
        eventsDict = {}
        for event in events:
            if event.name in eventsDict.keys():
                continue
            else:
                eventsDict[event.name] = EventInfo(name=event.name,
                                                   dates=event.dates,
                                                   displayDate=event.displayDate,
                                                   image=event.image,
                                                   url=event.url,
                                                   venue=event.venue,
                                                   source="event finder")
        return list(eventsDict.values())

# events = list(map(lambda x: x.to_dict(), sorted(EventFinderScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)