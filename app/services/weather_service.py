import requests


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(destination: str):

    geo = requests.get(
        GEOCODE_URL,
        params={
            "name": destination,
            "count": 1
        },
        timeout=10
    )

    geo.raise_for_status()

    geo_data = geo.json()

    if not geo_data.get("results"):
        return {
            "error": f"Could not find {destination}"
        }

    place = geo_data["results"][0]

    weather = requests.get(
        WEATHER_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,weather_code"
        },
        timeout=10
    )

    weather.raise_for_status()

    current = weather.json()["current"]

    return {

        "destination": destination,

        "country": place.get("country"),

        "temperature": current["temperature_2m"],

        "weather_code": current["weather_code"]

    }