#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/gpio.h>


/* Define el dispositivo GPIO y el pin CS */
#define SPI4_NODE DT_NODELABEL(spi4)

static const struct gpio_dt_spec ad5940_cs =
    GPIO_DT_SPEC_GET_BY_IDX(SPI4_NODE, cs_gpios, 0);

static const struct device *rst= DEVICE_DT_GET(DT_NODELABEL(reset));
void AD5940_CsClrZephyr(void)
{
    if (!device_is_ready(ad5940_cs.port)) {
        return;
    }
    gpio_pin_set_dt(&ad5940_cs, 1);  /* Pone CS en bajo */
}

void AD5940_CsSetZephyr(void)
{
    if (!device_is_ready(ad5940_cs.port)) {
        return;
    }
    gpio_pin_set_dt(&ad5940_cs, 0);  /* Pone CS en alto */
}
void AD5940_RstSet(void)
{
    if (!device_is_ready(rst)) {
        return;
    }
    gpio_pin_set_dt(&rst, 1);  /* Pone RST en alto */
}
void AD5940_RstReset(void)
{
    if (!device_is_ready(rst)) {
        return;
    }
    gpio_pin_set_dt(&rst, 1);  /* Pone RST en alto */
}