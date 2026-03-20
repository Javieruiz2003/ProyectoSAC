#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include "ad5940/ad5940.h"

int AD5940Port_Init(void);

int main(void)
{
    uint32_t adiid;
    uint32_t chipid;
    uint32_t test;

    printk("Programa arrancado\n");

    if (AD5940Port_Init() != 0) {
        printk("Error inicializando puerto AD5940\n");
        return 0;
    }

    printk("Puerto AD5940 inicializado\n");

    AD5940_RstClr();
    k_msleep(50);
    AD5940_RstSet();
    k_msleep(50);

    printk("Reset AD5940 hecho\n");

    AD5940_Initialize();

    adiid = AD5940_ReadReg(REG_AFECON_ADIID);
    chipid = AD5940_ReadReg(REG_AFECON_CHIPID);

    printk("ADIID  = 0x%08X\n", adiid);
    printk("CHIPID = 0x%08X\n", chipid);

    test = AD5940_ReadReg(REG_AFE_CALDATLOCK);
    printk("CALDATLOCK antes  = 0x%08X\n", test);

    AD5940_WriteReg(REG_AFE_CALDATLOCK, 0xDE87A5AF);

    test = AD5940_ReadReg(REG_AFE_CALDATLOCK);
    printk("CALDATLOCK despues = 0x%08X\n", test);


    void AD5940_Main2(void);
   

    printf("Prueba");
    AD5940_Main2();




    while (1) {
        k_msleep(2000);
    }

    return 0;
}