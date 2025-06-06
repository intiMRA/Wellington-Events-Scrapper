from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re
from datetime import datetime
from DateFormatting import DateFormatting
from dateutil import parser
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class HumanitixScrapper:

    @staticmethod
    def getDatesFromEvent(url)-> [datetime]:
        dates: [datetime] = []
        driver = webdriver.Chrome()
        driver.get(url)
        driver.maximize_window()
        driver.execute_script("window.scrollTo(200, 500);")
        while True:
            try:
                element = driver.find_element(By.XPATH, "//button[contains(., 'more dates')]")
                element.click()
                break
            except:
                driver.execute_script("window.scrollTo(200, 500);")
                sleep(1)
                pass
        form = driver.find_element(By.TAG_NAME, "form")
        listElements = form.find_elements(By.TAG_NAME, "li")
        for element in listElements:
            reg = r"(\d{1,2}\s[aA-zZ]{3},\s[aA-ZZ0-9:]*[amp]{2})"
            matches = re.findall(reg, element.text)
            if len(matches) > 1:
                startDate = parser.parse(matches[0].replace(",", ""))
                endDate = parser.parse(matches[-1].replace(",", ""))
                range = DateFormatting.createRange(startDate, endDate)
                for date in range:
                    dates.append(date)
            elif len(matches) == 1:
                date = parser.parse(matches[0])
                dates.append(date)
            else:
                print("date: ", element.text)
        driver.close()
        return dates

    @staticmethod
    def get_date(divStrings: [str], eventUrl: str) -> [datetime]:
        for dateString in divStrings:
            if "more times" in dateString:
                return HumanitixScrapper.getDatesFromEvent(eventUrl)
        for dateString in divStrings:
            try:
                if re.findall(r"(\d{1,2}\s[aA-zZ]{3},\s[aA-ZZ0-9:]*[AMP]{2})", dateString):
                    matchString = re.findall(r"(\d{1,2}\s[aA-zZ]{3},\s[aA-ZZ0-9:]*[AMP]{2})", dateString)[0]
                    matchString = matchString.replace(",", "")
                    date = parser.parse(matchString)
                    date = DateFormatting.replaceYear(date)
                    return [date]
            except Exception as e:
                print("humanitix failed to extract date from " + dateString)
                print(e)
    @staticmethod
    def formatInput(input_string):
        if not input_string:
            return input_string
        input_string = input_string.replace("&", "And").replace(" ", "").replace(",", "")
        return input_string[0].lower() + input_string[1:]

    @staticmethod
    def fetch_events(previousTitles: set) -> [EventInfo]:
        events: [EventInfo] = []
        eventTitles = previousTitles
        driver = webdriver.Chrome()
        driver.get('https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463')
        categoriesButton = driver.find_element(By.XPATH, "//button[contains(., 'Categories')]")
        categoriesButton.click()
        categories = driver.find_element(By.ID, "listbox-categories").find_elements(By.TAG_NAME, "li")
        categories = [(HumanitixScrapper.formatInput(category.text), category.text) for category in categories]
        for category, categoryName in categories:
            print("cat: ", category, " ", categoryName)
            page = 0
            while True:
                url = f'https://humanitix.com/nz/search?locationQuery=Wellington&lat=-41.2923814&lng=174.7787463&page={page}&categories={category}'
                driver.get(url)
                _ = WebDriverWait(driver, 10, poll_frequency=1).until(EC.presence_of_element_located((By.XPATH, f"//button[contains(., '{categoryName}')]")))
                height = driver.execute_script("return document.body.scrollHeight")
                scrolledAmount = 0
                while True:
                    if scrolledAmount > height:
                        break
                    driver.execute_script(f"window.scrollBy(0, {100});")

                    scrolledAmount += 100
                eventsData = driver.find_elements(By.CLASS_NAME, 'test')
                if not eventsData:
                    break
                for event in eventsData:
                    try:
                        venue = event.find_element(By.TAG_NAME, 'p')
                        divs = list(map(lambda x: x.text, event.find_elements(By.TAG_NAME, 'div')))
                        venue = venue.text
                        title = event.find_element(By.TAG_NAME, 'h6').text
                        if title in eventTitles:
                            continue
                        eventTitles.add(title)
                        imageURL = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                        eventUrl = event.get_attribute('href')
                        dates = HumanitixScrapper.get_date(divs, eventUrl)
                        events.append(EventInfo(name=title,
                                                dates=dates,
                                                image=imageURL,
                                                url=eventUrl,
                                                venue=venue,
                                                source="Humanitix",
                                                eventType=categoryName))
                    except Exception as e:
                        print(f"humanitix: {e}")
                        print("error: ", event.text)
                page += 1
        return events

# events = list(map(lambda x: x.to_dict(), sorted(HumanitixScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
