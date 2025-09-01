from datetime import datetime

now = datetime.now()
CURRENT_FESTIVALS = []
CURRENT_FESTIVALS_DETAILS = []
if now.month == 8 or now.month == 7:
    CURRENT_FESTIVALS.append("BurgerWellington")
    CURRENT_FESTIVALS_DETAILS.append({
        "id": "BurgerWellington",
        "name": "Burger Wellington",
        "icon": "burger",
        "url": "https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/burgers.json"
    })
