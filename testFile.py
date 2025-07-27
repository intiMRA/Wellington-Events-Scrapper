import random
from datetime import datetime
import pytz
import FileUtils
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
driver = uc.Chrome()
banned_file = open("lol.json", mode="w")
for event in events:
    if not event.image or "oe=" not in event.image:
        continue
    match = re.findall(r"oe=[aA-zZ0-9]+", event.image)[0]
    if is_facebook_url_expired_now(match.split("=")[-1]):
        new_event = FacebookScrapper.get_event(event.url, "", driver, banned_file)
        event.image = new_event.image
        sleep(random.uniform(1, 5))
