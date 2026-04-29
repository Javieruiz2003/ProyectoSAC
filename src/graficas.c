#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include "graficas.h" // Incluye su propia cabecera

void graficar_datos_teleplot(float *data, uint32_t size, const char *label)
{
    for (uint32_t i = 0; i < size; i++) {
        printk(">%s:%f\n", label, (double)data[i]);
        k_sleep(K_MSEC(1));
    }
}