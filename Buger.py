from typing import List


class Burger:
    id: str
    name: str
    image: str
    description: str
    price: float
    beer_match_price: float
    meal_available: str
    beer_match: str
    venue: str
    coordinates: dict[str, float]
    sides_included: bool
    main_protein: str
    dietary_requirements: List[str]
    url: str

    def __init__(
            self: str,
            id: str,
            name: str,
            image: str,
            description: str,
            price: float,
            beer_match_price: float,
            meal_available: str,
            beer_match: str,
            venue: str,
            coordinates: dict[str, float],
            sides_included: bool,
            main_protein: str,
            dietary_requirements: List[str],
            url: str
    ):
        """
        :param id: the id
        :param name: burger name
        :param image: burger image
        :param description: burger description
        :param price: burger price
        :param beer_match_price: beer-match
        :param meal_available: lunch or dinner
        :param beer_match: beer-match price
        :param venue: the location
        :param coordinates: the coordinates
        :param dietary_requirements: list of requirements,
        :param url: the url
        :param sides_included: if it comes with fries
        :param main_protein: what is it made of
        """
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.price = price
        self.beer_match_price = beer_match_price
        self.meal_available = meal_available
        self.beer_match = beer_match
        self.venue = venue
        self.coordinates = coordinates
        self.dietary_requirements = dietary_requirements
        self.url = url
        self.main_protein = main_protein
        self.sides_included = sides_included

    def to_dict(self):
        """Convert the EventInfo object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "image": self.image,
            "description": self.description,
            "price": self.price,
            "beerMatchPrice": self.beer_match_price,
            "mealAvailable": self.meal_available,
            "beerMatch": self.beer_match,
            "venue": self.venue,
            "coordinates": self.coordinates,
            "dietaryRequirements": self.dietary_requirements,
            "mainProtein": self.main_protein,
            "sidesIncluded": self.sides_included,
            "url": self.url
        }

    @classmethod
    def from_dict(cls, data: dict):
        cls(
            id=data["id"],
            name=data["name"],
            image=data["image"],
            description=data["description"],
            price=data["price"],
            beer_match_price=data["beerMatchPrice"],
            meal_available=data["mealAvailable"],
            beer_match=data["beerMatch"],
            venue=data["venue"],
            coordinates=data["coordinates"],
            dietary_requirements=data["dietaryRequirements"],
            main_protein=data["mainProtein"],
            sides_included=data["sidesIncluded"],
            url=data["url"]
        )
