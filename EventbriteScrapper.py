# https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/
from datetime import datetime, timedelta
from DateFormatting import DateFormatting

from selenium.webdriver.common.by import By
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil.relativedelta import relativedelta
from dateutil import parser
import json
from time import sleep

class EventbriteScrapper:
    @staticmethod
    def getAllDates(url: str) -> [datetime]:
        driver = webdriver.Chrome()
        driver.get(url)
        sleep(1)
        dates = []
        try:
            driver.find_element(By.XPATH, "//div[contains(., 'looking for was not found')]")
            driver.close()
            return []
        except:
            pass
        try:
            elements = driver.find_elements(By.CLASS_NAME, "child-event-dates-item")
            for e in elements:
                parts = e.text.split("\n")
                if len(parts) > 3:
                    parts = parts[1:]
                    dateString = parts[0] + " " + parts[1] + " " + parts[2]
                    dates.append(DateFormatting.replaceYear(parser.parse(dateString)))
            driver.close()
            return dates
        except:
            return []
    @staticmethod
    def getCategories(driver: webdriver) -> [(str, str)]:
        categories = []
        driver.find_element(By.CLASS_NAME, "filter-toggle").click()
        filters = driver.find_element(By.CLASS_NAME, "filter-choice-items")
        cats = filters.find_elements(By.TAG_NAME, "li")
        for cat in cats:
            link = cat.find_element(By.TAG_NAME, "a").get_attribute("href")
            category = (cat.text, link)
            categories.append(category)
        return categories

    @staticmethod
    def getEvents(driver: webdriver, titles: set, category: str) -> [EventInfo]:
        curentPage = 1
        events = []
        while True:
            nextUrl = re.sub(r"page=\d+", f"page={curentPage}", driver.current_url)
            driver.get(nextUrl)
            try:
                sleep(1)
                pagination = driver.find_element(By.XPATH, "//li[@data-testid='pagination-parent']")
                firstPage, lastPage = pagination.text.split(" of ")
                firstPage = int(firstPage)
                lastPage = int(lastPage)
                if firstPage > lastPage:
                    return events
            except Exception as e:
                print(f"error finding paginstion: {e}")
            curentPage += 1
            #search-event
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='search-event']")
            for card in cards:
                imageUrl = card.find_element(By.CLASS_NAME, "event-card-image").get_attribute("src")
                titleTag = card.find_element(By.CLASS_NAME, "event-card-link ")
                eventLink = titleTag.get_attribute("href")
                texts = card.text.split("\n")

                tags = [
                    "Sales end soon",
                    "Selling quickly",
                    "Nearly full",
                    "Just added"
                ]

                soldTags = [
                    "Sold Out",
                    "Sales Ended",
                    "Unavailable"
                ]
                if texts[0] in soldTags :
                    continue
                if texts[0] in tags:
                    texts = texts[1:]
                title = texts[0]
                if title in titles:
                    continue
                titles.add(title)
                dateString = texts[1]
                venue = texts[2]

                if re.findall(r"\d+\s+more", dateString):
                    dates = EventbriteScrapper.getAllDates(eventLink)
                elif "," in dateString:
                    parts = dateString.split(",")[1:]
                    dateString = " ".join(parts)
                    date = DateFormatting.replaceYear(parser.parse(dateString))
                    dates = [date]
                else:
                    try:
                        if "Tomorrow" in dateString:
                            target_date = datetime.now() + timedelta(days=1)
                            dateString = re.sub("Tomorrow", f"{target_date.day}/{target_date.month}/{target_date.year}", dateString)
                        elif "Today" in dateString:
                            target_date = datetime.now()
                            dateString = re.sub("Today", f"{target_date.day}/{target_date.month}/{target_date.year}", dateString)
                        dates = [DateFormatting.replaceYear(parser.parse(dateString))]
                    except Exception as e:
                        print("texts: ", texts)
                        print("dateString: ", dateString)
                        print("error: ", e)
                        continue
                try:
                    events.append(EventInfo(name=title,
                                            image=imageUrl,
                                            venue=venue,
                                            dates=dates,
                                            url=eventLink,
                                            source="eventbrite",
                                            eventType=category))
                except Exception as e:
                    if "No dates found for" in str(e):
                        print("Eventbrite error: ", e)
                        continue
                    else:
                        raise e


    @staticmethod
    def fetch_events(previousTitles: set) -> [EventInfo]:
        events = []
        driver = webdriver.Chrome()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        cats = EventbriteScrapper.getCategories(driver)
        for cat in cats:
            catName, link = cat
            print("fetching: ", catName)
            driver.get(link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            #&start_date=2025-05-23&end_date=2025-06-29
            new_url = (driver.current_url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            driver.get(new_url)
            events += EventbriteScrapper.getEvents(driver, previousTitles, catName)

        return events
# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)