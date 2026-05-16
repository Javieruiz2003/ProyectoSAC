# Uso con nRF Connect for VS Code

Este repositorio esta configurado como una aplicacion Zephyr/nRF Connect.

## Abrir la aplicacion

1. Abre la carpeta `ProyectoSAC` en Visual Studio Code.
2. Abre la extension `nRF Connect` desde la barra lateral.
3. En `Applications` debe aparecer esta carpeta como aplicacion.
4. Si la extension pide SDK o toolchain, selecciona la version instalada desde Toolchain Manager.

## Crear configuracion de build

Desde la extension:

1. Pulsa `Add Build Configuration`.
2. Selecciona la placa:

```text
nrf5340dk/nrf5340/cpuapp
```

3. Deja la ruta de la aplicacion como la raiz del proyecto.
4. Compila con `Build`.
5. Carga en la placa con `Flash`.

## Terminal serie

Para ver las muestras del firmware:

1. Abre `Serial Terminal` desde la extension.
2. Selecciona el puerto de la nRF5340 DK.
3. Usa `115200` baudios.

El programa debe imprimir lineas como:

```text
[ID:0] 4000.00 Hz 1234.56 Ohm -12.34 deg
```

Ese formato es el que lee la GUI de `scripts/gesture_gui.py`.

## Configuracion incluida

El archivo `.vscode/settings.json` registra esta carpeta como aplicacion:

```json
{
  "nrf-connect.applications": [
    "${workspaceFolder}"
  ],
  "C_Cpp.default.configurationProvider": "nrf-connect"
}
```
