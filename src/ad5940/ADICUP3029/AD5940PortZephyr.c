#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/gpio.h>


/* Define el dispositivo GPIO y el pin CS */
#define SPI4_NODE DT_NODELABEL(spi4)

static const struct gpio_dt_spec ad5940_cs =
    GPIO_DT_SPEC_GET_BY_IDX(SPI4_NODE, cs_gpios, 0);


void AD5940_CsClr(void)
{
    if (!device_is_ready(ad5940_cs.port)) {
        return;
    }
    gpio_pin_set_dt(&ad5940_cs, 1);  /* Pone CS en bajo */
}

void AD5940_CsSet(void)
{
    if (!device_is_ready(ad5940_cs.port)) {
        return;
    }
    gpio_pin_set_dt(&ad5940_cs, 0);  /* Pone CS en alto */
}