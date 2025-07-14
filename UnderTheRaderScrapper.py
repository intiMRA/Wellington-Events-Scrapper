import re
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from DateFormatting import DateFormatting
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional

class UnderTheRaderScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "display_title_1").text
        header = driver.find_element(By.CLASS_NAME, "col-md-9").text.split("\n")
        date_string = header[2].split(",")[0]
        parts = date_string.split(" ")
        date = parser.parse(f"{parts[1]} {parts[2]}")
        image_url = driver.find_element(By.CLASS_NAME, "img-responsive").get_attribute('src')
        venue = header[4]
        description = driver.find_element(By.CLASS_NAME, "description").text
        return EventInfo(name=title,
                        dates=[date],
                        image=image_url,
                        url=url,
                        venue=venue,
                        source="Under The Radar",
                        eventType="Music",
                         description=description)

    @staticmethod
    def fetch_events(previousTitles: Set[str]) -> List[EventInfo]:
        events: List[EventInfo] = []
        driver = webdriver.Chrome()
        driver.get("https://www.undertheradar.co.nz/utr/gigRegion/Wellington")
        while True:
            try:
                loadModeButton = driver.find_element(By.XPATH, "//a[contains(., 'Load More')]")
                loadModeButton.click()
                sleep(1)
            except:
                break
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "vevent")))
        html = driver.find_elements(By.CLASS_NAME, 'vevent')
        for event in html:
            title: str = event.find_element(By.CLASS_NAME, 'gig-title').text
            if title in previousTitles:
                continue
            imageURL = event.find_element(By.CSS_SELECTOR, ".gig-image img").get_attribute("data-original")
            date = event.find_element(By.CLASS_NAME, 'lite').text
            cleaned_date_str = DateFormatting.cleanUpDate(date)
            match = re.findall(r"(\d{1,2}\s\w+\s\d{1,2}[:0-9AMP]+)", cleaned_date_str)[0]
            date_obj = parser.parse(match)
            date_obj = DateFormatting.replaceYear(date_obj)
            venue = event.find_element(By.CLASS_NAME, 'venue-title').text
            title_element = event.find_element(By.CLASS_NAME, "gig-title").find_element(By.TAG_NAME, "a")
            url = title_element.get_attribute("href")
            try:
                events.append(EventInfo(name=title,
                                        dates=[date_obj],
                                        image=imageURL,
                                        url=url,
                                        venue=venue,
                                        source="Under The Radar",
                                        eventType="Music"))
            except Exception as e:
                print(f"under the radar: {e}")
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(UnderTheRaderScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)