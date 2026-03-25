#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/printk.h>
#include "ad5940.h"

#define SPI_NODE   DT_NODELABEL(spi4)
#define GPIO0_NODE DT_NODELABEL(gpio0)
#define GPIO1_NODE DT_NODELABEL(gpio1)

#if !DT_NODE_EXISTS(SPI_NODE)
#error "El nodo spi4 no existe en devicetree"
#endif

#if !DT_NODE_HAS_STATUS(SPI_NODE, okay)
#error "El nodo spi4 existe pero no está en estado okay"
#endif

static const struct device *spi_dev   = DEVICE_DT_GET(SPI_NODE);
static const struct device *gpio0_dev = DEVICE_DT_GET(GPIO0_NODE);
static const struct device *gpio1_dev = DEVICE_DT_GET(GPIO1_NODE);

static const struct spi_config spi_cfg = {
    .frequency = 1000000,
    .operation = SPI_OP_MODE_MASTER | SPI_WORD_SET(8) | SPI_TRANSFER_MSB,
    .slave = 0,
};

#define AD5940_CS_PIN   12   /* P1.12 */
#define AD5940_RST_PIN   7   /* P0.07 */

void AD5940_CsClr(void)
{
    gpio_pin_set(gpio1_dev, AD5940_CS_PIN, 0);
}

void AD5940_CsSet(void)
{
    gpio_pin_set(gpio1_dev, AD5940_CS_PIN, 1);
}

void AD5940_RstClr(void)
{
    gpio_pin_set(gpio0_dev, AD5940_RST_PIN, 0);
}

void AD5940_RstSet(void)
{
    gpio_pin_set(gpio0_dev, AD5940_RST_PIN, 1);
}

void AD5940_Delay10us(uint32_t time)
{
    k_busy_wait(time * 10);
}

void AD5940_ReadWriteNBytes(unsigned char *pSendBuffer,
                            unsigned char *pRecvBuff,
                            unsigned long length)
{
    int ret;

    struct spi_buf tx_buf = {
        .buf = pSendBuffer,
        .len = length,
    };

    struct spi_buf_set tx = {
        .buffers = &tx_buf,
        .count = 1,
    };

    struct spi_buf rx_buf = {
        .buf = pRecvBuff,
        .len = length,
    };

    struct spi_buf_set rx = {
        .buffers = &rx_buf,
        .count = 1,
    };

    if (pSendBuffer && pRecvBuff) {
        ret = spi_transceive(spi_dev, &spi_cfg, &tx, &rx);
    } else if (pSendBuffer) {
        ret = spi_write(spi_dev, &spi_cfg, &tx);
    } else if (pRecvBuff) {
        ret = spi_read(spi_dev, &spi_cfg, &rx);
    } else {
        printk("AD5940_ReadWriteNBytes: buffers NULL\n");
        return;
    }

    if (ret) {
        printk("spi error = %d, len = %lu\n", ret, length);
    }
}

int AD5940Port_Init(void)
{
    if (!device_is_ready(spi_dev)) {
        printk("SPI2 no lista\n");
        return -1;
    }

    if (!device_is_ready(gpio0_dev)) {
        printk("GPIO0 no lista\n");
        return -1;
    }

    if (!device_is_ready(gpio1_dev)) {
        printk("GPIO1 no lista\n");
        return -1;
    }

    gpio_pin_configure(gpio1_dev, AD5940_CS_PIN, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio0_dev, AD5940_RST_PIN, GPIO_OUTPUT_HIGH);

    return 0;
}

uint32_t AD5940_ClrMCUIntFlag(void)
{
    return 0;
}

uint32_t AD5940_GetMCUIntFlag(void)
{
    return 0;
}