import re
from datetime import datetime
import serial
import sys
from astropy import units
from astropy.units import cds, imperial
from chimera.core.exceptions import OptionConversionException
from chimera.instruments.weatherstation import WeatherBase
from chimera.interfaces.weatherstation import WeatherTemperature, WeatherRain, WSValue, WeatherHumidity, \
    WeatherPressure, WeatherWind

import numpy as np

regex_header = re.compile('(?P<id_station>[0-9]+)(T|R)+(?P<id_msg>.+?),')
regex_data = re.compile('(?P<type>[A-Z][a-z])=+(?P<value>.+?(,|$))')
regex_eol = re.compile('(,|\r)$')

# From Vaisala WXT520 manual (M210906EN-C), page 70
vaisala_unit_dict = {
    'Pa': {'H': 100 * units.Pa, 'P': units.Pa, 'B': units.bar, 'M': cds.mmHg, 'I': 25.399999705 * cds.mmHg},  # Pressure
    'Sx': {'M': units.meter / units.second, 'K': units.kilometer / units.second, 'S': imperial.mi / units.hour,  # Wind
           'N': imperial.knot}}


class Vaisala(WeatherBase, WeatherTemperature, WeatherHumidity, WeatherPressure, WeatherWind, WeatherRain):
    __config__ = dict(
        model="Vaisala weather transmitter WXT520",
        device="COM4",
        id_station=0
    )

    def __init__(self):
        WeatherBase.__init__(self)
        self._data = dict()

    def __start__(self):
        """
        Open Serial and set frequency to once every 10 seconds
        """
        self._serial = serial.Serial(self["device"], baudrate=19200, timeout=0)
        self.setHz(1 / 10.)

    def __stop__(self):
        self._serial.flush()
        self._serial.close()

    def control(self):
        self.log.debug('Control.')
        lines = self._serial.readlines()
        self.log.debug('Control serial.')

        for line in lines:
            self.log.debug('Updating: ' + line)
            self.update_data(line)
        self.log.debug('Control done.')
        return True

    def get_header(self, line):
        return [m.groupdict() for m in regex_header.finditer(line)][0]

    def get_data(self, line):
        return {m[0]: regex_eol.sub('', m[1]) for m in regex_data.findall(line)}

    def update_data(self, line):
        header = self.get_header(line)
        self.log.debug("Header: " + str(header))
        if int(header['id_station']) == self["id_station"]:
            data = self.get_data(line)
            self.log.debug("Data: " + str(data))
            self._data[header['id_msg']] = data
            self._data[header['id_msg']]['obs_time'] = datetime.utcnow()
            self.log.debug("Data dict:" + str(self._data))

    def rain_rate(self, unit_out=units.imperial.inch / units.hour):
        pass

    def isRaining(self):
        return False

    def wind_direction(self, unit_out=units.degree):
        if unit_out not in self.__accepted_direction_unit__:
            raise OptionConversionException("Invalid wind direction unit %s." % unit_out)

        value = float(self._data['1']['Dm'][:-1])

        return WSValue(self._data['1']['obs_time'], self._convert_units(value, units.degree, unit_out), unit_out)

    def wind_speed(self, unit_out=units.meter / units.second):

        if unit_out not in self.__accepted_speed_units__:
            raise OptionConversionException("Invalid wind speed unit %s." % unit_out)

        value, unit = float(self._data['1']['Sm'][:-1]), vaisala_unit_dict['Sx'][self._data['1']['Sm'][-1]]

        return WSValue(self._data['1']['obs_time'], self._convert_units(value, unit, unit_out), unit_out)

    def pressure(self, unit_out=units.Pa):

        if unit_out not in self.__accepted_pressures_unit__:
            raise OptionConversionException("Invalid pressure unit %s." % unit_out)

        value, unit = float(self._data['2']['Pa'][:-1]), vaisala_unit_dict['Pa'][self._data['2']['Pa'][-1]]

        return WSValue(self._data['2']['obs_time'], self._convert_units(value, unit, unit_out), unit_out)

    def humidity(self, unit_out=units.pct):
        if unit_out not in self.__accepted_humidity_units__:
            raise OptionConversionException("Invalid humidity unit %s." % unit_out)

        value, unit = float(self._data['2']['Ua'][:-1]), self._data['2']['Ua'][-1]

        return WSValue(self._data['2']['obs_time'], self._convert_units(value, units.pct, unit_out), unit_out)

    def temperature(self, unit_out=units.Celsius):
        if unit_out not in self.__accepted_temperature_units__:
            raise OptionConversionException("Invalid temperature unit %s." % unit_out)

        value, unit = float(self._data['2']['Ta'][:-1]), self._data['2']['Ta'][-1]

        return WSValue(self._data['2']['obs_time'],
                       self._convert_units(value, units.Celsius if unit == 'C' else units.Fahrenheit, units.Celsius,
                                           unit_out), unit_out)

    def dew_point(self, unit_out=units.Celsius):
        '''
        Calculates dew point according to the  Arden Buck equation (https://en.wikipedia.org/wiki/Dew_point).

        :param unit_out:
        :return:
        '''

        b = 18.678
        c = 257.14  # Celsius
        d = 235.5  # Celsius

        gamma_m = lambda T, RH: np.log(RH / 100. * np.exp((b - T / d) * (T / (c + T))))
        Tdp = lambda T, RH: c * gamma_m(T, RH) / (b - gamma_m(T, RH))

        return WSValue(self._data['2']['obs_time'],
                       self._convert_units(Tdp(self.temperature(units.deg_C).value,
                                               self.humidity(units.pct).value),
                                           units.Celsius, unit_out), unit_out)

    if __name__ == '__main__':
        with open('../../tests/example_data.txt') as fp:
            for line in fp.readlines():
                sys.stdout.write(line)
            print('\t' + str([m.groupdict() for m in regex_header.finditer(line)][0]))
            print('\t' + str({m[0]: regex_eol.sub('', m[1]) for m in regex_data.findall(line)}))

            # print re.findall()
