from geopy.geocoders import Nominatim
from typing import Optional
import re


class CoordinatesMapper:
    @staticmethod
    def get_coordinates(address: str) -> Optional[dict[str, str]]:
        clean_ups = [
            " - Mana"
        ]
        regexes = [
            r"(\d+\s*st|\d+\s*th)\s*[fF]{1}loor",
            r"(\d+\s*st|\d+\s*th)\s*[Ll]{1}evel",
            r"#?[Ll](?:evel)?\s?(\d+)|\s*#(\d+)"
        ]
        geolocator = Nominatim(user_agent="wellington_events")
        for clean_up in clean_ups:
            address = re.sub(fr"{clean_up}", "", address)
        for regex in regexes:
            address = re.sub(regex, "", address)
        variations = [address]

        first_part = ",".join(address.split(",")[1:]).strip()
        if first_part:
            variations.append(first_part)
            wellington_first_part = first_part + ", Wellington, New Zealand"
            variations.append(wellington_first_part)
        wellington_first_full = address + ", Wellington, New Zealand"
        variations.append(wellington_first_full)
        last_part = ",".join(address.split(",")[0:-2]).strip()
        if last_part:
            variations.append(last_part)
        if len(address.split(",")) > 1 and not re.findall(r"\d+", address):
            new_variations = []
            for variation in variations:
                new_variations.append(variation)
                new_variations.append(f"1 {variation}")
            variations = new_variations
        location = None
        for variation in variations:
            print(f"address variation {variation}")
            try:
                try_location = geolocator.geocode(variation, timeout=10)
                if try_location:
                    location = try_location
                    break
            except Exception as e:
                print(f"An error occurred for {address}: {e}")
                return None
        if location:
            return {"lat": location.latitude, "long": location.longitude}
        else:
            print(f"no location found for address: {address}")
            return None
