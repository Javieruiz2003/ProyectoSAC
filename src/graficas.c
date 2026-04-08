#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

/**
 * @brief Genera una representación visual (gráfica de barras horizontal) 
 *        de un conjunto de datos en la consola.
 * 
 * @param data Puntero al arreglo de datos (float).
 * @param size Tamaño del arreglo.
 * @param label Etiqueta para identificar la gráfica.
 */
void graficar_datos_consola(float *data, uint32_t size, const char *label)
{
    const int MAX_WIDTH = 50; // Ancho máximo de la barra en caracteres
    float max_val = 0.0f;

    printk("\n--- Grafica: %s ---\n", label);

    // Encontrar el valor máximo para normalizar la gráfica
    for (uint32_t i = 0; i < size; i++) {
        if (data[i] > max_val) {
            max_val = data[i];
        }
    }

    // Evitar división por cero
    if (max_val == 0) max_val = 1.0f;

    for (uint32_t i = 0; i < size; i++) {
        int bar_length = (int)((data[i] / max_val) * MAX_WIDTH);
        
        printk("[%3d] (%6.2f): ", i, (double)data[i]);
        
        for (int j = 0; j < bar_length; j++) {
            printk("#");
        }
        printk("\n");
    }
    printk("----------------------------\n\n");
}
