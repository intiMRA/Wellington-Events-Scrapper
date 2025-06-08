import requests
from bs4 import BeautifulSoup

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from dateutil import parser
from typing import  List, Set

class RougueScrapper:

    @staticmethod
    def fetch_events(previousTitltes: Set[str]) -> List[EventInfo]:
        eventsInfo: List[EventInfo] = []
        response = requests.get(f"https://rogueandvagabond.co.nz/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Find all divs with class 'deal_title'
            events = soup.find_all('div', class_='vevent')
            # Loop through each div and extract the title
            for event in events:
                imageURL = None
                url = None
                titleDiv = event.find_all('div', class_='gig-title')[0]
                titleTag = titleDiv.find('a')
                title = titleTag.get_text()
                if title in previousTitltes:
                    continue

                dateTag = event.find_all('span', class_='lite')[0].text
                dateString = re.sub('\W+', ' ', dateTag).strip()
                venue = "Rogue And Vagabond"
                imageDivs = event.find_all('div', class_='gig-image')
                if imageDivs:
                    a_tag = event.find('a')
                    imageTag = event.find('img')
                    if imageTag:
                        imageURL = imageTag.get('src')
                    if a_tag:
                        url = a_tag.get('href')

                dateString = DateFormatting.cleanUpDate(dateString)
                match = re.findall(r"(\d{1,2}\s\w+\s\d{1,2}\s[pam0-9]{4})", dateString)[0]
                parts = match.split(" ")
                time = ":".join(parts[-2:])
                match = " ".join(parts[:-2]) + " " + time
                date = parser.parse(match)
                date = DateFormatting.replaceYear(date)
                try:
                    eventsInfo.append(EventInfo(name=title,
                                                dates=[date],
                                                image=imageURL,
                                                url=url,
                                                venue=venue,
                                                source="Rogue & Vagabond",
                                                eventType="Music"))
                except Exception as e:
                    print(f"rogue: {e}")
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")

        return eventsInfo

# events = list(map(lambda x: x.to_dict(), sorted(RougueScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)