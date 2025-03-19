from datetime import datetime, timedelta
import re
import pandas

class DateFormatting:
    @staticmethod
    def formatDisplayDate(date: datetime) -> str :
        date = date.replace(year=datetime.today().year)
        return date.strftime("%a %d %b")

    @staticmethod
    def formatDateStamp(date: datetime) -> str :
        date = date.replace(year=datetime.today().year)
        return date.strftime("%d-%m-%Y")

    @staticmethod
    def createRange(startDate: datetime, endDate: datetime) -> pandas.DatetimeIndex:
        if startDate < datetime.now():
            startDate = datetime.now()
        return pandas.date_range(startDate, endDate - timedelta(days=1))

    @staticmethod
    def cleanUpDate(dateString: str) -> str:
        return re.sub(r'(\d+)(ST|ND|RD|TH)', r'\1', dateString, flags=re.IGNORECASE)