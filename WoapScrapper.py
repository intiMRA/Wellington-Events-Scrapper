import random
from typing import Optional, Set, List

from EventInfo import EventInfo
import requests
import json
from dateutil import parser
from datetime import datetime
from time import sleep
class WoapScrapper:
    @staticmethod
    def get_events_from_batch(batch: List[str]) -> List[EventInfo]:
        events: List[EventInfo] = []
        url = 'https://graphql.datocms.com/'
        headers = {
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'authorization': 'Bearer 6d1e8dce63e951295b5ec7f7aac0be',
            'content-type': 'application/json',
            'origin': 'https://visawoap.com',
            'priority': 'u=1, i',
            'referer': 'https://visawoap.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-environment': 'main'
        }

        data = {
            "operationName": "AllListings",
            "variables": {
                "skip": 0,
                "sort": None,
                "filter": {
                    "id": {
                        "in": batch
                    }
                }
            },
            "query": """
                    query AllListings($skip: IntType = 0, $filter: ListingModelFilter, $sort: [ListingModelOrderBy] = name_ASC) {
                      allListings(skip: $skip, filter: $filter, orderBy: $sort) {
                        ...ListingListLevel
                        __typename
                      }
                      _allListingsMeta(filter: $filter) {
                        count
                        __typename
                      }
                    }

                    fragment SessionNew on SessionNewRecord {
                      kickerberryId
                      sessionType
                      cost
                      tickets
                      start
                      end
                      __typename
                    }

                    fragment DietaryRequirements on ListingRecord {
                      dairyFree
                      dairyFreePossible
                      vegetarian
                      vegetarianPossible
                      vegan
                      veganPossible
                      nutFree
                      nutFreePossible
                      glutenFree
                      glutenFreePossible
                      __typename
                    }

                    fragment ListingListLevel on ListingRecord {
                      id
                      listingType
                      kickerberryId
                      name
                      image
                      description
                      price
                      lowestPrice
                      highestPrice
                      beerMatchPrice
                      availableForLunch
                      availableForDinner
                      hasDelivery
                      delivereasyLink
                      beerMatch
                      ticketButtonText
                      venue {
                        id
                        kickerberryId
                        slug
                        address1
                        address2
                        suburb
                        name
                        coordinates {
                          latitude
                          longitude
                          __typename
                        }
                        __typename
                      }
                      sessionsNew {
                        ...SessionNew
                        __typename
                      }
                      link
                      ...DietaryRequirements
                      soldOut
                      sellingFast
                      waitlistLink
                      __typename
                    }
                    """
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        # You can check the response
        if response.status_code == 200:
            listings = response.json()["data"]["allListings"]
            for listing in listings:
                title: str = listing["name"]
                image: str = listing["image"]
                listingType: str = listing["listingType"]
                description: str = listing["description"]
                venue_dict = listing["venue"]
                address: str = venue_dict["address1"]
                venue_name = venue_dict["name"]
                venue: str = f"{venue_name}, {address}"
                venue_coordinates = venue_dict["coordinates"]
                coordinates = None
                if venue_coordinates:
                    coordinates = {
                        "lat": float(venue_coordinates["latitude"]),
                        "long": float(venue_coordinates["longitude"])
                    }

                sessions: List[dict[str, str]] = listing["sessionsNew"]
                dates: List[datetime] = []
                for session in sessions:
                    start = session["start"]
                    date: datetime = parser.parse(start)
                    dates.append(parser.parse(date.strftime("%Y-%m-%d %H:%M")))
                event_url = listing["link"]
                wait_list_url = listing["waitlistLink"]
                if not event_url:
                    event_url = wait_list_url
                if not event_url:
                    venue_slug = venue_dict["slug"]
                    kickerberryId = listing["kickerberryId"]
                    event_url = f"https://visawoap.com/venue/{venue_slug}/{kickerberryId}"
                print(f"title: {title} url: {event_url}")
                try:
                    event = EventInfo(name=title,
                                      image=image,
                                      venue=venue,
                                      dates=dates,
                                      url=event_url,
                                      source="WOAP",
                                      event_type="Food & Drink",
                                      description=description,
                                      coordinates=coordinates)
                    events.append(event)
                except Exception as e:
                    print(e)
                print("-" * 100)
            return events
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return []
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        filters_url = 'https://visawoap.com/api/search'

        headers = {
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'baggage': 'sentry-environment=vercel-production,sentry-release=1f2f56039bf37684942469927923241d14731493,sentry-public_key=5e7a72c26cb3c4dbc1327375d02401fb,sentry-trace_id=46b4c963cc774abb8773ff64776c1c92,sentry-sample_rate=1,sentry-sampled=true',
            'content-type': 'application/json',
            'origin': 'https://visawoap.com',
            'priority': 'u=1, i',
            'referer': 'https://visawoap.com/explore',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sentry-trace': '46b4c963cc774abb8773ff64776c1c92-b1942d046695663d-1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        data = {
            "filters": {
                "OR": [
                    {"listingType": {"eq": "event"}, "OR": []}
                ],
                "AND": []
            },
            "keyword": "",
            "sort": None
        }

        filter_response = requests.post(filters_url, headers=headers, data=json.dumps(data)).json()
        ids = filter_response["ids"]
        batches = []
        batch = []
        for i in range(0,len(ids)):
            if i != 0 and i % 20 == 0:
                batches.append(batch)
                batch = []
            batch.append(ids[i])
        if batch:
            batches.append(batch)
        events: List[EventInfo] = []
        for batch in batches:
            events += WoapScrapper.get_events_from_batch(batch)
            sleep(random.uniform(1, 3))
        return events
# events = WoapScrapper.fetch_events(set(), set())