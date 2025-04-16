from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from DateFormatting import DateFormatting
from EventInfo import EventInfo
from datetime import datetime
import json


class UnderTheRaderScrapper:
    @staticmethod
    def fetch_events() -> [EventInfo]:
        events: [EventInfo] = []
        driver = webdriver.Chrome()
        driver.get("https://www.undertheradar.co.nz/utr/gigRegion/Wellington")
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "vevent")))
        html = driver.find_elements(By.CLASS_NAME, 'vevent')
        for event in html:
            imageURL = event.find_element(By.CSS_SELECTOR, ".gig-image img").get_attribute("data-original")
            date = event.find_element(By.CLASS_NAME, 'lite').text
            cleaned_date_str = DateFormatting.cleanUpDate(date)
            date_obj = datetime.strptime(cleaned_date_str, '%a %d %B %I:%M%p')
            date_obj = DateFormatting.replaceYear(date_obj)
            title: str = event.find_element(By.CLASS_NAME, 'gig-title').text
            venue = event.find_element(By.CLASS_NAME, 'venue-title').text
            title_element = event.find_element(By.CLASS_NAME, "gig-title").find_element(By.TAG_NAME, "a")
            url = title_element.get_attribute("href")
            try:
                events.append(EventInfo(name=title,
                                        dates=[date_obj],
                                        image=imageURL,
                                        url=url,
                                        venue=venue,
                                        source="under the radar",
                                        eventType="Music"))
            except Exception as e:
                print(f"under the radar: {e}")
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(UnderTheRaderScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)