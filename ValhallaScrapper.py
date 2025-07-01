from future.backports.datetime import timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from DateFormatting import DateFormatting
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set
from datetime import datetime
from time import sleep

class ValhallaScrapper:
    @staticmethod
    def get_dates(url: str) -> List[datetime]:
        driver = webdriver.Chrome()
        driver.get(url)
        sleep(1)
        start_time = driver.find_elements(By.CLASS_NAME, "event-time-localized-start")
        if start_time:
            date = driver.find_element(By.CLASS_NAME, 'event-date').text
            start_time_text = start_time[0].text
            driver.close()
            return [parser.parse(f"{date} {start_time_text}")]
        times = driver.find_elements(By.CLASS_NAME, "eventitem-meta-time")
        dates = driver.find_elements(By.CLASS_NAME, 'event-date')
        start_time = parser.parse(f"{dates[0].text} {times[0].text}")
        end_time = parser.parse(f"{dates[1].text} {times[1].text}")
        if end_time.day != start_time.day and abs(end_time - start_time) > timedelta(hours=5):
            driver.close()
            return [start_time, end_time]
        driver.close()
        return [start_time]

    @staticmethod
    def slow_scroll_to_bottom(driver, titles: Set[str], scroll_increment=300) -> List[EventInfo]:
        events = {}
        height = driver.execute_script("return document.body.scrollHeight")
        scrolledAmount = 0
        while True:
            if scrolledAmount > height:
                driver.close()
                return list(events.values())
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")

            scrolledAmount += scroll_increment
            html = driver.find_elements(By.CLASS_NAME, 'eventlist-event')
            for event in html:
                imageURL = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                title: str = event.find_element(By.CLASS_NAME, 'eventlist-title').text
                if not title or title in titles:
                    continue
                titles.add(title)
                venue = "Valhalla"
                title_element = event.find_element(By.CLASS_NAME, "eventlist-title").find_element(By.TAG_NAME, "a")
                url = title_element.get_attribute("href")
                dates = ValhallaScrapper.get_dates(url)
                dates = list(map(lambda date: DateFormatting.replaceYear(date), dates))
                try:
                    eventInfo = EventInfo(name=title,
                                          dates=dates,
                                          image=imageURL,
                                          url=url,
                                          venue=venue,
                                          source="Valhalla",
                                          eventType="Music")
                    events[title] = eventInfo
                except Exception as e:
                    print(f"valhalla: {e}")

    @staticmethod
    def fetch_events(titles: Set[str]) -> List[EventInfo]:
        driver = webdriver.Chrome()
        driver.get("https://www.valhallatavern.com/events-1")
        return list(ValhallaScrapper.slow_scroll_to_bottom(driver, titles, scroll_increment=1000))

# events = list(map(lambda x: x.to_dict(), sorted(ValhallaScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)