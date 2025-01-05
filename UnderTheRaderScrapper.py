from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo

class UnderTheRaderScrapper:
    @staticmethod
    def fetch_events() -> [EventInfo]:
        events: [EventInfo] = []
        driver = webdriver.Chrome()
        driver.get("https://www.undertheradar.co.nz/utr/gigRegion/Wellington")
        html = driver.find_elements(By.CLASS_NAME, 'vevent')
        for event in html:

            imageURL = event.find_element(By.CSS_SELECTOR, ".gig-image img").get_attribute("src")
            date = event.find_element(By.CLASS_NAME, 'lite').text
            title: str = event.find_element(By.CLASS_NAME, 'gig-title').text
            venue = event.find_element(By.CLASS_NAME, 'venue-title').text
            title_element = event.find_element(By.CLASS_NAME, "gig-title").find_element(By.TAG_NAME, "a")
            url = title_element.get_attribute("href")
            events.append(EventInfo(name=title, date=date,image=imageURL, url=url, venue=venue))
        driver.close()
        return events