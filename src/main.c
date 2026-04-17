#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include "ad5940.h"
#include "AD5940Main.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

int main(void)
{
	/* Delay to allow serial connection before output */
	k_msleep(3000);
	printf("\n\n=== AD5940 BIA app v56-hibernate-wake ===\n");

	printf("Calling MCUResourceInit...\n");
	if (AD5940_MCUResourceInit() != 0) {
		printf("ERROR: MCU resource init failed\n");
		return -1;
	}
	printf("MCUResourceInit done, calling AD5940_Main...\n");

	AD5940_Main();

	LOG_INF("Measurement done, entering idle loop");
	while (1) {
		k_msleep(1000);
	}

	return 0;
}
