# Aplicacion de escritorio

Esta carpeta contiene la nueva aplicacion Python para operar el sistema desde el ordenador. La interfaz esta hecha con `tkinter`, asi que no necesita dependencias externas para arrancar.

## Que incluye

- Acceso en modo normal o administrador.
- Registro y carga de perfiles de usuario.
- Captura de bioimpedancia desde simulacion o por UART.
- Calibracion y almacenamiento local en JSON.
- Control basico del brazo y grabacion de secuencias de comandos.
- Movimiento en tiempo real con mano virtual y replicado del brazo.

## Ejecucion

Desde esta carpeta:

```powershell
python main.py
```

## Sensor por UART

En la pestaña `Sensor` puedes seleccionar:

- Fuente `Simulacion` o `UART`.
- Puerto serie y velocidad.
- Tipo de dato del paquete: `float32` o `uint32`.
- Orden de bytes: `little` o `big`.
- Media de las ultimas `N` muestras para suavizar la lectura.
- Escala independiente para modulo de impedancia y fase, util si el firmware acaba enviando enteros.

La trama esperada es:

```c
struct sensor_sample_t {
    tipo frecuencia;
    tipo modulo_z;
    tipo fase;
};
```

Donde `tipo` puede ser `float32` o `uint32` segun la configuracion elegida en la app.
Con `float32` la muestra ocupa 12 bytes: 4 de frecuencia, 4 de modulo y 4 de fase.

## Estructura

- `sac_gui/models.py`: modelos de dominio y contexto de sesion.
- `sac_gui/storage.py`: persistencia local en `data/app_state.json`.
- `sac_gui/services/`: servicios de sensor y brazo.
- `sac_gui/controller.py`: logica de aplicacion.
- `sac_gui/ui/`: estilos y ventana principal.

El fichero de datos se crea automaticamente en `aplicacion/data/app_state.json` al ejecutar la app por primera vez.
