#include <stdint.h>
#define APPBUFF_SIZE 512
extern uint32_t AppBuff[APPBUFF_SIZE];
int32_t BIAShowResult(uint32_t *pData, uint32_t DataCount);
void AD5940BIAStructInit(void);
void AD5940_Main(void);
