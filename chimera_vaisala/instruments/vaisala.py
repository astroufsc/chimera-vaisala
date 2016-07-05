import serial
from chimera.instruments.weatherstation import WeatherBase
from chimera.interfaces.weatherstation import WeatherTemperature, WeatherRain


class AAGCloudWatcherCOM(WeatherBase, WeatherTemperature, WeatherRain):
    __config__ = dict(
        model="Vaisala weather transmitter WXT520",
        device="COM4"
    )

    def __init__(self):
        WeatherBase.__init__(self)

    def __start__(self):
        """
        Start AAG Cloud Watcher software
        """
        self._serial = serial.Serial(self["device"], baudrate=19200, timeout=10)
        self.setHz(1/10)

    def __stop__(self):
        self._serial.close()

    def control(self):
        lines = self._serial.readlines()

        for line in lines:
            self.log.debug('Updating: '+line)
