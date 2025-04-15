from selenium import webdriver
from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime


class ValhallaScrapper:
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
            html = driver.find_elements(By.CLASS_NAME, 'eventlist-event')
            for event in html:
                imageURL = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                date = event.find_element(By.CLASS_NAME, 'eventlist-column-date').text
                date = date.replace("\n", " ")
                dates = []
                firstDatePattern = r"([A-Za-z]{3} \d{1,2})"
                firstDate = re.findall(firstDatePattern, date)
                if not firstDate:
                    continue
                firstDate = firstDate[0]
                lastDatePattern = r"(\d{1,2} [A-Za-z]{3})"
                lastDate = re.findall(lastDatePattern, date)

                firstDateObject = datetime.strptime(firstDate, '%b %d')
                dates.append(firstDateObject)

                if lastDate:
                    lastDateObject = datetime.strptime(lastDate[0], '%d %b')
                    dates.append(lastDateObject)
                title: str = event.find_element(By.CLASS_NAME, 'eventlist-title').text
                venue = "Valhalla"
                title_element = event.find_element(By.CLASS_NAME, "eventlist-title").find_element(By.TAG_NAME, "a")
                url = title_element.get_attribute("href")
                if not title:
                    continue
                dates = list(map(lambda date: date.replace(year=datetime.today().year), dates))
                try:
                    eventInfo = EventInfo(name=title,
                                          dates=dates,
                                          image=imageURL,
                                          url=url,
                                          venue=venue,
                                          source="valhalla",
                                          eventType="Music")
                    events[title] = eventInfo
                except:
                    print(f"valhalla: {e}")

    @staticmethod
    def fetch_events() -> [EventInfo]:
        driver = webdriver.Chrome()
        driver.get("https://www.valhallatavern.com/events-1")
        return list(ValhallaScrapper.slow_scroll_to_bottom(driver, scroll_increment=1000))
