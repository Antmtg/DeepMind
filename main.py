import machine
import ssd1306
import time
import uos

# =============================================================================
# PARÁMETROS DE CONFIGURACIÓN CLÍNICA
# =============================================================================
SUAVIDAD_FACTOR = 0.7          # Filtro exponencial para BPM (0 = rápido, 1 = lento)
UMBRAL_FONDO = 50000           # Umbral para detectar dedo retirado (IR)
COMPENSACION_LUZ_AMBIENTE = 0  # Compensación luz ambiente (0 = cámara oscura)
TIEMPO_CALIBRACION_MS = 5000   # Duración de la calibración
TIEMPO_MEDICION_MS = 25000     # Duración de la toma de señal
INTERVALO_MIN_MS = 300         # Refractario mínimo (200 BPM máximo)
INTERVALO_MAX_MS = 1500        # Intervalos mayores se descartan (40 BPM mínimo)
PICOS_MINIMOS = 2              # Mínimo de pulsos válidos para BPM
RATIO_SPO2_MIN = 0.30          # Límite inferior sanidad ratio SpO2
RATIO_SPO2_MAX = 3.00          # Límite superior sanidad ratio SpO2
MAX_USUARIOS = 5

# Pines I2C
PIN_OLED_SDA = 21
PIN_OLED_SCL = 22
PIN_SENSOR_SDA = 25
PIN_SENSOR_SCL = 26
PIN_BOTON_BOOT = 0

# Direcciones I2C
MAX30102_ADDR = 0x57
OLED_ADDR = 0x3C

# Registros MAX30102
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A
REG_LED1_PA = 0x0C     # Rojo (LED1)
REG_LED2_PA = 0x0D     # IR (LED2)
REG_FIFO_DATA = 0x07
REG_TINT = 0x1F        # Temperatura entera
REG_TFRACT = 0x20      # Temperatura fracción
REG_TCONFIG = 0x21     # Configuración temperatura

# Estados del sistema
ESTADO_ESPERANDO = 0
ESTADO_CALIBRANDO = 1
ESTADO_MIDIENDO = 2
ESTADO_RESULTADO = 3

# =============================================================================
# HARDWARE: I2C, PANTALLA Y WATCHDOG
# =============================================================================
i2c_oled = machine.SoftI2C(sda=machine.Pin(PIN_OLED_SDA), scl=machine.Pin(PIN_OLED_SCL), freq=100000)
pantalla = ssd1306.SSD1306_I2C(128, 64, i2c_oled)

i2c_sensor = machine.SoftI2C(sda=machine.Pin(PIN_SENSOR_SDA), scl=machine.Pin(PIN_SENSOR_SCL), freq=100000)

# Watchdog de hardware: resucita el ESP32 si se bloquea (8 segundos de margen)
wdt = machine.WDT(timeout=8000)

boton_boot = machine.Pin(PIN_BOTON_BOOT, machine.Pin.IN, machine.Pin.PULL_UP)
usuario_actual = 1

# =============================================================================
# CSV LOCAL EN EL ESP32 (UN ARCHIVO POR USUARIO)
# =============================================================================
def guardar_csv(usuario, timestamp, bpm, spo2, temp):
    archivo = "validaciones_usuario_{}.csv".format(usuario)
    try:
        # Crear con cabecera si no existe
        try:
            uos.stat(archivo)
        except OSError:
            with open(archivo, "w") as f:
                f.write("timestamp_ms,BPM,SpO2,Temp_C\n")
        with open(archivo, "a") as f:
            f.write("{},{},{},{}\n".format(timestamp, bpm, spo2, temp))
    except OSError as e:
        print("Error escribiendo CSV:", e)

# =============================================================================
# SENSOR MAX30102
# =============================================================================
def escribir_registro(reg, valor):
    try:
        i2c_sensor.writeto_mem(MAX30102_ADDR, reg, bytes([valor]))
        return True
    except OSError:
        return False

def leer_registro(reg, nbytes=1):
    try:
        return i2c_sensor.readfrom_mem(MAX30102_ADDR, reg, nbytes)
    except OSError:
        return None

def inicializar_max30102():
    """Inicializa el MAX30102 en modo SpO2. Reintenta hasta 3 veces."""
    for intento in range(3):
        try:
            # Reset del sensor
            escribir_registro(REG_MODE_CONFIG, 0x40)
            time.sleep(0.1)
            # Configuración SpO2: rango 4096nA, 100 Hz, ancho de pulso 411 us
            escribir_registro(REG_SPO2_CONFIG, 0x27)
            # Corriente LED Rojo y IR (0x3F = ~50 mA)
            escribir_registro(REG_LED1_PA, 0x3F)
            escribir_registro(REG_LED2_PA, 0x3F)
            # Modo SpO2 (LED rojo + IR)
            escribir_registro(REG_MODE_CONFIG, 0x03)
            wdt.feed()
            return True
        except OSError:
            time.sleep(0.5)
    return False

def recalibrar_sensor_continuo():
    """Reestablece configuración base sin reset completo."""
    escribir_registro(REG_MODE_CONFIG, 0x03)
    escribir_registro(REG_SPO2_CONFIG, 0x27)

def leer_sensores_duales():
    """Lee 6 bytes del FIFO: 3 bytes rojo + 3 bytes IR."""
    try:
        data = i2c_sensor.readfrom_mem(MAX30102_ADDR, REG_FIFO_DATA, 6)
        if data is None or len(data) < 6:
            inicializar_max30102()
            return 0, 0
        rojo_raw = ((data[0] << 16) | (data[1] << 8) | data[2]) & 0x03FFFF
        ir_raw = ((data[3] << 16) | (data[4] << 8) | data[5]) & 0x03FFFF

        # Ceros absolutos = sensor apagado o sin contacto I2C
        if rojo_raw == 0 and ir_raw == 0:
            inicializar_max30102()
            return 0, 0

        rojo_filtrado = max(0, rojo_raw - COMPENSACION_LUZ_AMBIENTE)
        ir_filtrado = max(0, ir_raw - COMPENSACION_LUZ_AMBIENTE)
        return rojo_filtrado, ir_filtrado
    except OSError:
        inicializar_max30102()
        return 0, 0

def leer_temp():
    """Lee la temperatura del die del MAX30102 sin alterar el modo SpO2."""
    try:
        escribir_registro(REG_TCONFIG, 0x01)   # Iniciar conversión de temperatura
        time.sleep_ms(30)                       # Esperar conversión (~25 ms típico)
        entero = leer_registro(REG_TINT, 1)[0]
        fraccion = leer_registro(REG_TFRACT, 1)[0]
        if entero > 127:
            entero -= 256
        return round(entero + (fraccion * 0.0625), 1)
    except OSError:
        inicializar_max30102()
        return 0.0

# =============================================================================
# PANTALLA OLED
# =============================================================================
def pantalla_limpiar():
    pantalla.fill(0)

def pantalla_mostrar_texto(lineas, centrar=False):
    """lineas: lista de tuplas (texto, y) o (texto, x, y)."""
    pantalla.fill(0)
    for item in lineas:
        if len(item) == 2:
            texto, y = item
            x = (128 - len(texto) * 8) // 2 if centrar else 4
            pantalla.text(texto, x, y)
        else:
            texto, x, y = item
            pantalla.text(texto, x, y)
    pantalla.show()

def mostrar_bienvenida():
    pantalla_mostrar_texto([
        ("PROTOTIPO", 0),
        ("Usuario: {}".format(usuario_actual), 18),
        ("Coloque indice", 42),
    ], centrar=True)

def mostrar_calibracion(segundos, puntos):
    ancho = len(puntos) * 8
    pos_x = (128 - ancho) // 2
    pantalla.fill(0)
    pantalla.text("Calibrando...", 24, 10)
    pantalla.text("Usr: {}".format(usuario_actual), 40, 50)
    pantalla.text(puntos, pos_x, 30)
    pantalla.show()

def mostrar_medicion(segundos_restantes, frase, progreso_px):
    pantalla.fill(0)
    pantalla.text("Tiempo: {}s".format(segundos_restantes), 25, 5)
    pantalla.text(frase, 4, 25)
    pantalla.rect(0, 45, 128, 12, 1)
    pantalla.fill_rect(0, 45, progreso_px, 12, 1)
    pantalla.show()

def mostrar_resultado(bpm, spo2, temp):
    pantalla_mostrar_texto([
        ("Usr {} Listo".format(usuario_actual), 24, 0),
        ("BPM : {}".format(bpm), 0, 25),
        ("SpO2: {} %".format(spo2), 0, 38),
        ("Temp: {} C".format(temp), 0, 51),
    ])

def mostrar_error(lineas):
    pantalla_mostrar_texto(lineas)

# =============================================================================
# BOTÓN BOOT CON ANTIRREBOTE (DEBOUNCE)
# =============================================================================
class BotonDebounce:
    def __init__(self, pin, tiempo_ms=50):
        self.pin = pin
        self.tiempo_ms = tiempo_ms
        self.estado_estable = pin.value()
        self.ultimo_cambio = time.ticks_ms()

    def actualizar(self):
        """Devuelve True si se detectó un pulso completo (presionar + soltar)."""
        valor_actual = self.pin.value()
        ahora = time.ticks_ms()
        if valor_actual != self.estado_estable:
            if time.ticks_diff(ahora, self.ultimo_cambio) > self.tiempo_ms:
                self.estado_estable = valor_actual
                self.ultimo_cambio = ahora
                return True  # Cambio confirmado
        return False

    def presionado(self):
        """True si el botón está presionado (nivel bajo por PULL_UP)."""
        return self.estado_estable == 0

boton = BotonDebounce(boton_boot, tiempo_ms=60)

# =============================================================================
# FILTRO DE MEDIA MÓVIL PARA SUAVIZAR SEÑAL IR
# =============================================================================
class FiltroMovil:
    def __init__(self, tamano=5):
        self.tamano = tamano
        self.muestras = []

    def aplicar(self, valor):
        self.muestras.append(valor)
        if len(self.muestras) > self.tamano:
            self.muestras.pop(0)
        return sum(self.muestras) // len(self.muestras)

filtro_ir = FiltroMovil(tamano=5)

# =============================================================================
# VARIABLES GLOBALES DE ESTADO
# =============================================================================
estado = ESTADO_ESPERANDO
bpm_suavizado = 0.0

# =============================================================================
# FUNCIONES DE CADA ESTADO
# =============================================================================
def estado_esperando():
    global estado, bpm_suavizado
    wdt.feed()
    mostrar_bienvenida()

    # Cambio de usuario con botón
    if boton.actualizar() and boton.presionado():
        usuario_actual = usuario_actual % MAX_USUARIOS + 1
        mostrar_bienvenida()
        time.sleep_ms(300)

    _, ir_actual = leer_sensores_duales()
    if ir_actual >= UMBRAL_FONDO:
        estado = ESTADO_CALIBRANDO
        return

    recalibrar_sensor_continuo()
    time.sleep_ms(100)

def estado_calibrando():
    global estado
    wdt.feed()
    inicio = time.ticks_ms()
    puntos_texto = ""

    while time.ticks_diff(time.ticks_ms(), inicio) < TIEMPO_CALIBRACION_MS:
        wdt.feed()
        _, ir_val = leer_sensores_duales()
        if ir_val < UMBRAL_FONDO:
            print("Error: dedo retirado durante calibración.")
            mostrar_bienvenida()
            estado = ESTADO_ESPERANDO
            return

        transcurrido = time.ticks_diff(time.ticks_ms(), inicio)
        puntos_texto = ". " * min(5, (transcurrido // 1000) + 1)
        mostrar_calibracion(transcurrido // 1000, puntos_texto)
        time.sleep_ms(50)

    estado = ESTADO_MIDIENDO

def estado_midiendo():
    global estado, bpm_suavizado
    wdt.feed()
    inicio = time.ticks_ms()
    intervalos = []

    ac_rojo_max, ac_rojo_min = 0, 999999
    dc_rojo_acum, muestras_rojo = 0, 0
    ac_ir_max, ac_ir_min = 0, 999999
    dc_ir_acum, muestras_ir = 0, 0

    lectura_anterior = 0
    subiendo = False
    ultimo_pico = 0
    medicion_valida = True
    umbral_pico = None  # Umbral dinámico basado en amplitud

    while time.ticks_diff(time.ticks_ms(), inicio) < TIEMPO_MEDICION_MS:
        wdt.feed()
        ahora = time.ticks_ms()
        rojo_val, ir_val = leer_sensores_duales()

        if ir_val < UMBRAL_FONDO:
            print("Error: dedo retirado durante la medición.")
            medicion_valida = False
            break

        ir_suave = filtro_ir.aplicar(ir_val)

        # Estadísticas para SpO2
        if rojo_val > ac_rojo_max: ac_rojo_max = rojo_val
        if rojo_val < ac_rojo_min: ac_rojo_min = rojo_val
        dc_rojo_acum += rojo_val
        muestras_rojo += 1

        if ir_val > ac_ir_max: ac_ir_max = ir_val
        if ir_val < ac_ir_min: ac_ir_min = ir_val
        dc_ir_acum += ir_val
        muestras_ir += 1

        # Umbral dinámico de pico (60% del rango observado)
        if umbral_pico is None and muestras_ir > 20:
            rango = ac_ir_max - ac_ir_min
            umbral_pico = ac_ir_min + rango * 0.6

        # Detección de pico con histéresis
        if umbral_pico is not None:
            if ir_suave > umbral_pico and not subiendo:
                subiendo = True
            elif subiendo and ir_suave < (umbral_pico * 0.4):
                subiendo = False
                if ultimo_pico != 0:
                    intervalo = time.ticks_diff(ahora, ultimo_pico)
                    if INTERVALO_MIN_MS < intervalo < INTERVALO_MAX_MS:
                        intervalos.append(intervalo)
                        bpm_instante = 60000 / intervalo
                        if bpm_suavizado == 0:
                            bpm_suavizado = bpm_instante
                        else:
                            bpm_suavizado = (bpm_suavizado * SUAVIDAD_FACTOR) + (bpm_instante * (1 - SUAVIDAD_FACTOR))
                ultimo_pico = ahora

        # Estadísticas de picos (fallback al método original si no hay umbral)
        elif ir_val > lectura_anterior:
            subiendo = True
        elif subiendo and ir_val < lectura_anterior:
            subiendo = False
            if ultimo_pico != 0:
                intervalo = time.ticks_diff(ahora, ultimo_pico)
                if INTERVALO_MIN_MS < intervalo < INTERVALO_MAX_MS:
                    intervalos.append(intervalo)
                    bpm_instante = 60000 / intervalo
                    if bpm_suavizado == 0:
                        bpm_suavizado = bpm_instante
                    else:
                        bpm_suavizado = (bpm_suavizado * SUAVIDAD_FACTOR) + (bpm_instante * (1 - SUAVIDAD_FACTOR))
            ultimo_pico = ahora

        lectura_anterior = ir_val

        # Pantalla
        transcurrido = time.ticks_diff(ahora, inicio)
        segundos_restantes = 25 - (transcurrido // 1000)
        frase = "Respire lento..." if (ahora // 1000) % 2 == 0 else "Respire lento"
        progreso_px = int((transcurrido / TIEMPO_MEDICION_MS) * 128)
        mostrar_medicion(segundos_restantes, frase, progreso_px)

        print("Pulsacion_IR:{}, Pulsacion_Rojo:{}".format(ir_val, rojo_val))
        print("CSV_RAW:Usuario_{},{},{},{}".format(usuario_actual, ahora, ir_val, rojo_val))
        time.sleep_ms(10)

    # ---- Procesar resultado ----
    if medicion_valida and len(intervalos) >= PICOS_MINIMOS and muestras_rojo > 0 and muestras_ir > 0:
        promedio_intervalo = sum(intervalos) / len(intervalos)
        bpm_calculado = 60000 / promedio_intervalo
        bpm_final = round(bpm_calculado, 1)

        ac_rojo = ac_rojo_max - ac_rojo_min
        dc_rojo = dc_rojo_acum / muestras_rojo
        ac_ir = ac_ir_max - ac_ir_min
        dc_ir = dc_ir_acum / muestras_ir

        spo2_final = 0
        if dc_rojo > 0 and dc_ir > 0 and ac_ir > 0:
            ratio_R = (ac_rojo / dc_rojo) / (ac_ir / dc_ir)
            # Sanidad del ratio antes de aplicar fórmula
            if RATIO_SPO2_MIN <= ratio_R <= RATIO_SPO2_MAX:
                # Fórmula cuadrática oficial Maxim Integrated
                spo2_calculado = -45.060 * (ratio_R * ratio_R) + 30.354 * ratio_R + 94.845
                spo2_final = int(round(spo2_calculado))
                if spo2_final > 100: spo2_final = 100
                if spo2_final < 0: spo2_final = 0

        temp_final = leer_temp()

        mostrar_resultado(bpm_final, spo2_final, temp_final)

        timestamp_actual = time.ticks_ms()
        guardar_csv(usuario_actual, timestamp_actual, bpm_final, spo2_final, temp_final)

        print("=============================")
        print("APP_DATA:{},{},{}".format(bpm_final, spo2_final, temp_final))
        print("CSV_CALC:Usuario_{},{},{},{},{}".format(usuario_actual, timestamp_actual, bpm_final, spo2_final, temp_final))
        print("BPM: {} | SpO2: {}% | Temp: {} C".format(bpm_final, spo2_final, temp_final))
        print("=============================")

        # Esperar a que se retire el dedo antes de volver a reposo
        while True:
            wdt.feed()
            _, ir_check = leer_sensores_duales()
            if ir_check < UMBRAL_FONDO:
                break
            time.sleep(0.5)
        mostrar_bienvenida()
        estado = ESTADO_ESPERANDO
    else:
        mostrar_error([("Lectura", 35, 20), ("invalida", 30, 35)])
        time.sleep(3)
        mostrar_bienvenida()
        estado = ESTADO_ESPERANDO

# =============================================================================
# INICIALIZACIÓN Y BUCLE PRINCIPAL
# =============================================================================
print("CSV_HEADER:Usuario,Timestamp_ms,BPM,SpO2,Temp_C")

if not inicializar_max30102():
    pantalla_limpiar()
    pantalla.text("ERROR DE SENSOR", 4, 20)
    pantalla.show()
    while True:
        wdt.feed()
        time.sleep(1)

mostrar_bienvenida()
print("Sistema listo. Suavidad: {} | Umbral Fondo: {}".format(SUAVIDAD_FACTOR, UMBRAL_FONDO))

while True:
    if estado == ESTADO_ESPERANDO:
        estado_esperando()
    elif estado == ESTADO_CALIBRANDO:
        estado_calibrando()
    elif estado == ESTADO_MIDIENDO:
        estado_midiendo()
    elif estado == ESTADO_RESULTADO:
        estado = ESTADO_ESPERANDO

    wdt.feed()
    time.sleep_ms(20)