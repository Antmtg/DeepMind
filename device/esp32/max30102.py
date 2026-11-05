"""Controlador minimo del MAX30102 para MicroPython.

El MAX30102 entrega muestras PPG de luz roja e infrarroja. Este modulo:

1. Configura el sensor en modo SpO2 a 100 Hz.
2. Lee la FIFO de 32 muestras.
3. Estima SpO2 y pulso con un algoritmo de banco (DC/AC y picos).
4. Puede leer la temperatura interna del dado (no es temperatura corporal).

No sustituye una validacion clinica ni un algoritmo certificado. Si no hay
muestras suficientes o la senal es invalida, devuelve None: nunca inventa
valores.
"""

import time


REG_INTR_STATUS_1 = 0x00
REG_INTR_STATUS_2 = 0x01
REG_INTR_ENABLE_1 = 0x02
REG_INTR_ENABLE_2 = 0x03
REG_FIFO_WR_PTR = 0x04
REG_OVF_COUNTER = 0x05
REG_FIFO_RD_PTR = 0x06
REG_FIFO_DATA = 0x07
REG_FIFO_CONFIG = 0x08
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A
REG_LED1_PA = 0x0C
REG_LED2_PA = 0x0D
REG_TEMP_INT = 0x1F
REG_TEMP_FRAC = 0x20
REG_TEMP_CONFIG = 0x21


class MAX30102:
    def __init__(self, i2c, address=0x57):
        self.i2c = i2c
        self.address = address
        self.available = False
        self.initialize()

    def _write(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value & 0xFF]))

    def _read(self, register, length=1):
        return self.i2c.readfrom_mem(self.address, register, length)

    def initialize(self):
        """Resetea y configura el sensor. Lanza OSError si no responde."""
        try:
            self._read(REG_MODE_CONFIG)
        except OSError:
            self.available = False
            raise

        self._write(REG_MODE_CONFIG, 0x40)  # reset
        time.sleep(0.1)
        for _ in range(20):
            if not (self._read(REG_MODE_CONFIG)[0] & 0x40):
                break
            time.sleep(0.05)

        # Limpia punteros y contador de desbordamiento.
        self._write(REG_FIFO_WR_PTR, 0x00)
        self._write(REG_OVF_COUNTER, 0x00)
        self._write(REG_FIFO_RD_PTR, 0x00)

        # Promedio de 4 muestras, rollover activo, casi lleno en 17 muestras.
        self._write(REG_FIFO_CONFIG, 0x4F)
        # Modo SpO2: rojo + infrarrojo.
        self._write(REG_MODE_CONFIG, 0x03)
        # Rango 4096 nA, 100 muestras/s, ancho de pulso 411 us.
        self._write(REG_SPO2_CONFIG, 0x27)
        # Corriente de LED moderada. Ajustar segun el dedo y la placa.
        self._write(REG_LED1_PA, 0x24)
        self._write(REG_LED2_PA, 0x24)

        self._write(REG_FIFO_WR_PTR, 0x00)
        self._write(REG_OVF_COUNTER, 0x00)
        self._write(REG_FIFO_RD_PTR, 0x00)
        self.available = True

    def _fifo_count(self):
        write_ptr = self._read(REG_FIFO_WR_PTR)[0]
        read_ptr = self._read(REG_FIFO_RD_PTR)[0]
        return (write_ptr - read_ptr) & 0x1F

    def read_fifo(self):
        """Devuelve una lista de tuplas (rojo, infrarrojo) de 18 bits."""
        count = self._fifo_count()
        if count == 0:
            return []
        raw = self._read(REG_FIFO_DATA, count * 6)
        write_ptr = self._read(REG_FIFO_WR_PTR)[0]
        self._write(REG_FIFO_RD_PTR, write_ptr)

        samples = []
        for index in range(0, len(raw), 6):
            red = ((raw[index] << 16) | (raw[index + 1] << 8) | raw[index + 2]) & 0x03FFFF
            infrared = ((raw[index + 3] << 16) | (raw[index + 4] << 8) | raw[index + 5]) & 0x03FFFF
            samples.append((red, infrared))
        return samples

    def read_temperature(self):
        """Temperatura interna del dado en grados Celsius, o None."""
        try:
            self._write(REG_TEMP_CONFIG, 0x01)
            time.sleep(0.1)
            integer = self._read(REG_TEMP_INT)[0]
            fraction = self._read(REG_TEMP_FRAC)[0]
            if integer >= 128:
                integer -= 256
            return round(integer + (fraction & 0x0F) * 0.0625, 2)
        except OSError:
            return None

    def read_measurement(self, window_seconds=4, sample_hz=100):
        """Lee una ventana PPG y devuelve un dict o None si no es valida."""
        target = max(60, int(window_seconds * sample_hz))
        red_values = []
        ir_values = []
        started = time.ticks_ms()
        timeout_ms = int(window_seconds * 1000) + 3000

        while len(ir_values) < target:
            for red, infrared in self.read_fifo():
                red_values.append(red)
                ir_values.append(infrared)
            if time.ticks_diff(time.ticks_ms(), started) > timeout_ms:
                break
            time.sleep(0.01)

        if len(ir_values) < target // 2:
            return None

        # Descarta el primer 20 %: la FIFO puede traer muestras viejas.
        start = len(ir_values) // 5
        red_values = red_values[start:]
        ir_values = ir_values[start:]

        spo2 = estimate_spo2(red_values, ir_values)
        heart_rate = estimate_heart_rate(ir_values, sample_hz)
        if spo2 is None or heart_rate is None:
            return None

        return {
            "spo2": spo2,
            "heart_rate_bpm": heart_rate,
            "sensor_temperature_c": self.read_temperature(),
        }


def _mean(values):
    return sum(values) / float(len(values)) if values else 0.0


def estimate_spo2(red_values, ir_values, intercept=110.0, slope=25.0):
    """Aproximacion por relacion de componentes AC/DC.

    SpO2 = intercepto - pendiente * (AC_rojo/DC_rojo) / (AC_ir/DC_ir).
    Es una formula de banco; requiere calibracion para uso real.
    """
    if len(red_values) < 30 or len(ir_values) < 30:
        return None
    red_dc = _mean(red_values)
    ir_dc = _mean(ir_values)
    if red_dc <= 0 or ir_dc <= 0:
        return None
    red_ac = max(red_values) - min(red_values)
    ir_ac = max(ir_values) - min(ir_values)
    if ir_ac <= 0 or red_ac <= 0:
        return None

    ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
    spo2 = intercept - slope * ratio
    if spo2 < 70 or spo2 > 100:
        return None
    return int(round(spo2))


def _smooth(values, size=5):
    if len(values) < size:
        return list(values)
    result = []
    total = 0
    for index, value in enumerate(values):
        total += value
        if index >= size:
            total -= values[index - size]
        result.append(total / float(min(index + 1, size)))
    return result


def estimate_heart_rate(ir_values, sample_hz=100):
    """Cuenta picos del PPG infrarrojo con un periodo refractario."""
    if len(ir_values) < sample_hz:
        return None

    smoothed = _smooth(ir_values, 5)
    baseline = _mean(smoothed)
    centered = [value - baseline for value in smoothed]
    deviation = (sum(value * value for value in centered) / len(centered)) ** 0.5
    if deviation <= 0:
        return None

    threshold = deviation * 0.45
    min_distance = int(sample_hz * 0.30)  # maximo ~200 lpm
    peaks = []
    last_peak = -min_distance
    for index in range(1, len(centered) - 1):
        value = centered[index]
        if (
            value > threshold
            and value >= centered[index - 1]
            and value > centered[index + 1]
            and index - last_peak >= min_distance
        ):
            peaks.append(index)
            last_peak = index

    if len(peaks) < 3:
        return None

    intervals = [peaks[index] - peaks[index - 1] for index in range(1, len(peaks))]
    average_interval = _mean(intervals)
    if average_interval <= 0:
        return None

    bpm = int(round(60.0 * sample_hz / average_interval))
    if bpm < 35 or bpm > 220:
        return None

    # Descarta una medicion con intervalos demasiado irregulares.
    variance = sum((interval - average_interval) ** 2 for interval in intervals) / len(intervals)
    if variance ** 0.5 > average_interval * 0.55:
        return None
    return bpm
