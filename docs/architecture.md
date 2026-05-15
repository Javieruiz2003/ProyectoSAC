# Arquitectura del Sistema

## Diagrama de bloques hardware

El sistema usa la placa nRF5340 DK como controlador principal y el AD5940BIOZ como front-end analógico para medir bioimpedancia mediante electrodos ECG. La comunicación entre ambos se realiza por SPI2 y señales GPIO dedicadas para selección de chip, reset e interrupción.

```
┌──────────────────────┐        SPI2 + GPIO         ┌──────────────────────┐
│                      │  MOSI P1.13 -------------> │                      │
│      nRF5340 DK      │  MISO P1.14 <------------- │      AD5940BIOZ      │
│      cpuapp          │  SCLK P1.15 -------------> │   Bioimpedance AFE   │
│                      │  CS   P1.12 -------------> │                      │
│                      │  RST  P0.07 -------------> │                      │
│                      │  INT  P1.04 <------------- │                      │
│                      │                            └──────────┬───────────┘
│                      │                                       │
│ USB/UART logs        │                              Electrodos ECG
│ 115200 baud          │                                       │
└──────────┬───────────┘                                       │
           │                                                   │
           v                                                   v
  PC / Serial Terminal / Teleplot                  Brazo del usuario de prueba
```

## Diagrama de bloques software

El software se organiza en 5 capas, desarrolladas de abajo hacia arriba:

```
Capa 5: System Integration     ← main.c, arranque, bucle continuo, errores
         ▲
Capa 4: Communication          ← UART/logs, printk, formato para visualización
         ▲
Capa 3: Application Logic      ← Configuración BIA, sweep, magnitud y fase
         ▲
Capa 2: Driver / Port Layer    ← Port AD5940 sobre Zephyr SPI/GPIO
         ▲
Capa 1: Hardware Setup         ← Devicetree overlay + Kconfig (prj.conf)
```

### Capa 1: Hardware Setup

**Devicetree overlay** (`.overlay`) + **Kconfig** (`prj.conf`)

- Archivos: `boards/nrf5340dk_nrf5340_cpuapp.overlay`, `prj.conf`
- Periféricos habilitados: GPIO, SPI, logging, consola UART, `printk`, FPU y `printf` con coma flotante.
- SPI usado: `spi2`, con `spi4` deshabilitado para evitar conflictos.
- Pines principales:
  - SCLK: P1.15
  - MOSI: P1.13
  - MISO: P1.14
  - CS: P1.12, activo bajo y controlado manualmente por GPIO
  - RESET: P0.07, activo bajo
  - INT: P1.04, entrada con pull-up y activo bajo
- Verificación: el proyecto compila y `device_is_ready()` confirma que SPI2 está disponible.

### Capa 2: Driver / Port Layer

**Zephyr APIs:** `spi_transceive()`, `gpio_pin_configure_dt()`, `gpio_pin_set_dt()`, `gpio_pin_interrupt_configure_dt()`.

- Archivos principales: `src/ad5940/ad5940_port.c`, `src/ad5940/ad5940.c`, `src/ad5940/ad5940.h`
- Responsabilidad: adaptar la librería de Analog Devices al entorno Zephyr/nRF5340.
- Funciones de portabilidad implementadas:
  - `AD5940_ReadWriteNBytes()`
  - `AD5940_CsClr()` / `AD5940_CsSet()`
  - `AD5940_RstClr()` / `AD5940_RstSet()`
  - `AD5940_Delay10us()`
  - `AD5940_GetMCUIntFlag()` / `AD5940_ClrMCUIntFlag()`
  - `AD5940_MCUResourceInit()`
- Parámetros actuales: SPIM2 a 1 MHz, transferencia de 8 bits, MSB first y CS manual.
- Verificación: el sistema inicializa SPI/GPIO, muestra los pines asignados por UART y puede inicializar el AD5940 sin error.

### Capa 3: Application Logic

Configuración del AD5940 para medición de bioimpedancia, ejecución de barridos de frecuencia y procesamiento de resultados.

- Archivos principales: `src/ad5940/AD5940Main.c`, `src/ad5940/AD5940Main.h`, `src/ad5940/BodyImpedance.c`, `src/ad5940/BodyImpedance.h`
- Configuración actual de medición:
  - Resistencia de calibración: 10 kOhm
  - Sweep habilitado
  - Frecuencia inicial: 4 kHz
  - Frecuencia final: 198 kHz
  - Puntos por sweep: 48
  - ODR BIA: 20
  - Fuente FIFO: DFT
- Datos calculados: frecuencia, magnitud de impedancia en ohmios y fase en grados.
- Verificación: los datos impresos por UART cambian de forma coherente al modificar el contacto de los electrodos o al realizar movimientos del brazo.

### Capa 4: Communication

La comunicación actual de la demo es por USB/UART mediante `printk` y logs de Zephyr. BLE queda fuera del alcance actual y solo se contempla como ampliación futura.

- Archivos principales: `src/ad5940/debug_config.h`, `src/graficas.c`, `src/graficas.h`
- Formato de salida BIA actual:

```text
<frecuencia> Hz <magnitud> Ohm <fase> deg
```

- Formato auxiliar compatible con Teleplot:

```text
>label:valor
```

- Verificación: el PC recibe los datos por terminal serie a 115200 baud y la herramienta de visualización puede representar la señal.

### Capa 5: System Integration

Integración en `main.c`: inicialización de recursos, arranque de la aplicación BIA y mantenimiento del sistema en ejecución.

- Archivo principal: `src/main.c`
- Flujo de arranque:
  1. Esperar 3 s para facilitar la conexión del terminal serie.
  2. Inicializar recursos del AD5940 con `AD5940_MCUResourceInit()`.
  3. Lanzar la aplicación de bioimpedancia con `AD5940_Main()`.
  4. Mantener el sistema activo con un bucle de espera si la medición termina.
- Verificación: el sistema realiza sweeps continuos y no se bloquea durante una prueba prolongada.

## Decisiones de diseño

### DD-001: Port layer Zephyr para la librería AD5940

- **Contexto:** La librería del AD5940 está pensada para varios microcontroladores y requiere funciones de bajo nivel específicas de plataforma.
- **Decisión:** Implementar esas funciones en `src/ad5940/ad5940_port.c` usando APIs estándar de Zephyr.
- **Alternativas consideradas:** Reescribir el driver desde cero o mantener un port de referencia STM32/ADICUP3029.
- **Justificación:** Reutilizar la librería del fabricante reduce riesgo y permite concentrar el esfuerzo en la integración con nRF5340.

### DD-002: CS manual por GPIO

- **Contexto:** El AD5940 necesita temporización cuidadosa de CS, especialmente al despertar de hibernación.
- **Decisión:** Eliminar `cs-gpios` del nodo SPI y controlar CS manualmente desde el port layer.
- **Alternativas consideradas:** Usar el control automático de CS de Zephyr.
- **Justificación:** El control manual permite añadir retardos entre ciclos SPI y tras activar CS.

### DD-003: UART/logs como canal de demo

- **Contexto:** La demo necesita observar datos rápido en PC y el proyecto ya tiene consola UART habilitada.
- **Decisión:** Enviar frecuencia, magnitud y fase por UART/logs y usar una herramienta gráfica externa para visualizar.
- **Alternativas consideradas:** BLE GATT o una aplicación móvil.
- **Justificación:** UART reduce complejidad para la primera demo y facilita depuración en hardware real.

## Mapeo de archivos a capas

| Archivo | Capa | Descripción |
|---------|------|-------------|
| `prj.conf` | Hardware Setup | Configuración Kconfig: SPI, GPIO, UART/logs, FPU y stacks |
| `boards/nrf5340dk_nrf5340_cpuapp.overlay` | Hardware Setup | Pines SPI2 y GPIO del AD5940 |
| `src/main.c` | System Integration | Punto de entrada, inicialización y arranque de BIA |
| `src/ad5940/ad5940_port.c` | Driver / Port Layer | Adaptación Zephyr de SPI, GPIO, reset e interrupción |
| `src/ad5940/ad5940.c` | Driver / Port Layer | Librería base del AD5940 |
| `src/ad5940/BodyImpedance.c` | Application Logic | Aplicación BIA y procesamiento de datos del AFE |
| `src/ad5940/AD5940Main.c` | Application Logic | Configuración de sweep, FIFO, interrupciones y salida de resultados |
| `src/ad5940/debug_config.h` | Communication | Macros de salida por `printk` y parámetros de demo |
| `src/graficas.c` | Communication | Función auxiliar para salida estilo Teleplot |
| `CMakeLists.txt` | System Integration | Lista de fuentes e includes del firmware |
