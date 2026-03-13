#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/gpio.h>
#include "ad5940/AD5940.h"


#define AD5940_NODE DT_NODELABEL(ad5940)

#if !DT_NODE_HAS_STATUS(AD5940_NODE, okay)
#error "No se encontró el nodo ad5940 en app.overlay"
#endif

static const struct spi_dt_spec ad5940_spi =
    SPI_DT_SPEC_GET(AD5940_NODE,
                    SPI_WORD_SET(8) | SPI_TRANSFER_MSB,
                    0);

int main(void)
{
    printk("Programa arrancado\n");

    if (!spi_is_ready_dt(&ad5940_spi)) {
        printk("SPI no está lista\n");
        return 0;
    }else {
        printk("SPI lista correctamente\n");
    }

    

    while (1) {
        printk("Loop OK\n");
        k_msleep(2000);
    }

    return 0;
}
