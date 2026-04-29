#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/random/random.h> // CORREGIDO
#include <math.h> // Para funciones matemáticas como sinf()
#include "graficas.h" // CORREGIDO: Incluye el .h, NO el .c

#define DATA_SIZE 100

int main(void)
{
    float datos_impedancia[DATA_SIZE];
    float fase = 0.0f;

    printk("Iniciando test de Teleplot en nRF5340...\n");
    k_sleep(K_MSEC(5000)); // Pausa para abrir Teleplot en el PC

    while (1) {
        // 1. Generar datos de prueba (Simulamos una impedancia que oscila)
        for (int i = 0; i < DATA_SIZE; i++) {
            // Base de 150 Ohm + oscilación de 50 Ohm + pequeño ruido aleatorio
            float ruido = (float)(sys_rand32_get() % 100) / 50.0f; 
            datos_impedancia[i] = 150.0f + (50.0f * sinf(fase + (float)i * 0.1f)) + ruido;
        }

        // 2. Enviar el bloque de datos a Teleplot
        graficar_datos_teleplot(datos_impedancia, DATA_SIZE, "Impedancia_Prueba");

        // 3. Actualizar fase para que la siguiente gráfica sea distinta
        fase += 0.5f;

        printk("Bloque enviado. Esperando 2 segundos...\n");
        k_sleep(K_MSEC(2000));
    }

    return 0;
}