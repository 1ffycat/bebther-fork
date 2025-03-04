"""
PLEASE FOLLOW THE DATA FORMAT

Data Format:
    Temperature
    Humidity
    WindSpeed
    Pressure
    UVIndex
    DayTemperature
    NightTemperature
    SunriseTime
    SunsetTime
"""


class Parser:
    """Basic parser object's structure.
    Used for reference"""

    name = "Base Parser"
    description = "this is an empty parser"
    URL = "https://lyceum.yandex.ru"

    def get_data(location_key="292712") -> dict:
        """Parse the data and return as a formatted dict"""
        pass

    def get_city(city_name="Irkutsk") -> str:
        """Get the city id from name"""
        pass
