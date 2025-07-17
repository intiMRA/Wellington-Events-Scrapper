from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from typing import Optional


class CoordinatesMapper:
    @staticmethod
    def get_coordinates(address: str) -> Optional[dict[str, str]]:
        geolocator = Nominatim(user_agent="wlleington_events")
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                return {"lat": location.latitude, "long": location.longitude}
            else:
                address = address.split(",")[-1]
                try:
                    location = geolocator.geocode(address, timeout=10)
                    if location:
                        return {"lat": location.latitude, "long": location.longitude}
                    else:
                        print(f"no location found for address: {address}")
                        return None
                except Exception as e:
                    print(f"An error occurred for {address}: {e}")
                    return None
        except Exception as e:
            print(f"An error occurred for {address}: {e}")
            return None
