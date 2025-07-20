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


sleep(5000)
