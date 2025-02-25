from datetime import datetime
import re

class DateFormatting:
    @staticmethod
    def formatDisplayDate(date: datetime) -> str :
        return date.strftime("%a %d %b")

    @staticmethod
    def formatDateStamp(date: datetime) -> str :
        date = date.replace(year=datetime.today().year)
        return date.strftime("%d-%m-%Y")

    @staticmethod
    def cleanUpDate(dateString: str) -> str:
        return re.sub(r'(\d+)(ST|ND|RD|TH)', r'\1', dateString, flags=re.IGNORECASE)