from datetime import datetime, timedelta
import re
import pandas
import pytz
from dateutil import parser

class DateFormatting:
    @staticmethod
    def formatDisplayDate(date: datetime) -> str :
        DateFormatting.replaceYear(date)
        return date.strftime("%a %d %b")
    
    @staticmethod
    def replaceYear(date: datetime) -> datetime :
        if date.year < datetime.today().year:
            return date.replace(year=datetime.today().year)
        return date

    @staticmethod
    def formatDateStamp(date: datetime) -> str :
        DateFormatting.replaceYear(date)
        date = date.replace(microsecond=0, second=0)
        parts = date.isoformat().split("+")
        date = parts[0]
        return date if "Z" in date else date + "Z"

    @staticmethod
    def createRange(startDate: datetime, endDate: datetime) -> pandas.DatetimeIndex:
        try:
            if startDate < datetime.now():
                startDate = datetime.now()
            return pandas.date_range(startDate, endDate - timedelta(days=1))
        except:
            now = datetime.now().isoformat().split("T")[0] + "T" + startDate.isoformat().split("T")[1]
            now = parser.parse(now)
            if startDate < now:
                startDate = now
            pds = pandas.date_range(startDate, endDate - timedelta(days=1))
            return pds

    @staticmethod
    def cleanUpDate(dateString: str) -> str:
        return re.sub(r'(\d+)(ST|ND|RD|TH)', r'\1', dateString, flags=re.IGNORECASE)