# DETECCIÓN DE MOVIMIENTO UTILIZANDO BIOIMPEDANCIA

Este proyecto implementa un sistema de monitorización de bioimpedancia usando el AD5940BIOZ conectado a una placa nRF5340 DK. Con este análisis se busca detectar movimientos de un brazo y diferenciar cambios en la señal de impedancia. Los datos se envían por UART/logs y se muestran en una herramienta de visualización gráfica.

El firmware configura el AD5940, ejecuta barridos de frecuencia de bioimpedancia y emite muestras con frecuencia, magnitud y fase para su análisis.

## Equipo

| Nombre                      | Rol                  | GitHub            |
|-----------------------------|----------------------|-------------------|
| Rafael Cuadrado Sola        | Programador          | @rafacuadrado     |
| Amadeusz Aparicio           | Programador          | @cyber-embdsys    |
| Javier Ruiz Hurtado         | Programador          | @Javieruiz2003    |
| Francisco Santos Durán      | Programador          | @frasandur1       |

## Requisitos previos

- **nRF Connect SDK** v2.x instalado ([guía de instalación](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/installation.html))
- **VS Code** con la extensión **nRF Connect for VS Code**
- **Nordic nRF5340 DK** (placa de desarrollo)
- **AD5940BIOZ** (placa para medición de bioimpedancia)
- Cable USB para conexión y alimentación de la placa
- Electrodos ECG para medición de bioimpedancia

## Conexiones principales

| Señal | Pin nRF5340 DK | Uso                                    |
|-------|----------------|----------------------------------------|
| SCLK  | P1.15          | Reloj SPI2                             |
| MOSI  | P1.13          | Datos hacia AD5940                     |
| MISO  | P1.14          | Datos desde AD5940                     |
| CS    | P1.12          | Chip select manual, activo bajo        |
| RESET | P0.07          | Reset del AD5940, activo bajo          |
| INT   | P1.04          | Interrupción del AD5940, activo bajo   |


## Compilar y flashear

1. Abrir el proyecto en VS Code con la extensión nRF Connect.

2. Compilar desde la terminal:
   ```bash
   west build -b nrf5340dk/nrf5340/cpuapp
   ```

3. Flashear al dispositivo:
   ```bash
   west flash
   ```

4. Ver logs del serial:
   ```bash
   # Opción 1: nRF Connect Serial Terminal en VS Code
   # Opción 2: desde la terminal
   putty -D /dev/ttyACM0 -b 115200
   ```

## Salida esperada

Durante la ejecución, el firmware imprime datos de bioimpedancia con este formato:

```text
<frecuencia> Hz <magnitud> Ohm <fase> deg
```

Ejemplo:

```text
4000.00 Hz 1234.56 Ohm -12.34 deg
```

Estos datos pueden visualizarse desde una terminal serie o adaptarse a herramientas como Teleplot.

## Estructura del repositorio

```
├── src/              ← Código fuente
├── boards/           ← Devicetree overlays (.overlay)
├── docs/
│   ├── PRD.md        ← Requisitos del proyecto
│   ├── architecture.md ← Diseño del sistema
│   ├── designs/      ← Design docs por bloque
│   ├── verification/ ← Evidencia de pruebas
│   └── WORKFLOW.md   ← Flujo de trabajo del equipo
├── llm-context/      ← Documentación de referencia para IA
├── scripts/          ← Scripts de utilidad
├── prj.conf          ← Configuración Kconfig
├── CMakeLists.txt    ← Build system
└── .github/          ← Templates de PR e issues
```

## Seguridad de uso

Este proyecto es un prototipo académico/técnico y no es un dispositivo médico. Las pruebas con electrodos deben realizarse con el hardware alimentado de forma segura, conexiones revisadas y supervisión del equipo. Los datos obtenidos no deben usarse para diagnóstico clínico.

## Documentación

- [PRD - Requisitos del proyecto](docs/PRD.md)
- [Arquitectura del sistema](docs/architecture.md)
- [Flujo de trabajo](docs/WORKFLOW.md)
- [Uso con nRF Connect for VS Code](docs/nrf-connect-vscode.md)

## Flujo de trabajo

Este proyecto sigue el flujo de trabajo descrito en [docs/WORKFLOW.md](docs/WORKFLOW.md).
Cada bloque de funcionalidad pasa por: **Design Doc** -> **Implementación** -> **Verificación** -> **Pull Request**.
