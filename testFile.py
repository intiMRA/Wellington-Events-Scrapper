from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from time import sleep
from EventInfo import EventInfo
import re

url = "https://www.facebook.com/events/1964233224348051"

profile_path = "~/ChromeTestProfile"  # Replace with your actual path

options = Options()
options.add_argument(f"user-data-dir={profile_path}")

driver = webdriver.Chrome(options=options)
driver.get(url)
sleep(1)
info = driver.find_element(By.XPATH, "//div[@aria-label='Event permalink']")
spans = info.find_elements(By.TAG_NAME, "span")
texts = []
invite_text = "Invite"
for span in spans:
    text = span.text
    if text in texts:
        continue
    texts.append(text)
for text in texts:
    print(text)
    print("-" * 100)

button = info.find_element(By.XPATH, '//div[@role="button" and text()="See more"]')
button.click()
sleep(1)
long_desc: str = info.find_element(By.XPATH, "//span[contains(., 'See less')]").text

if "..." in long_desc:
    long_desc = "\n".join(long_desc.split("\n")[0:-2])
else:
    long_desc = re.sub(r"See less", "", long_desc)
print(long_desc)
address = info.find_element(By.XPATH, "//div[@aria-label='Location information for this event']")
venue = address.text.split("\n")[-1]
image_url = driver.find_element(By.XPATH, "//img[@data-imgperflogname='profileCoverPhoto']").get_attribute("src")
dates = texts[0]
title = texts[1]
event = EventInfo(name=title,
                  image=image_url,
                  venue=venue,
                  dates=[],
                  url="",
                  source="",
                  event_type="",
                  description=long_desc)

sleep(5000)
