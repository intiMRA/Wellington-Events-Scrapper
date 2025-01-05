#

from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re

class EventFinderScrapper:
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
                imageURL = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                date = event.find_element(By.CLASS_NAME, 'dtstart').text
                title: str = event.find_element(By.CLASS_NAME, 'card-title').text
                venue = event.find_element(By.CLASS_NAME, 'p-locality').text
                title_element = event.find_element(By.CLASS_NAME, "card-title").find_element(By.TAG_NAME, "a")
                eventURL = title_element.get_attribute("href")
                events.append(EventInfo(name=title, date=date,image=imageURL, url=eventURL, venue=venue))
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
                eventsDict[event.name] = EventInfo(name=event.name, date=event.date + " - More dates",image=event.image, url=event.url, venue=event.venue)
            else:
                eventsDict[event.name] = EventInfo(name=event.name, date=event.date , image=event.image, url=event.url, venue=event.venue)
        return list(eventsDict.values())