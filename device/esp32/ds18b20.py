"""Lectura opcional de temperatura corporal con DS18B20 (MicroPython).

Requiere el modulo `onewire` y `ds18x20` incluidos en las compilaciones
habituales de MicroPython para ESP32. Si el sensor no esta conectado, el
firmware continua y usa la temperatura interna del MAX30102 como referencia,
nunca como temperatura corporal.
"""

import time

try:
    import onewire
    import ds18x20
except ImportError:  # Algunas compilaciones no incluyen ds18x20.
    onewire = None
    ds18x20 = None


class DS18B20:
    def __init__(self, pin):
        self.available = False
        self.roms = []
        if onewire is None or ds18x20 is None:
            return
        try:
            self.bus = onewire.OneWire(pin)
            self.sensor = ds18x20.DS18X20(self.bus)
            self.roms = self.sensor.scan()
            self.available = bool(self.roms)
        except Exception:
            self.available = False

    def read(self):
        """Devuelve la temperatura en Celsius o None si no hay lectura."""
        if not self.available:
            return None
        try:
            self.sensor.convert_temp()
            time.sleep(0.75)
            values = []
            for rom in self.roms:
                value = self.sensor.read_temp(rom)
                if value is not None and -10.0 <= value <= 60.0:
                    values.append(value)
            if not values:
                return None
            return round(sum(values) / len(values), 2)
        except Exception:
            return None
