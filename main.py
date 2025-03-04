"""Main behavior"""

import asyncio
import datetime
import json
import os
import pathlib
import sys
from os import walk

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QComboBox, QMainWindow

import Modules.database as database
import Modules.dialogs as dialogs
import Modules.images as images

IS_DEBUG = True  # Controls some behavior such as debug-outputs
CURRENT_PARSER = None  # Contains instance of the selected Parser object
parsers = list()  # List of all available parsers
# Location of this file
directory = pathlib.Path(__file__).parent.resolve()
# Default theme
IS_DARK_THEME = True
# Autorun
IS_AUTORUN = False
# Current city string
CURRENT_CITY = "London"
# Default city stored in settings
DEFAULT_CITY = "London"
# Last parsed data
LAST_DATA = None


def debug(value) -> None:
    """Modified print method. Prints value if the debug mode is enabled"""
    if IS_DEBUG:
        if isinstance(value, list) or isinstance(value, dict):
            print(f"[DEBUG | {datetime.datetime.now()}]: ", end="")
            print(*value)
        else:
            print(f"[DEBUG | {datetime.datetime.now()}]: {value}")


class Windows(QMainWindow):
    """Windows functionality"""

    def __init__(self) -> None:
        """UI Initialization"""
        super().__init__()
        # Connecting and initializing the database
        database.start()
        # Initial setup
        self.read_settings()
        global CURRENT_CITY
        CURRENT_CITY = DEFAULT_CITY
        global CURRENT_PARSER
        if len(parsers) > 0:
            CURRENT_PARSER = parsers[0]
        # Opening main window
        self.init_main()
        self.update_parsers()

    def update_city_name(self) -> None:
        """Update backend cityName variable from UI"""
        global CURRENT_CITY
        CURRENT_CITY = self.cityNameField.toPlainText()

    def toggle_parser(self, index) -> None:
        """Switching to the next available parser"""
        global parsers, CURRENT_PARSER
        CURRENT_PARSER = parsers[index]
        self.update_data()

    def read_settings(self) -> None:
        """Read settings from the JSON file"""
        try:
            # Opening the file and parsing JSON
            os.chdir(f"{directory}\\")
            data = json.loads(open(f"{directory}\\settings.json", "r").readline())
            global DEFAULT_CITY, IS_DARK_THEME, IS_AUTORUN
            # Applying to variables
            DEFAULT_CITY = data["defaultCity"]
            IS_DARK_THEME = data["isDarkTheme"]
            IS_AUTORUN = data["isAutorun"]
            print(data["defaultCity"])
        except Exception as e:
            debug(f"Couldn't load settings: {e}")

    async def write_settings(self) -> None:
        """Save settings to the JSON file"""
        try:
            global DEFAULT_CITY, IS_DARK_THEME, IS_AUTORUN
            sfile = open("settings.json", "w")
            settings = dict()
            # Filling in the dictionary
            settings["defaultCity"] = DEFAULT_CITY
            settings["isDarkTheme"] = IS_DARK_THEME
            settings["isAutorun"] = IS_AUTORUN
            # Writing the dumped JSON data to file
            sfile.write(json.dumps(settings))
        except Exception as e:
            debug(f"Couldn't save settings: {e}")

    def update_parsers(self) -> None:
        """Updating list of available parsers"""
        files = []
        # Getting all files present in the ./Parsers/ folder
        for dirpath, dirname, filenames in walk(f"{directory}/Parsers/"):
            files.append(filenames)
            break
        debug(files)
        filenames.remove("baseParser.py")
        result = []
        # Importing the modules from files
        for i in filenames:
            if i.endswith("Parser.py"):
                result.append(
                    getattr(
                        __import__(
                            f"Parsers.{i.replace('.py', '')}", fromlist=["Parser"]
                        ),
                        "Parser",
                    )
                )
            else:
                filenames.remove(i)
        global parsers
        parsers = result
        self.update_parsers_ui()

    def update_parsers_ui(self) -> None:
        """Updating QComboBox items in UI, adding parsers to select"""
        global parsers
        self.parserBox.clear()
        for i in parsers:
            self.parserBox.addItem(i.name)

    def update_one_parser_ui(self, box: QComboBox) -> None:
        """Updating given QComboBox, adding parsers to select"""
        global parsers
        box.clear()
        for i in parsers:
            box.addItem(i.name)

    def get_data(self) -> dict:
        """Get data from current parser"""
        global CURRENT_PARSER, LAST_DATA
        if CURRENT_PARSER is None:
            return None
        # Getting the parsed data
        data = CURRENT_PARSER.getData(CURRENT_PARSER.getCity(CURRENT_CITY))
        debug(data if data is not None else "NO WEATHER")
        LAST_DATA = data
        if data is None:
            dialogs.NoDataDialog().exec()
        return data

    def update_ui(self, data: dict[str, str]) -> None:
        """Updating weather data"""
        if data is None:
            return None
        # Filling parsed data into UI labels
        self.l_temp.setText(
            f"{'+' if data['Temperature'] > 0 else ''}" + f"{data['Temperature']}°"
        )
        self.l_humidity.setText(f"{data['Humidity']}%")
        self.l_wind_speed.setText(f"{data['WindSpeed']} m/s")
        self.l_pressure.setText(f"{data['Pressure']}")
        self.l_uv_index.setText(f"{data['UVIndex']}")
        self.l_day_temp.setText(
            f"{'+' if data['DayTemperature'] > 0 else ''}"
            + f"{data['DayTemperature']}°"
        )
        self.label_3.setText(datetime.datetime.now().time().strftime("%H:%M"))
        self.l_night_temp.setText(
            f"{'+' if data['NightTemperature'] > 0 else ''}"
            + f"{data['NightTemperature']}°"
        )
        self.l_sunrise.setText(f"{data['SunriseTime']}")
        self.l_sunset.setText(f"{data['SunsetTime']}")

    def update_data(self) -> None:
        """Updates data and UI values"""
        data = self.get_data()
        if data is not None:
            self.update_ui(data)
        else:
            debug("Error, no data.")

    def push_to_database(self) -> None:
        """Writes current weather data to the database."""
        global LAST_DATA, CURRENT_CITY, CURRENT_PARSER
        if LAST_DATA is None:
            debug("last_data was None, couldn't write to the db")
            dialogs.DBFailDialog().exec()
            return
        # Formatting dict for database entry
        data = LAST_DATA
        data["Date"] = datetime.datetime.now().date()
        data["City"] = CURRENT_CITY
        data["WeatherSource"] = CURRENT_PARSER.name
        if database.db is None:
            debug("WRITE: database does not exist")
            dialogs.DBFailDialog().exec()
            return
        try:
            database.write(LAST_DATA)
            dialogs.DBSavedDialog().exec()
        except Exception as e:
            debug(f"Couldn't write to the database: {e}")
            dialogs.DBFailDialog().exec()

    def get_ui_file(self, name: str) -> str:
        """Returns UI file path depending on color scheme"""
        global directory, IS_DARK_THEME
        bs = "\\"
        return (
            f"{directory}\\ui\\" + f"{'dark' if IS_DARK_THEME else 'light'}\\{name}.ui"
        )

    # Main window
    def init_main(self) -> None:
        """Loads gui of main window,
        defines functions and connects buttons to thems"""
        uic.loadUi(self.get_ui_file("main"), self)
        global LAST_DATA
        self.update_parsers_ui()  # Updating parsers list in UI
        self.parserBox.currentIndexChanged.connect(self.toggle_parser)
        self.update_ui(LAST_DATA)  # Updating UI

        def share() -> None:
            """Opens picture with info about weather"""
            global LAST_DATA, IS_DARK_THEME
            if LAST_DATA is None:
                dialogs.ShareFailDialog().exec()
                return
            images.Worker.output_image(LAST_DATA, IS_DARK_THEME)

        def buttons() -> None:
            """Connects buttons to functions"""
            self.cityNameField.setPlainText(CURRENT_CITY)
            self.cityNameField.textChanged.connect(self.update_city_name)
            self.setting_button.clicked.connect(self.init_settings)
            self.reload_button.clicked.connect(self.update_data)
            self.setting_button.clicked.connect(self.init_settings)
            self.compare_days_button.clicked.connect(self.init_compare_days)
            self.compare_sources_button.clicked.connect(self.init_compare_sources)
            self.save_button.clicked.connect(self.push_to_database)
            self.share_button.clicked.connect(share)
            self.update_parser_button.clicked.connect(self.update_parsers)

        buttons()

    def change_hometown(self) -> None:
        """Changes local entry of default city and save settings"""
        global DEFAULT_CITY
        DEFAULT_CITY = self.hometownField.toPlainText()

    def transit_to_main(self) -> None:
        """Transition method from settings to main window"""
        # Running settings save operarion async so it won't freeze the UI
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.write_settings())
        self.init_main()

    # Settings window
    def init_settings(self) -> None:
        """Loads gui of settings window,
        defines functions and connects buttons to them"""
        uic.loadUi(self.get_ui_file("settings"), self)

        def change_theme() -> None:
            """Changes theme"""

            def light() -> None:
                """Switches theme to light"""
                global IS_DARK_THEME
                IS_DARK_THEME = False
                # Reloads current window
                uic.loadUi(self.get_ui_file("settings"), self)

            def dark() -> None:
                """Switches theme to dark"""
                global IS_DARK_THEME
                IS_DARK_THEME = True
                # Reloads current window
                uic.loadUi(self.get_ui_file("Settings"), self)

            light() if self.theme_light.isChecked() else dark()
            buttons()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.write_settings())

        def autorun() -> None:
            def on() -> None:
                """Turns autorun on"""
                global IS_AUTORUN
                import winreg

                keyVal = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
                # Connecting to the registry
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)

                # Writing to the registry key or creating a new one
                try:
                    key = winreg.OpenKey(registry, keyVal, 0, winreg.KEY_ALL_ACCESS)
                except OSError:
                    key = winreg.CreateKey(winreg.registry, keyVal)

                # Setting key value
                winreg.SetValueEx(
                    key, "Bebther", 0, winreg.REG_SZ, f"{directory}\\run.bat"
                )
                # Closing the registry
                winreg.CloseKey(key)
                IS_AUTORUN = True

            def off() -> None:
                """Turns autorun off"""
                global IS_AUTORUN
                import winreg

                # Connecting to the registry
                keyVal = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)

                # Removing the registry key
                try:
                    key = winreg.OpenKey(registry, keyVal, 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteValue(key, "Bebther")
                    winreg.CloseKey(key)
                    IS_AUTORUN = False
                except OSError:
                    pass

            on() if self.autorun_on.isChecked() else off()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.write_settings())

        def buttons() -> None:
            """Connects buttons to functions"""
            # Main menu button
            self.main_button.clicked.connect(self.transit_to_main)

            # Theme buttons
            self.hometownField.textChanged.connect(self.change_hometown)
            global DEFAULT_CITY, IS_DARK_THEME
            self.hometownField.setPlainText(DEFAULT_CITY)
            self.theme_light.clicked.connect(change_theme)
            self.theme_dark.clicked.connect(change_theme)
            self.theme_light.setChecked(True if not IS_DARK_THEME else False)
            self.theme_dark.setChecked(True if IS_DARK_THEME else False)

            # Autorun buttons
            self.autorun_on.clicked.connect(autorun)
            self.autorun_off.clicked.connect(autorun)
            self.autorun_on.setChecked(IS_AUTORUN)
            self.autorun_off.setChecked(False if IS_AUTORUN else True)

        buttons()

    def init_compare_days(self) -> None:
        """Initialize the day comparison UI"""
        uic.loadUi(self.get_ui_file("compare_days"), self)

        self.main_button.clicked.connect(self.init_main)

        def fill_data() -> None:
            """Fill the weather data into UI labels"""

            def today() -> None:
                """Fill today's weather data into UI labels"""
                global LAST_DATA
                data = LAST_DATA
                if data is None:
                    return False
                # Filling parsed data into UI labels
                self.l_humidity_3.setText(f"{data['Humidity']}%")
                self.l_wind_speed_3.setText(f"{data['WindSpeed']} m/s")
                self.l_pressure_3.setText(f"{data['Pressure']}")
                self.l_uv_index_3.setText(f"{data['UVIndex']}")
                self.l_day_temp_3.setText(
                    f"{'+' if data['DayTemperature'] > 0 else ''}"
                    + f"{data['DayTemperature']}°"
                )
                self.l_night_temp_3.setText(
                    f"{'+' if data['NightTemperature'] > 0 else ''}"
                    + f"{data['NightTemperature']}°"
                )
                self.l_sunrise_3.setText(f"{data['SunriseTime']}")
                self.l_sunset_3.setText(f"{data['SunsetTime']}")

            def yesterday() -> None:
                """Fill yesterday's weather data into UI labels"""
                global LAST_DATA
                date = datetime.date.today()
                date = date - datetime.timedelta(days=1)
                data = database.read(date)
                if data is None:
                    return False
                # Filling parsed data into UI labels
                self.l_humidity_2.setText(f"{data['Humidity']}%")
                self.l_wind_speed_2.setText(f"{data['WindSpeed']} m/s")
                self.l_pressure_2.setText(f"{data['Pressure']}")
                self.l_uv_index_2.setText(f"{data['UVIndex']}")
                self.l_day_temp_2.setText(
                    f"{'+' if data['DayTemperature'] > 0 else ''}"
                    + f"{data['DayTemperature']}°"
                )
                self.l_night_temp_2.setText(
                    f"{'+' if data['NightTemperature'] > 0 else ''}"
                    + f"{data['NightTemperature']}°"
                )
                self.l_sunrise_2.setText(f"{data['SunriseTime']}")
                self.l_sunset_2.setText(f"{data['SunsetTime']}")

            def tda() -> None:
                """Fill two-days-ago's weather data into UI labels"""
                global LAST_DATA
                date = datetime.date.today()
                date = date - datetime.timedelta(days=2)
                data = database.read(date)
                if data is None:
                    return False
                # Filling parsed data into UI labels
                self.l_humidity.setText(f"{data['Humidity']}%")
                self.l_wind_speed.setText(f"{data['WindSpeed']} m/s")
                self.l_pressure.setText(f"{data['Pressure']}")
                self.l_uv_index.setText(f"{data['UVIndex']}")
                self.l_day_temp.setText(
                    f"{'+' if data['DayTemperature'] > 0 else ''}"
                    + f"{data['DayTemperature']}°"
                )
                self.l_night_temp.setText(
                    f"{'+' if data['NightTemperature'] > 0 else ''}"
                    + f"{data['NightTemperature']}°"
                )
                self.l_sunrise.setText(f"{data['SunriseTime']}")
                self.l_sunset.setText(f"{data['SunsetTime']}")

            today()
            yesterday()
            tda()

        fill_data()

    def init_compare_sources(self) -> None:
        """Initialize the source comparison UI"""
        uic.loadUi(self.get_ui_file("compare_sources"), self)
        # Adding parsers list to QComboBoxes
        self.update_one_parser_ui(self.parserBox)
        self.update_one_parser_ui(self.parserBox_2)
        global parsers
        # Connecting UI to the parser
        if len(parsers) > 0:
            self.update_cmp_data_1(0)
            self.parserBox.setCurrentIndex(0)
            if len(parsers) > 1:
                self.updata_cmp_data_2(1)
                self.parserBox_2.setCurrentIndex(1)
            else:
                self.updata_cmp_data_2(0)
                self.parserBox_2.setCurrentIndex(0)

        self.parserBox.currentIndexChanged.connect(self.update_cmp_data_1)
        self.parserBox_2.currentIndexChanged.connect(self.updata_cmp_data_2)
        self.main_button.clicked.connect(self.init_main)

    def update_cmp_data_1(self, index) -> None:
        """Update data for first comparison box"""
        global parsers, CURRENT_PARSER
        CURRENT_PARSER = parsers[index]
        data = self.get_data()
        if data is None:
            return False
        # Filling parsed data into UI labels
        self.l_temp.setText(
            f"{'+' if data['Temperature'] > 0 else ''}" + f"{data['Temperature']}°"
        )
        self.l_humidity.setText(f"{data['Humidity']}%")
        self.l_wind_speed.setText(f"{data['WindSpeed']} m/s")
        self.l_pressure.setText(f"{data['Pressure']}")
        self.l_uv_index.setText(f"{data['UVIndex']}")
        self.l_day_temp.setText(
            f"{'+' if data['DayTemperature'] > 0 else ''}"
            + f"{data['DayTemperature']}°"
        )
        self.l_night_temp.setText(
            f"{'+' if data['NightTemperature'] > 0 else ''}"
            + f"{data['NightTemperature']}°"
        )
        self.l_sunrise.setText(f"{data['SunriseTime']}")
        self.l_sunset.setText(f"{data['SunsetTime']}")

    def updata_cmp_data_2(self, index) -> None:
        """Update data for second comparison box"""
        global parsers, CURRENT_PARSER
        CURRENT_PARSER = parsers[index]
        data = self.get_data()
        if data is None:
            return False
        # Filling parsed data into UI labels
        self.l_temp_2.setText(
            f"{'+' if data['Temperature'] > 0 else ''}" + f"{data['Temperature']}°"
        )
        self.l_humidity_2.setText(f"{data['Humidity']}%")
        self.l_wind_speed_2.setText(f"{data['WindSpeed']} m/s")
        self.l_pressure_2.setText(f"{data['Pressure']}")
        self.l_uv_index_2.setText(f"{data['UVIndex']}")
        self.l_day_temp_2.setText(
            f"{'+' if data['DayTemperature'] > 0 else ''}"
            + f"{data['DayTemperature']}°"
        )
        self.l_night_temp_2.setText(
            f"{'+' if data['NightTemperature'] > 0 else ''}"
            + f"{data['NightTemperature']}°"
        )
        self.l_sunrise_2.setText(f"{data['SunriseTime']}")
        self.l_sunset_2.setText(f"{data['SunsetTime']}")


# Program's entry point
# Creating application and window instances


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = Windows()
    MainWindow.show()
    sys.exit(app.exec_())
