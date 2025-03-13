import requests
from bs4 import BeautifulSoup

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime


class TicketekScrapper:

    @staticmethod
    def fetch_events() -> [EventInfo]:
        eventsInfo: [EventInfo] = []
        page = 1
        while True:
            response = requests.get(
                f"https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington&page={page}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Find all divs with class 'deal_title'
                events = soup.find_all('div', class_='resultContainer')
                # Loop through each div and extract the title
                for event in events:
                    title = None
                    date = None
                    imageURL = None
                    url = None
                    venue = None
                    titleTag = event.find('h6')
                    if titleTag:
                        title = re.sub('\W+', ' ', titleTag.text).strip()
                    dateTag = event.find_all('div', class_='contentResultSummary')
                    if dateTag:
                        text = dateTag[0].text.strip()
                        textArray = text.split('\n')
                        if len(textArray) >= 2:
                            if re.search('\d+', textArray[1]):
                                date = re.sub('\W+', ' ', textArray[1])
                                venue = re.sub('\W+', ' ', textArray[0])
                            else:
                                date = re.sub('\W+', ' ', textArray[0])
                                venue = re.sub('\W+', ' ', textArray[1])
                        else:
                            date = "not listed"
                            venue = "not listed"
                    if date == None:
                        dateTag = event.find_all('div', class_='contentDate')
                        if dateTag:
                            date = dateTag[0].text.strip()
                        locationTag = event.find_all('div', class_='contentLocation')
                        if locationTag:
                            venue = locationTag[0].text.strip()
                    imageDivs = event.find_all('div', class_='contentImage')
                    if imageDivs:
                        a_tag = event.find('a')
                        imageTag = event.find('img')
                        if imageTag:
                            imageURL = imageTag.get('src')[2:]
                        if a_tag:
                            urlTag = a_tag.get('href')
                            if urlTag:
                                url = f"https://premier.ticketek.co.nz{urlTag}"

                    date = re.sub(':', ' ', date)
                    pattern = r"(\d{1,2} [A-Za-z]{3} \d{4}(?: \d{1,2} \d{2}[ap]m)?)"
                    dates = re.findall(pattern, date)
                    dateStamps = []
                    displayDate = None
                    for d in dates:
                        try:
                            date_obj = datetime.strptime(d, '%d %b %Y %I %M%p')
                        except:
                            date_obj = datetime.strptime(d, '%d %b %Y')
                        if displayDate == None:
                            displayDate = DateFormatting.formatDisplayDate(date_obj)
                        else:
                            displayDate += " to " + DateFormatting.formatDisplayDate(date_obj)
                        dateStamp = DateFormatting.formatDateStamp(date_obj)
                        if dateStamp not in dateStamps:
                            dateStamps.append(dateStamp)

                    eventsInfo.append(EventInfo(name=title,
                                                dates=dateStamps,
                                                displayDate=displayDate,
                                                image="https://" + imageURL,
                                                url=url,
                                                venue=venue,
                                                source="ticketek",
                                                eventType="Other"))
                tag = soup.find_all('div', class_='paginationResults')
                tag = re.sub('\W+', ' ', tag[0].text).strip().split(" of ")
                firstTag = tag[0].split(" ")[-1].strip()
                secondTag = tag[1].strip()
                if firstTag == secondTag:
                    break
                page += 1
            else:
                print(f"Failed to retrieve the page. Status code: {response.status_code}")
                break

        return eventsInfo


TicketekScrapper.fetch_events()
