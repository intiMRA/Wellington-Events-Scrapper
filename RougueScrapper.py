import requests
from bs4 import BeautifulSoup
from EventInfo import EventInfo
import re

class RougueScrapper:

    @staticmethod
    def fetch_events() -> [EventInfo]:
        eventsInfo: [EventInfo] = []
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

                dateTag = event.find_all('span', class_='lite')[0].text
                date = re.sub('\W+', ' ', dateTag).strip()
                venue = "Rogue And Vagabond"
                imageDivs = event.find_all('div', class_='gig-image')
                if imageDivs:
                    a_tag = event.find('a')
                    imageTag = event.find('img')
                    if imageTag:
                        imageURL = imageTag.get('src')
                    if a_tag:
                        url = a_tag.get('href')
                eventsInfo.append(EventInfo(name=title, date=date,image=imageURL, url=url, venue=venue))
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")


        return eventsInfo