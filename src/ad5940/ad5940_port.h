#include <stdint.h>

void AD5940_CsClr(void);
void AD5940_CsSet(void);
void AD5940_RstClr(void);
void AD5940_RstSet(void);
void AD5940_Delay10us(uint32_t time);
void AD5940_ReadWriteNBytes(unsigned char *pSendBuffer,
							unsigned char *pRecvBuff,
							unsigned long length);
int AD5940Port_Init(void);
uint32_t AD5940_ClrMCUIntFlag(void);
uint32_t AD5940_GetMCUIntFlag(void);


