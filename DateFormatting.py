from datetime import datetime, timedelta
import re
import pandas
import pytz

nz_tz = pytz.timezone("Pacific/Auckland")

class DateFormatting:
    @staticmethod
    def format_display_date(date: datetime) -> str:
        DateFormatting.replace_year(date)
        return date.strftime("%a %d %b")

    @staticmethod
    def replace_year(date: datetime) -> datetime:
        if date.year < datetime.today().year:
            return date.replace(year=datetime.today().year)
        return date

    @staticmethod
    def format_date_stamp(date: datetime) -> str:
        DateFormatting.replace_year(date)
        date = date.replace(microsecond=0, second=0)
        return date.strftime("%Y-%m-%d-%H:%M")

    @staticmethod
    def create_range(start_date: datetime, end_date: datetime) -> pandas.DatetimeIndex:
        try:
            hour = start_date.hour
            if start_date < datetime.now():
                start_date = datetime.now()
            start_date = start_date.replace(hour=hour)
            end_date = end_date.replace(hour=hour)
            return pandas.date_range(start_date, end_date)
        except:
            now = datetime.now(nz_tz)
            hour = start_date.hour
            if start_date < now:
                start_date = now
            start_date = start_date.replace(hour=hour)
            end_date = end_date.replace(hour=hour)
            pds = pandas.date_range(start_date, end_date, freq="D", tz='Pacific/Auckland')
            return pds

    @staticmethod
    def clean_up_date(dateString: str) -> str:
        return re.sub(r'(\d+)(ST|ND|RD|TH)', r'\1', dateString, flags=re.IGNORECASE)
