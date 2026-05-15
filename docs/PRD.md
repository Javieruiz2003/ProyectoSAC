# Product Requirements Document (PRD)

## Objetivo del proyecto

Este proyecto implementa un sistema de detección de movimiento del brazo mediante mediciones de bioimpedancia. Para ello se usa el AFE AD5940BIOZ conectado a la placa nRF5340 DK, que toma muestras eléctricas a través de electrodos ECG y permite observar cómo cambia la impedancia del tejido durante distintos movimientos.

El sistema debe inicializar el hardware, configurar el AD5940, realizar mediciones periódicas de bioimpedancia, procesar los datos obtenidos y mostrar la señal en una interfaz gráfica o herramienta de visualización serie. El objetivo final es disponer de una demo capaz de capturar datos reales, representarlos de forma clara y diferenciar estados o movimientos básicos del brazo.

El proyecto está dirigido al equipo de desarrollo y evaluación del prototipo, con foco en una demostración funcional sobre hardware real usando nRF Connect SDK, Zephyr RTOS y la placa nRF5340 DK.

## Requisitos Funcionales

| ID     | Requisito                                                                          | Prioridad | Capa               |
|--------|------------------------------------------------------------------------------------|-----------|--------------------|
| RF-001 | Configurar SPI2 y GPIO para comunicar el nRF5340 DK con el AD5940BIOZ              | Alta      | Hardware Setup     |
| RF-002 | Inicializar el AD5940 y verificar su presencia leyendo un identificador o registro | Alta      | Driver / Port Layer |
| RF-003 | Ejecutar mediciones periódicas de bioimpedancia usando la librería del AD5940      | Alta      | Application Logic  |
| RF-004 | Calcular magnitud y/o fase de la impedancia a partir de las muestras capturadas    | Alta      | Application Logic  |
| RF-005 | Enviar los datos medidos por UART/logs en un formato compatible con visualización  | Alta      | Communication      |
| RF-006 | Mostrar la evolución de la señal de bioimpedancia en una interfaz gráfica          | Media     | Communication      |
| RF-007 | Detectar variaciones de la señal asociadas a movimientos básicos del brazo         | Media     | Application Logic  |
| RF-008 | Registrar mensajes de error cuando falle la inicialización, lectura o comunicación | Media     | System Integration |
| RF-009 | Mantener un bucle principal estable tras finalizar o pausar una medición           | Baja      | System Integration |
| RF-010 | Permitir ajustar parámetros de medición como rango de frecuencia y puntos del sweep | Baja      | Application Logic  |

<!--
Capas válidas: Hardware Setup, Driver / Port Layer, Application Logic, Communication, System Integration.
Prioridades: Alta (debe funcionar para la demo), Media (mejora significativa), Baja (nice-to-have).
Usar verbos concretos: leer, escribir, transmitir, calcular, configurar, mostrar.
-->

## Requisitos No Funcionales

| ID      | Requisito                                                                 | Categoría       |
|---------|---------------------------------------------------------------------------|-----------------|
| RNF-001 | El sistema debe iniciar la primera medición en menos de 5 s tras arrancar | Rendimiento     |
| RNF-002 | El firmware debe compilar sin errores para `nrf5340dk/nrf5340/cpuapp`     | Mantenibilidad  |
| RNF-003 | Los datos enviados por UART deben mantener un formato estable y parseable | Mantenibilidad  |
| RNF-004 | El sistema debe funcionar durante al menos 10 minutos sin bloqueos        | Fiabilidad      |
| RNF-005 | Los fallos de comunicación con el AD5940 deben quedar visibles en logs    | Fiabilidad      |
| RNF-006 | El código específico de portabilidad del AD5940 debe estar separado de la lógica de aplicación |Mantenibilidad |
| RNF-007 | Las mediciones deben realizarse con electrodos y conexión segura para el usuario de prueba | Seguridad |

<!--
Categorías comunes: Rendimiento, Energía, Fiabilidad, Mantenibilidad, Seguridad.
-->

## Restricciones

- Hardware: nRF5340 DK, AD5940BIOZ y electrodos ECG
- SDK: nRF Connect SDK v2.x / Zephyr RTOS
- Comunicación con sensor: SPI2 y GPIO para CS, RESET e interrupción
- Salida de datos: UART/logs serie para depuración y visualización
- Pines actuales: SCLK P1.15, MOSI P1.13, MISO P1.14, CS P1.12, RESET P0.07, INT P1.04
- Configuración de demo actual: sweep de 4 kHz a 198 kHz con 48 puntos
- Formato de salida principal: `<frecuencia> Hz <magnitud> Ohm <fase> deg`
- La demo debe ejecutarse en la CPU de aplicación del nRF5340 DK

## Criterios de aceptación

<!-- ¿Cómo sabemos que el proyecto está "terminado"? Listar condiciones verificables. -->

- [ ] El firmware compila correctamente con `west build -b nrf5340dk/nrf5340/cpuapp`
- [ ] El sistema inicializa SPI, GPIO y el AD5940 sin errores visibles en logs
- [ ] El sistema lee datos de bioimpedancia del AD5940 correctamente (verificado con logs)
- [ ] Los datos se emiten por UART/logs en formato compatible con la herramienta de visualización
- [ ] La interfaz gráfica muestra la evolución de la señal de bioimpedancia
- [ ] Se observa una variación medible entre reposo y al menos un movimiento del brazo
- [ ] La prueba se realiza con electrodos colocados de forma estable y sin condiciones inseguras para el usuario
- [ ] El sistema funciona de forma continua durante al menos 10 minutos sin errores

## Fuera de alcance

<!-- ¿Qué NO va a hacer este proyecto? Esto evita scope creep. -->

- Implementar una aplicación móvil final para usuarios no técnicos
- Realizar diagnóstico médico o clasificación clínica de patologías
- Diseñar una placa electrónica propia distinta de la nRF5340 DK y AD5940BIOZ
- Transmitir datos por BLE, salvo que se apruebe como ampliación futura
- Entrenar un modelo avanzado de machine learning para clasificación de movimientos
