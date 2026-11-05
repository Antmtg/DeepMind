"""
BioMonitor O2T - Pantalla monocromatica para el ESP32 (MicroPython)

Driver autonomo para displays de un solo color por I2C (cuadritos pixel
grandes) de 128x64, tipicamente SSD1306 y variantes SH1106 con la misma
pata:  GND, VCC, SCL, SDA a 3.3 V en la direccion 0x3C.

La pantalla SOLO refleja informacion: si falla, el ESP32 sigue midiendo y
enviando. Todo metodo tolera errores internos.
"""

import time

import framebuf

ANCHO = 128
ALTO = 64


class Pantalla:
    """Display monocromo 128x64 por I2C con dibujos de pixeles grandes."""

    def __init__(self, i2c, direccion=0x3C, driver="ssd1306"):
        self.disponible = False
        self.i2c = i2c
        self.direccion = direccion
        self.driver = driver
        self.buffer = bytearray((ALTO // 8) * ANCHO)
        self.fb = framebuf.FrameBuffer(self.buffer, ANCHO, ALTO, framebuf.MONO_VLSB)
        try:
            dispositivos = i2c.scan()
        except Exception:
            dispositivos = []
        if direccion not in dispositivos:
            raise RuntimeError(
                "Display no responde en 0x{:02X} (encontrados: {})".format(
                    direccion, [hex(d) for d in dispositivos]
                )
            )
        self._inicializar()
        self.fb.fill(0)
        self.refrescar()
        self.disponible = True

    # --- bajo nivel ------------------------------------------------------

    def _cmd(self, *comandos):
        self.i2c.writeto(self.direccion, bytearray([0x00]) + bytes(comandos))

    def _inicializar(self):
        self._cmd(
            0xAE,          # display apagado durante la configuracion
            0xD5, 0x80,    # reloj interno
            0xA8, 0x3F,    # multiplex: 64 lineas
            0xD3, 0x00,    # offset 0
            0x40,          # linea de inicio 0
            0x8D, 0x14,    # bomba de carga encendida
            0x20, 0x00,    # modo de direccionamiento horizontal
            0xA1,          # mapeo de segmentos
            0xC8,          # barrido de lineas
            0xDA, 0x12,    # pines COM alternos
            0x81, 0xCF,    # contraste
            0xD9, 0xF1,    # pre-carga
            0xDB, 0x40,    # nivel VCOM
            0xA4,          # mostrar contenido de la RAM
            0xA6,          # colores normales (1 = encendido)
        )
        if self.driver == "sh1106":
            # Variante con offset interno de 2 columnas.
            self._cmd(0xA3, 0x00, 0x3F)
        self._cmd(0xAF)    # display encendido

    def refrescar(self):
        """Manda el framebuffer completo al display."""
        desplazamiento = 2 if self.driver == "sh1106" else 0
        for pagina in range(ALTO // 8):
            self._cmd(0xB0 + pagina, desplazamiento & 0x0F, 0x10 | (desplazamiento >> 4))
            inicio = pagina * ANCHO
            datos = self.buffer[inicio:inicio + ANCHO]
            for trozo in range(0, ANCHO, 32):
                self.i2c.writeto(
                    self.direccion,
                    bytes([0x40]) + datos[trozo:trozo + 32],
                )

    # --- utilidades de dibujo -------------------------------------------

    def texto_escalado(self, texto, x, y, escala, color=1):
        """Texto con pixeles grandes: cada pixel del glifo se agranda."""
        w = len(texto) * 8
        temporal = framebuf.FrameBuffer(
            bytearray((w * 8 + 7) // 8), w, 8, framebuf.MONO_VLSB
        )
        temporal.text(texto, 0, 0, color)
        for fila in range(8):
            for columna in range(w):
                if temporal.pixel(columna, fila):
                    self.fb.fill_rect(
                        x + columna * escala,
                        y + fila * escala,
                        escala,
                        escala,
                        color,
                    )

    # --- pantallas -------------------------------------------------------

    def mostrar_datos(self, spo2, pulso, estado):
        """Lectura principal: SpO2 grande, pulso y estado."""
        self.fb.fill(0)
        try:
            self.texto_escalado("{:.0f}%".format(spo2), 0, 2, 3)
            self.fb.text("SpO2", 100, 12, 1)
            self.fb.text("{} lpm".format(pulso), 0, 28, 1)
            self.fb.text(estado[:21], 0, 56, 1)
            self.refrescar()
        except Exception:
            pass

    def mostrar_codigo(self, codigo, validez=""):
        """Codigo de emparejamiento de 6 digitos con pixeles grandes."""
        self.fb.fill(0)
        try:
            self.fb.text("Empareja tu sensor:", 0, 0, 1)
            self.texto_escalado(codigo, 0, 14, 2)
            if validez:
                self.fb.text(str(validez)[:21], 0, 34, 1)
            self.fb.text("Escribelo en la app", 0, 56, 1)
            self.refrescar()
        except Exception:
            pass

    def mostrar_mensaje(self, linea1, linea2=""):
        self.fb.fill(0)
        try:
            self.fb.text(str(linea1)[:16], 0, 0, 1)
            self.texto_escalado(str(linea2)[:12], 0, 14, 1)
            self.refrescar()
        except Exception:
            pass


def inicializar_pantalla(i2c, config):
    """Crea la pantalla si config.USE_PANTALLA y existe el hardware."""
    if not getattr(config, "USE_PANTALLA", False):
        return None
    try:
        pantalla = Pantalla(
            i2c,
            direccion=getattr(config, "DISPLAY_ADDR", 0x3C),
            driver=getattr(config, "DISPLAY_DRIVER", "ssd1306"),
        )
        time.sleep_ms(50)
        pantalla.mostrar_mensaje("Iniciando...")
        return pantalla
    except Exception as exc:
        print("Pantalla no disponible:", exc)
        return None
