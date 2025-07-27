from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from datetime import datetime
from selenium.webdriver.common.by import By
from FacebookScrapper import FacebookScrapper

profile_path = "~/ChromeTestProfile"  # Replace with your actual path
# Set Chrome options
options = Options()
options.add_argument(f"user-data-dir={profile_path}")

# Initialize the ChromeDriver
driver = webdriver.Chrome(options=options)
start_date = datetime.now()
start_date_string = start_date.strftime("%Y-%m-%d")
start_date_string += "T05%3A00%3A00.000Z"
end_date = start_date + relativedelta(days=30)
end_date_string = end_date.strftime("%Y-%m-%d")
end_date_string += "T05%3A00%3A00.000Z"

driver.get(
    f"https://www.facebook.com/events/?"
    f"date_filter_option=CUSTOM_DATE_RANGE"
    f"&discover_tab=CUSTOM"
    f"&location_id=1590021457900572"
    f"&start_date={start_date_string}"
    f"&end_date={end_date_string}")
html = driver.find_elements(By.TAG_NAME, 'a')

for h in html:
    print(h.text)
    t = h.text.split("\n")[0]
    print(FacebookScrapper.parse_date(t))

sleep(5000)
