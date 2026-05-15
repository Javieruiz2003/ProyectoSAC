# GUI de reconocimiento de movimientos

Esta herramienta lee la salida serie del firmware AD5940 BIA y permite:

- ver magnitud/fase en tiempo real;
- calibrar gestos por persona usando perfiles por frecuencia y calibracion manual;
- reconocer el movimiento actual en modo simple o en modo conjunto;
- guardar capturas CSV;
- proteger con contraseña la grabación de secuencias de movimientos;
- guardar secuencias y volver a imprimirlas desde la lista.

## Formato esperado

El firmware debe imprimir líneas con este formato:

```text
[ID:12] 50000.00 Hz 1234.56 Ohm 12.34 deg
```

Ese formato ya coincide con `BIAShowResult()` en `src/ad5940/AD5940Main.c`.

## Instalación

Desde la raíz del proyecto:

```bash
python -m pip install -r scripts/requirements-gesture-gui.txt
```

`tkinter` viene incluido normalmente con Python en Windows. Si `pyserial` no está instalado, la app sigue arrancando y se puede probar con el modo simulación.

## Ejecución

```bash
python scripts/gesture_gui.py
```

## Uso recomendado

1. Conecta la nRF5340 DK y abre la app.
2. Selecciona el puerto serie y `115200` baudios.
3. Pulsa `Conectar`.
4. Marca los gestos que quieras calibrar y pulsa `Calibrar seleccionados`.
5. La app ira indicando cada paso seleccionado. Por defecto `Flexion brazo` queda desmarcado por ahora. Tambien puedes usar `Iniciar calibracion manual`: eliges un gesto, escribes los segundos de captura y pulsas para empezar; se detiene y guarda automaticamente al terminar ese tiempo. El perfil guarda Reposo como referencia y los movimientos como cambios respecto a Reposo, separados por frecuencia y con picos de movimiento.
6. En cada gesto hay 3 segundos para prepararse y 6 segundos para repetir la accion. Durante la captura, la consola muestra cada muestra de forma ordenada y numerada. Desde `Perfil calibrado` puedes borrar una calibracion especifica.
7. Cuando haya perfil calibrado, la pantalla principal mostrara el movimiento detectado.
8. Usa `Guardar CSV bruto` para guardar capturas y analizarlas despues.
9. Para secuencias, pulsa `Desbloquear / crear contrasena`, luego `Grabar secuencia`, realiza los movimientos y pulsa de nuevo para detener.
10. Guarda la secuencia con nombre y despues podras imprimirla desde la lista.

La app tambien incluye una pestana `Ayuda` con la explicacion de cada apartado.

## Archivos generados

La app crea estos archivos locales:

- `scripts/gesture_data/calibration_profile.json`
- `scripts/gesture_data/gesture_sequences.json`
- `scripts/gesture_data/captures/*.csv`

No contienen datos del firmware salvo las capturas CSV que se guarden explícitamente.
