#include <zephyr/drivers/uart.h>
#include "ad5940/ad5940.h"
#include "ad5940/BodyImpedance.h"

extern AppBIACfg_Type *pCfg;
extern const struct device *uart;
extern uint32_t bufferLectura[512];

int main(void);
