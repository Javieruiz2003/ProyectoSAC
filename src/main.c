#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include "ad5940/ad5940.h"
#include "ad5940/BodyImpedance.h"

int AD5940Port_Init(void);

int main(void)
{
    printk("Inicio BIA\n");

    if (AD5940Port_Init() != 0) {
        printk("Error puerto\n");
        return 0;
    }

    AD5940_RstClr();
    k_msleep(50);
    AD5940_RstSet();
    k_msleep(50);

    printk("Reset hecho\n");

    AD5940_Initialize();

    printk("Inicializando BIA...\n");

    AppBIACfg_Type *pBIACfg;
    AppBIAGetCfg(&pBIACfg);

    AppBIAInit(0, 0);

    printk("BIA listo\n");

    while (1) {
        AppBIACtrl(BIACTRL_START, 0);
        k_msleep(1000);
    }

    return 0;
}