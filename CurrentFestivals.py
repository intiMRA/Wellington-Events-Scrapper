from datetime import datetime

now = datetime.now()
CURRENT_FESTIVALS = []
if now.month == 8 or now.month == 7:
    CURRENT_FESTIVALS.append("BurgerWellington")
