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
from dateutil import parser
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
    def getAllEventDates(url: str, title: str) -> [datetime]:
        dateObjects = []
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
                    fullString = dateString
                    dateString = dateString.split(",")[0]
                    if len(dateString.split("–")) > 1:
                        start, last = dateString.split("–")
                        hour = fullString.split(",")[-1].split("–")[0]
                        start += " " + hour
                        last += " " + hour
                        start_date_obj = parser.parse(start)
                        end_date_obj = parser.parse(last)

                        start_date_obj = DateFormatting.replaceYear(start_date_obj)

                        end_date_obj = DateFormatting.replaceYear(end_date_obj)
                        dateObjects = list(DateFormatting.createRange(start_date_obj, end_date_obj))
                    else:
                        dateString = dateString + " " + fullString.split(",")[-1].split("–")[0]
                        date_obj = parser.parse(dateString)
                        date_obj = DateFormatting.replaceYear(date_obj)
                        dateObjects.append(date_obj)
                except Exception as e:
                    print("error: ", dateString, " title: ", title)
                    print(f"event finder: {e}")
            driver.close()
            return dateObjects
        except Exception as e:
            print("error: ", url, " title: ", title)
            print(f"event finder: {e}")
        return dateObjects

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
            print("error: ", url)
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
                title = None
                try:
                    title = event.find_element(By.CLASS_NAME, 'p-name').text
                except:
                    print(f"no title: {event.text}")
                    continue
                title_element = event.find_element(By.CLASS_NAME, "card-title").find_element(By.TAG_NAME, "a")
                try:
                    eventURL = title_element.get_attribute("href")
                except:
                    print(f"invalid event: {title}")
                try:
                    imageURL = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                except Exception as e:
                    print(f"event finder no image found: {eventURL}")

                metaDate = event.find_element(By.CLASS_NAME, "meta-date").text
                date = event.find_element(By.CLASS_NAME, 'dtstart').text
                dates = []
                if "more dates" in metaDate:
                    dates = EventFinderScrapper.getAllEventDates(eventURL, title)
                elif "Tomorrow" in date or "Today" in date:
                    dateObject = EventFinderScrapper.get_time_from_string(date)
                    dates.append(dateObject)
                else:
                    cleaned_date_str = DateFormatting.cleanUpDate(date)
                    try:
                        date_obj = parser.parse(cleaned_date_str)
                        date_obj = DateFormatting.replaceYear(date_obj)
                        dates.append(date_obj)
                    except:
                        print("event finder error: " + date)
                        print("title: " + event.find_element(By.CLASS_NAME, 'card-title').text)
                    if not date_obj:
                        print(f"event finder error: {event.text}")
                        dates.append(datetime.now())
                try:
                    venue = event.find_element(By.CLASS_NAME, 'p-locality').text
                except:
                    print(f"event finder error on locality: {url}")
                try:
                    events.append(EventInfo(
                        name=title,
                        dates=dates,
                        image=imageURL,
                        url=eventURL,
                        venue=venue,
                        source="event finder",
                        eventType="Other"))
                except Exception as e:
                    print(f"event finder: {e}")
                    pass
            driver.close()
            currentPage += 1

        return events

    @staticmethod
    def fetch_events() -> [EventInfo]:

        todaysEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/today"
        tomorrowsEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/tomorrow"
        thisWeekEndsEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/this-weekend"
        nextWeeksEventsUrl = "https://www.eventfinda.co.nz/whatson/events/wellington/next-week"
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
                try:
                    eventsDict[event.name] = EventInfo(name=event.name,
                                                       dates=list(map(lambda x: parser.parse(x), event.dates)),
                                                       image=event.image,
                                                       url=event.url,
                                                       venue=event.venue,
                                                       source="event finder",
                                                       eventType=event.eventType)
                except Exception as e:
                    print(f"event finder: {e}")
        return list(eventsDict.values())

# events = list(map(lambda x: x.to_dict(), sorted(EventFinderScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
