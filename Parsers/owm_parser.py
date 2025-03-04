"""Data parser for OpenWeatherMap"""

import datetime
import json

import requests

from main import debug


class Parser:
    """Basic parser object's structure.
    Used for reference"""

    name = "OpenWeatherMap"
    description = "60 calls a minute"
    URL = "https://openweathermap.org/"
    apikey = "c000d489291afdc8c6b578c2c79d2e5f"

    def get_data(location_key="292712") -> dict:
        """Parse the data and return as a formatted dict"""
        result = dict()
        # Sending request to get lon & lat
        rlk = requests.get(
            url="https://api.openweathermap.org/data/2.5/weather?"
            + f"q={location_key}&appid={Parser.apikey}&units=metric"
        )
        if rlk.status_code != 200:
            debug("Couldn't get OWM data, SC != 200")
            return None
        # Parsing JSON data format for lon/lat
        rlk = json.loads(rlk.content)["coord"]
        # Sending request to get weather info
        response = requests.get(
            url="https://api.openweathermap.org/data/2.5/onecall?"
            + f"lat={rlk['lat']}&lon={rlk['lon']}&appid={Parser.apikey}"
            + "&units=metric"
        )
        if response.status_code != 200:
            debug("Couldn't get OWM2 data, SC != 200")
        # Parsing JSON data format for weather
        response = json.loads(response.content)["current"]
        # Filling in the dictionary
        result["Temperature"] = round(float(response["temp"]), 1)
        result["Humidity"] = response["humidity"]
        result["WindSpeed"] = response["wind_speed"]
        result["Pressure"] = response["pressure"]
        result["UVIndex"] = response["uvi"]
        result["SunriseTime"] = (
            datetime.datetime.fromtimestamp(int(response["sunrise"]))
            .time()
            .strftime("%H:%M")
        )
        result["SunsetTime"] = (
            datetime.datetime.fromtimestamp(int(response["sunset"]))
            .time()
            .strftime("%H:%M")
        )
        # Sending request to get day/night temperatures
        response = requests.get(
            url="https://api.openweathermap.org/data/2.5/forecast?"
            + f"q={location_key}&appid={Parser.apikey}&units=metric"
        )
        if response.status_code != 200:
            debug("Couldn't get OWM3 data, SC != 200")
        # Parsing JSON data format for day/night temperatures
        response = json.loads(response.content)["list"][0]["main"]
        result["DayTemperature"] = round(float(response["temp_max"]), 1)
        result["NightTemperature"] = round(float(response["temp_min"]), 1)
        return result

    def get_city(city_name="Irkutsk") -> str:
        """Get the city id from name"""
        # OWM doesn't need any ID, only city name is needed
        return city_name
