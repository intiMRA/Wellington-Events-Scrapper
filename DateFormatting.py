from datetime import datetime, timedelta
import re
import pandas
import pytz

nz_tz = pytz.timezone("Pacific/Auckland")

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
        return date.strftime("%Y-%m-%d-%H:%M")

    @staticmethod
    def createRange(startDate: datetime, endDate: datetime) -> pandas.DatetimeIndex:
        try:
            hour = startDate.hour
            if startDate < datetime.now():
                startDate = datetime.now()
            startDate = startDate.replace(hour=hour)
            endDate = endDate.replace(hour=hour)
            return pandas.date_range(startDate, endDate)
        except:
            now = datetime.now(nz_tz)
            hour = startDate.hour
            if startDate < now:
                startDate = now
            startDate = startDate.replace(hour=hour)
            endDate = endDate.replace(hour=hour)
            pds = pandas.date_range(startDate, endDate, freq="D", tz='Pacific/Auckland')
            return pds

    @staticmethod
    def cleanUpDate(dateString: str) -> str:
        return re.sub(r'(\d+)(ST|ND|RD|TH)', r'\1', dateString, flags=re.IGNORECASE)