import math
import random
from typing import Optional, Set, List, Any
from Buger import Burger
from EventInfo import EventInfo
import requests
import json
from dateutil import parser
from datetime import datetime
from time import sleep
import re

class WoapScrapper:
    @staticmethod
    def make_request(batch: List[str]) -> tuple[dict[str, Any], float]:
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
                             }
                             _allListingsMeta(filter: $filter) {
                               count
                             }
                           }

                           fragment SessionNew on SessionNewRecord {
                             kickerberryId
                             start
                             end
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
                             mainProtein
                             __typename
                           }

                           fragment ListingListLevel on ListingRecord {
                             id
                             sidesIncluded
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
                             beerMatch
                             venue {
                               kickerberryId
                               slug
                               address1
                               suburb
                               name
                               coordinates {
                                 latitude
                                 longitude
                               }
                             }
                             sessionsNew {
                               ...SessionNew
                             }
                             link
                             ...DietaryRequirements
                             waitlistLink
                           }
                           """
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json(), response.status_code

    @staticmethod
    def get_events_from_batch(batch: List[str]) -> List[EventInfo]:
        events: List[EventInfo] = []
        response, code = WoapScrapper.make_request(batch)

        # You can check the response
        if code == 200:
            listings = response["data"]["allListings"]
            for listing in listings:
                title: str = listing["name"]
                image: str = listing["image"]
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
                venue_slug = venue_dict["slug"]
                kickerberry_id = listing["kickerberryId"]
                event_url = f"https://visawoap.com/venue/{venue_slug}/{kickerberry_id}"
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
            print(f"Error: {code}")
            print(response)
            return []

    @staticmethod
    def fetch_burgers():
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
                    {"listingType": {"eq": "burger"}, "OR": []}
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
        for i in range(0, len(ids)):
            if i != 0 and i % 20 == 0:
                batches.append(batch)
                batch = []
            batch.append(ids[i])
        if batch:
            batches.append(batch)
        burgers = []
        for batch in batches:
            response = WoapScrapper.make_request(batch)[0]
            for dict in response["data"]["allListings"]:
                dict_venue = dict["venue"]
                venue_name = dict_venue['name']
                venue_address = dict_venue['address1']
                venue_suburb = dict_venue['suburb']
                venue = f"{venue_name}, {venue_address}, {venue_suburb}"
                coordinates = {"lat": dict_venue["coordinates"]["latitude"],
                               "long": dict_venue["coordinates"]["longitude"]}
                lunch = dict["availableForLunch"]
                dinner = dict["availableForDinner"]
                meal_available = "Dinner"
                if lunch and dinner:
                    meal_available = "Lunch and Dinner"
                elif lunch:
                    meal_available = "Lunch"
                dietary_requirements = []
                dairy_free = dict["dairyFree"]
                dairy_free_possible = dict["dairyFreePossible"]
                vegetarian = dict["vegetarian"]
                vegetarian_possible = dict["vegetarianPossible"]
                vegan = dict["vegan"]
                vegan_possible = dict["veganPossible"]
                nut_free = dict["nutFree"]
                nut_free_possible = dict["nutFreePossible"]
                gluten_free = dict["glutenFree"]
                gluten_free_possible = dict["glutenFreePossible"]
                if dairy_free_possible or dairy_free:
                    dietary_requirements.append("Dairy Free Available")

                if vegan_possible or vegan:
                    dietary_requirements.append("Vegan Available")

                if vegetarian_possible or vegetarian:
                    dietary_requirements.append("Vegetarian Available")

                if nut_free_possible or nut_free:
                    dietary_requirements.append("Nut Free Available")

                if gluten_free_possible or gluten_free:
                    dietary_requirements.append("Gluten Free Available")

                kickerberry_id = dict["kickerberryId"]
                venue_slug = dict_venue["slug"]
                burger_url = f"https://visawoap.com/venue/{venue_slug}/{kickerberry_id}"

                burger = Burger(
                    id=dict["id"],
                    name=dict["name"],
                    description=dict["description"],
                    image=dict["image"],
                    beer_match=dict["beerMatch"],
                    coordinates=coordinates,
                    price=dict["price"],
                    venue=venue,
                    meal_available=meal_available,
                    beer_match_price=dict["beerMatchPrice"],
                    dietary_requirements=dietary_requirements,
                    url=burger_url,
                    sides_included=dict["sidesIncluded"],
                    main_protein=re.sub(r"\s*\(.*\)", "", dict["mainProtein"])
                )
                burgers.append(burger)
        dietary_requirements_filters = set()
        beer_match = set()
        proteins = set()
        price_range = {"min": math.inf, "max": 0}
        burger_dicts = []
        for burger in burgers:
            for requirement in burger.dietary_requirements:
                dietary_requirements_filters.add(requirement)
            beer_match.add(burger.beer_match)
            price_range["min"] = min(price_range["min"], burger.price)
            price_range["max"] = max(price_range["max"], burger.price)
            for protein in burger.main_protein.split(","):
                proteins.add(protein.strip())
            burger_dicts.append(burger.to_dict())
        sleep(random.uniform(1, 3))
        burgers_json = {
            "burgers": burger_dicts,
            "filters": {
                "dietaryRequirements": list(dietary_requirements_filters),
                "priceRange": price_range,
                "beerMatch": list(beer_match),
                "proteins": list(proteins)
            }
        }
        with open("burgersCopy.json", mode="w") as cpy:
            with open("burgers.json", mode="r") as f:
                cpy.write(f.read())

        with open("burgers.json", mode="w") as f:
            json.dump(burgers_json, f, indent=2)

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
        for i in range(0, len(ids)):
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
        WoapScrapper.fetch_burgers()
        return events


# events = WoapScrapper.fetch_events(set(), set())
# WoapScrapper.fetch_burgers()
