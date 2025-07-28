import json
import os
import random
from datetime import datetime
from EventInfo import EventInfo
import pytz
import FileUtils
import ScrapperNames
from FacebookScrapper import FacebookScrapper
import re
import undetected_chromedriver as uc
from time import sleep

def is_facebook_url_expired_now(oe_hex):
    # Get current time in NZ
    nz_timezone = pytz.timezone('Pacific/Auckland')
    now_nz = datetime.now(nz_timezone)

    # Decode Facebook's OE timestamp (UTC)
    unix_time = int(oe_hex, 16)
    utc_expiry = datetime.fromtimestamp(unix_time, pytz.utc)

    # Convert expiry to NZ time
    nz_expiry = utc_expiry.astimezone(nz_timezone)

    # Compare
    return now_nz > nz_expiry

events = FileUtils.load_events()
path_profile = os.path.join(os.path.expanduser("~"), "SeleniumProfiles", "MyTestProfile")
options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-infobars")
options.add_argument("--start-maximized")
options.add_argument(f"--user-data-dir={path_profile}")
options.add_argument(
    f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 115)}.0.0.0 Safari/537.36")

# Initialize undetected ChromeDriver
driver = uc.Chrome(
    options=options,
    headless=False,  # Headless mode is more easily detected
    use_subprocess=True
)
files = FileUtils.get_files_for_scrapper(ScrapperNames.FACEBOOK)
banned_file = files[-1]
out_file = files[0]
new_events = []
fetch_events = []
for event in events:
    if not event.image or "oe=" not in event.image:
        new_events.append(event)
        continue
    match = re.findall(r"oe=[aA-zZ0-9]+", event.image)[0]
    if is_facebook_url_expired_now(match.split("=")[-1]):
        fetch_events.append(event)
    else:
        new_events.append(event)
total = len(fetch_events)
print(f"fetching: {total}")
event_count = 1
for event in fetch_events:
    print(f"{event_count} out of {total}")
    try:
        new_event = FacebookScrapper.get_event(event.url, event.eventType, driver, banned_file)
        new_events.append(new_event)
        json.dump(new_event.to_dict(), out_file, indent=2)
        out_file.write(",\n")
    except Exception as e:
        print(e)
    sleep(random.uniform(1, 5))
    event_count += 1
#
# new_events = []
# loaded_events = [EventInfo.from_dict(event) for event in FileUtils.load_from_files(ScrapperNames.FACEBOOK)[0]]
# for e in events:
#     found = False
#     for e2 in loaded_events:
#         if e2.url == e.url:
#             new_events.append(e2)
#             found = True
#             break
#     if not found:
#         new_events.append(e)
FileUtils.write_to_events_file(new_events)
