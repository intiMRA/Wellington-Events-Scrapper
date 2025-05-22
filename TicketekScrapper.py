import requests
from bs4 import BeautifulSoup
from EventInfo import EventInfo
import re
from dateutil import parser

class TicketekScrapper:
    @staticmethod
    def extractEvents(url: str, nationWide: bool, categoryName: str) -> [EventInfo]:
        events = []
        response = requests.get(url)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        htmlEvents = soup.find_all("div", attrs={"class": "event-item"})
        hasWellingtonTitle = any("- Wellington" in event.find("h6").text for event in htmlEvents)
        for htmlEvent in htmlEvents:
            try:
                title = htmlEvent.find("h6").text
                imageURL = htmlEvent.find("img").get("src")
                dateString, venue = htmlEvent.find("div", attrs={"class": "event-venue-dates"}).find_all("p")
                dateString = dateString.text
                dateString = re.findall(r"(\d{1,2}\s\w+\s\d{4}\s[pam0-9:]+)", dateString)[0]
                venue = venue.text
                date = parser.parse(dateString)
                title = re.sub(r"([\t\n\r])", "", title).strip()
                venue = re.sub(r"([\t\n\r])", "", venue).strip()
                if hasWellingtonTitle and "wellington" not in title.lower():
                    continue
                if nationWide and "wellington" not in title.lower() and "wellington" not in venue.lower():
                    continue
                events.append(EventInfo(name=title,
                                        dates=[date],
                                        image="https://" + imageURL,
                                        url=url,
                                        venue=venue,
                                        source="ticketek",
                                        eventType=categoryName))
            except Exception as e:
                print("tiket error: ", e)
        return events

    @staticmethod
    def fetch_events() -> [EventInfo]:
        eventsInfo: [EventInfo] = []
        response = requests.get(
            f"https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington")
        soup = BeautifulSoup(response.text, "html.parser")
        cats = soup.find_all('a', class_="cat-nav-item")
        cats = [(cat.text, cat.get("href").split("c=")[-1]) for cat in cats if len(cat.get("href").split("c=")) > 1]
        cats.append(("Other", "Other"))
        titles = set()
        for categoryName, categoryTag in cats:
            print(f"categoryName: {categoryName}, categoryTag: {categoryTag}")
            page = 1
            while True:
                response = requests.get(
                    f"https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington&page={page}&c={categoryTag}")
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    error = soup.find_all("p", class_="noResultsMessage")
                    if error:
                        break
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
                        if title in titles:
                            continue
                        titles.add(title)
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
                                parts = date.strip().split(' ')
                                parts1 = parts[0:6]
                                parts2 = parts[6:]
                                time1 = ":".join(parts1[-2:])
                                time2 = ":".join(parts2[-2:])
                                date = ' '.join(parts1[0:-2]) + ' ' + time1 + ' ' + ' '.join(parts2[0:-2]) + ' ' + time2
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

                        pattern = r"(\d{1,2}\s\w+\s\d{4})"
                        dates = re.findall(pattern, date)
                        times = re.findall(r"\d{1,2}[:]*\d{0,2}[amp]{2}", date)
                        dateObjects = []
                        if len(dates) > 1 or venue == "Nationwide" or not dates:
                            events = TicketekScrapper.extractEvents(url, venue == "Nationwide", categoryName)
                            eventsInfo += events
                            continue
                        if not times:
                            times = ["10am"]
                        date = dates[0] + " " + times[0]
                        date_obj = parser.parse(date)
                        if date_obj not in dateObjects:
                            dateObjects.append(date_obj)

                        title = re.sub(r"([\t\n\r])", "", title).strip()
                        venue = re.sub(r"([\t\n\r])", "", venue).strip()
                        try:
                            eventsInfo.append(EventInfo(name=title,
                                                        dates=dateObjects,
                                                        image="https://" + imageURL,
                                                        url=url,
                                                        venue=venue,
                                                        source="ticketek",
                                                        eventType=categoryName))
                        except Exception as e:
                            print(f"tiket: {e}")
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


# events = list(map(lambda x: x.to_dict(), sorted(TicketekScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)