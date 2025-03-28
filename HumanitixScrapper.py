# https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463
# https://humanitix.com/_next/data/hze7h3WN8iE4RUuQho5-Z/nz/search.json?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463&page=0
from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re
from datetime import datetime
from DateFormatting import DateFormatting
import json
from dateutil import parser


class HumanitixScrapper:
    @staticmethod
    def get_date(dateString: str) -> [datetime]:
        try:
            if re.findall(r"([A-Za-z]{3},\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[ampAMP]+)", dateString):
                matchString = re.findall(r"([A-Za-z]{3},\s\d{1,2}\s[aA-zZ]{3})", dateString)[0]

                date = parser.parse(matchString)
                return [date]
            elif re.findall(
                    r"([A-Za-z]{3},\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[amp]+\s-\s\d+\s[aA-zZ]{3},\s\d+([:]*\d{1,2})?[amp]+\s[aA-zZ]*)",
                    dateString):
                startDateString = re.findall(r'([A-Za-z]{3},\s\d{1,2}\s[aA-zZ]{3})', dateString)[0]
                endDateString = re.findall(r'(\d{1,2}\s[aA-zZ]{3})', dateString)[-1]
                startDate = parser.parse(startDateString)
                endDate = parser.parse(endDateString)
                return [startDate, endDate]
            else:
                print("fail")
                print(dateString)
                print("-" * 15)
                return []
        except:
            print(dateString)

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
            eventsData = driver.find_elements(By.CLASS_NAME, 'test')
            if not eventsData:
                return events
            for event in eventsData:
                try:
                    venue = event.find_element(By.TAG_NAME, 'p')
                    dateString = event.find_elements(By.TAG_NAME, 'div')[-2].text

                    venue = venue.text
                    title = event.find_element(By.TAG_NAME, 'h6').text
                    imageURL = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    eventUrl = event.get_attribute('href')
                    dates = HumanitixScrapper.get_date(dateString)
                    events.append(EventInfo(name=title,
                                            dates=dates,
                                            image=imageURL,
                                            url=eventUrl,
                                            venue=venue,
                                            source="humanitix",
                                            eventType="Other"))
                except Exception as e:
                    print(f"humanitix: {e}")
                    print("error: ", event.text)
            page += 1
        return events

# events = list(map(lambda x: x.to_dict(), sorted(HumanitixScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
