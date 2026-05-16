#include "ad5940.h"
#include <stdio.h>
#include <math.h>
#include <stdbool.h>
#include "BodyImpedance.h"

#define APPBUFF_SIZE 512
#define PRINT_DIV    1   /* Imprimir 1 de cada N muestras */

/* ===================== CONFIG GLOBAL ===================== */
#define DEFAULT_SWEEP_POINTS     5
#define DEFAULT_NUM_REPETITIONS  1

float cfgRcalVal = 10000.0f;

/* Cambia esto segun lo que quieras */
int32_t cfgNumOfData = -1;
/* -1 = tiempo real continuo */
/* DEFAULT_NUM_REPETITIONS * DEFAULT_SWEEP_POINTS = barrido finito */

bool cfgSweepEn = true;
float cfgSweepStart = 4000.0f;
float cfgSweepStop  = 198000.0f;
uint32_t cfgSweepPoints = DEFAULT_SWEEP_POINTS;
uint8_t cfgNumRepetitions = DEFAULT_NUM_REPETITIONS;

/* ===================== OTROS PARAMETROS ===================== */
#define CFG_BIA_ODR         200.0f
#define CFG_FIFO_THRESH     4
#define CFG_DFT_NUM         DFTNUM_4096
#define CFG_SINC3_OSR       ADCSINC3OSR_2
#define CFG_SWEEP_LOG       bFALSE

uint32_t AppBuff[APPBUFF_SIZE];

static uint32_t sample_id = 0;
static uint32_t print_div_counter = 0;
static uint8_t chip_info_printed = 0;

/* ===================== PRINT ===================== */
int32_t BIAShowResult(uint32_t *pData, uint32_t DataCount)
{
  float freq;
  fImpPol_Type *pImp = (fImpPol_Type*)pData;

  AppBIACtrl(BIACTRL_GETFREQ, &freq);

  for(uint32_t i = 0; i < DataCount; i++)
  {
    print_div_counter++;

    if(print_div_counter >= PRINT_DIV)
    {
      print_div_counter = 0;

      float phase_deg = pImp[i].Phase * 180.0f / MATH_PI;

      if(phase_deg > 180.0f)
        phase_deg -= 360.0f;

      printf("[ID:%u] %.2f Hz %.2f Ohm %.2f deg\n",
             sample_id++,
             (double)freq,
             (double)pImp[i].Magnitude,
             (double)phase_deg);
    }
  }

  return 0;
}

/* ===================== CONFIG HARDWARE ===================== */
void AD5940PlatformCfg(void)
{
  CLKCfg_Type clk_cfg;
  FIFOCfg_Type fifo_cfg;
  AGPIOCfg_Type gpio_cfg;

  AD5940_HWReset();
  AD5940_Initialize();

  /* ID del chip solo una vez */
  if(!chip_info_printed)
  {
    uint32_t adiid  = AD5940_ReadReg(REG_AFECON_ADIID);
    uint32_t chipid = AD5940_ReadReg(REG_AFECON_CHIPID);

    printf("=== AD5940 INIT ===\n");
    printf("ADIID  = 0x%08X\n", adiid);
    printf("CHIPID = 0x%08X\n", chipid);

    chip_info_printed = 1;
  }

  /* CLOCK */
  clk_cfg.ADCClkDiv = ADCCLKDIV_1;
  clk_cfg.ADCCLkSrc = ADCCLKSRC_HFOSC;
  clk_cfg.SysClkDiv = SYSCLKDIV_1;
  clk_cfg.SysClkSrc = SYSCLKSRC_HFOSC;
  clk_cfg.HfOSC32MHzMode = bTRUE;
  clk_cfg.HFOSCEn = bTRUE;
  clk_cfg.HFXTALEn = bFALSE;
  clk_cfg.LFOSCEn = bTRUE;
  AD5940_CLKCfg(&clk_cfg);

  /* FIFO */
  fifo_cfg.FIFOEn = bFALSE;
  fifo_cfg.FIFOMode = FIFOMODE_FIFO;
  fifo_cfg.FIFOSize = FIFOSIZE_4KB;
  fifo_cfg.FIFOSrc = FIFOSRC_DFT;
  fifo_cfg.FIFOThresh = CFG_FIFO_THRESH;
  AD5940_FIFOCfg(&fifo_cfg);

  fifo_cfg.FIFOEn = bTRUE;
  AD5940_FIFOCfg(&fifo_cfg);

  /* INTERRUPTS */
  AD5940_INTCCfg(AFEINTC_1, AFEINTSRC_ALLINT, bTRUE);
  AD5940_INTCCfg(AFEINTC_0, AFEINTSRC_DATAFIFOTHRESH, bTRUE);
  AD5940_INTCClrFlag(AFEINTSRC_ALLINT);

  /* GPIO */
  gpio_cfg.FuncSet = GP6_SYNC | GP5_SYNC | GP4_SYNC | GP2_TRIG | GP1_SYNC | GP0_INT;
  gpio_cfg.InputEnSet = AGPIO_Pin2;
  gpio_cfg.OutputEnSet = AGPIO_Pin0 | AGPIO_Pin1 | AGPIO_Pin4 | AGPIO_Pin5 | AGPIO_Pin6;
  gpio_cfg.OutVal = 0;
  gpio_cfg.PullEnSet = 0;
  AD5940_AGPIOCfg(&gpio_cfg);

  AD5940_SleepKeyCtrlS(SLPKEY_UNLOCK);
}

/* ===================== CONFIG BIA ===================== */
void AD5940BIAStructInit(void)
{
  AppBIACfg_Type *pBIACfg;

  AppBIAGetCfg(&pBIACfg);

  pBIACfg->SeqStartAddr = 0;
  pBIACfg->MaxSeqLen = 512;

  pBIACfg->RcalVal = cfgRcalVal;
  pBIACfg->DftNum = CFG_DFT_NUM;

  /* CLAVE */
  pBIACfg->NumOfData = cfgNumOfData;

  pBIACfg->BiaODR = CFG_BIA_ODR;
  pBIACfg->FifoThresh = CFG_FIFO_THRESH;
  pBIACfg->ADCSinc3Osr = CFG_SINC3_OSR;

  /* BARRIDO */
  pBIACfg->SweepCfg.SweepEn = cfgSweepEn ? bTRUE : bFALSE;
  pBIACfg->SweepCfg.SweepStart = cfgSweepStart;
  pBIACfg->SweepCfg.SweepStop = cfgSweepStop;
  pBIACfg->SweepCfg.SweepPoints = cfgSweepPoints;
  pBIACfg->SweepCfg.SweepLog = CFG_SWEEP_LOG;
  pBIACfg->SweepCfg.SweepIndex = 0;

  pBIACfg->SinFreq = cfgSweepStart;
}

/* ===================== MAIN ===================== */
void AD5940_Main(void)
{
  uint32_t temp;

  AD5940PlatformCfg();
  AD5940BIAStructInit();

  AppBIAInit(AppBuff, APPBUFF_SIZE);
  AppBIACtrl(BIACTRL_START, 0);

  while(1)
  {
    if(AD5940_GetMCUIntFlag())
    {
      AD5940_ClrMCUIntFlag();

      temp = APPBUFF_SIZE;
      AppBIAISR(AppBuff, &temp);

      if(temp > 0)
      {
        BIAShowResult(AppBuff, temp);
      }
    }
  }
}
