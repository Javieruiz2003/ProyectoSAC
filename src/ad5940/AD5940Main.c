/*!
 *****************************************************************************
 @file:    AD5940Main.c
 @author:  $Author: nxu2 $
 @brief:   Used to control specific application and futhur process data.
 @version: $Revision: 766 $
 @date:    $Date: 2017-08-21 14:09:35 +0100 (Mon, 21 Aug 2017) $
 -----------------------------------------------------------------------------

Copyright (c) 2017-2019 Analog Devices, Inc. All Rights Reserved.

This software is proprietary to Analog Devices, Inc. and its licensors.
By using this software you agree to the terms of the associated
Analog Devices Software License Agreement.

*****************************************************************************/
/**
 * @addtogroup AD5940_System_Examples
 * @{
 *  @defgroup BioElec_Example
 *  @{
  */

#include "ad5940.h"
#include <stdio.h>
#include <zephyr/kernel.h>
#include "BodyImpedance.h"
#include "AD5940Main.h"

#define APPBUFF_SIZE 512
uint32_t AppBuff[APPBUFF_SIZE];
extern uint8_t BIAend;

/* Config parameters AD5940 */
float cfgRcalVal = 10000;
int32_t cfgNumOfData = DEFAULT_NUM_REPETITIONS * DEFAULT_SWEEP_POINTS;
bool cfgSweepEn = true;
float cfgSweepStart = 4000;
float cfgSweepStop = 198000;
uint32_t cfgSweepPoints = DEFAULT_SWEEP_POINTS;
uint8_t cfgNumRepetitions = DEFAULT_NUM_REPETITIONS;

/* Buffer global para almacenar los puntos de medicion */
MeasurementPoint g_measurement_buffer[DEFAULT_SWEEP_POINTS];
uint8_t g_measurement_count = 0;
static bool g_measurement_complete = false;

/* It's your choice here how to do with the data. Here is just an example to print them to UART */
int32_t BIAShowResult(uint32_t *pData, uint32_t DataCount)
{
  float freq;
  float bi_result[3] = {0, 0, 0};

  fImpPol_Type *pImp = (fImpPol_Type*)pData;
  AppBIACtrl(BIACTRL_GETFREQ, &freq);

  bi_result[0] = freq;
  bi_result[1] = pImp[0].Magnitude;
  bi_result[2] = pImp[0].Phase * 180 / MATH_PI;

  DEBUG_PRINT("%.2f Hz %.2f Ohm %.2f deg\n",
              (double)bi_result[0], (double)bi_result[1], (double)bi_result[2]);

  /* Store point in global buffer */
  if (g_measurement_count < DEFAULT_SWEEP_POINTS) {
    g_measurement_buffer[g_measurement_count].frequency = freq;
    g_measurement_buffer[g_measurement_count].magnitude = pImp[0].Magnitude;
    g_measurement_buffer[g_measurement_count].phase = pImp[0].Phase * 180 / MATH_PI;
    g_measurement_count++;

    if (g_measurement_count >= cfgSweepPoints) {
      DEBUG_PRINT("\n=== MEASUREMENT COMPLETE: All %d points collected ===\n",
                  (int)cfgSweepPoints);
      g_measurement_complete = true;

      /* Reset for next measurement */
      g_measurement_count = 0;
      g_measurement_complete = false;
    }
  }

  return 0;
}

/* Initialize AD5940 basic blocks like clock */
void AD5940PlatformCfg(void)
{
  CLKCfg_Type clk_cfg;
  FIFOCfg_Type fifo_cfg;
  AGPIOCfg_Type gpio_cfg;

  /* Use hardware reset */
  AD5940_HWReset();
  AD5940_Delay10us(2000);  /* 20ms after reset */
  AD5940_Initialize();
  /* Step1. Configure clock */
  clk_cfg.ADCClkDiv = ADCCLKDIV_1;
  clk_cfg.ADCCLkSrc = ADCCLKSRC_HFOSC;
  clk_cfg.SysClkDiv = SYSCLKDIV_1;
  clk_cfg.SysClkSrc = SYSCLKSRC_HFOSC;
  clk_cfg.HfOSC32MHzMode = bFALSE;
  clk_cfg.HFOSCEn = bTRUE;
  clk_cfg.HFXTALEn = bFALSE;
  clk_cfg.LFOSCEn = bTRUE;
  AD5940_CLKCfg(&clk_cfg);
  /* Step2. Configure FIFO and Sequencer*/
  fifo_cfg.FIFOEn = bFALSE;
  fifo_cfg.FIFOMode = FIFOMODE_FIFO;
  fifo_cfg.FIFOSize = FIFOSIZE_4KB;
  fifo_cfg.FIFOSrc = FIFOSRC_DFT;
  fifo_cfg.FIFOThresh = 4;
  AD5940_FIFOCfg(&fifo_cfg);
  fifo_cfg.FIFOEn = bTRUE;
  AD5940_FIFOCfg(&fifo_cfg);

  /* Step3. Interrupt controller */
  AD5940_INTCCfg(AFEINTC_1, AFEINTSRC_ALLINT, bTRUE);
  AD5940_INTCCfg(AFEINTC_0, AFEINTSRC_DATAFIFOTHRESH, bTRUE);
  AD5940_INTCClrFlag(AFEINTSRC_ALLINT);
  /* Step4: Reconfigure GPIO */
  gpio_cfg.FuncSet = GP6_SYNC|GP5_SYNC|GP4_SYNC|GP2_TRIG|GP1_SYNC|GP0_INT;
  gpio_cfg.InputEnSet = AGPIO_Pin2;
  gpio_cfg.OutputEnSet = AGPIO_Pin0|AGPIO_Pin1|AGPIO_Pin4|AGPIO_Pin5|AGPIO_Pin6;
  gpio_cfg.OutVal = 0;
  gpio_cfg.PullEnSet = 0;

  AD5940_AGPIOCfg(&gpio_cfg);
}

/* !!Change the application parameters here if you want to change it to none-default value */
void AD5940BIAStructInit(void)
{
  static bool first_time = 1;
  AppBIACfg_Type *pBIACfg;

  AppBIAGetCfg(&pBIACfg);

  pBIACfg->SeqStartAddr = 0;
  pBIACfg->MaxSeqLen = 512;

  pBIACfg->RcalVal = cfgRcalVal;
  pBIACfg->DftNum = DFTNUM_8192;
  pBIACfg->NumOfData = cfgNumOfData;
  pBIACfg->BiaODR = 20;
  pBIACfg->FifoThresh = 4;
  pBIACfg->ADCSinc3Osr = ADCSINC3OSR_2;

  pBIACfg->SweepCfg.SweepEn = cfgSweepEn;
  pBIACfg->SweepCfg.SweepStart = cfgSweepStart;
  pBIACfg->SweepCfg.SweepStop = cfgSweepStop;
  pBIACfg->SweepCfg.SweepPoints = cfgSweepPoints;
  pBIACfg->SweepCfg.SweepLog = bTRUE;

  if (first_time) {
    pBIACfg->SweepCfg.SweepIndex = 0;
    first_time = 0;
  }
}


void AD5940_Main(void)
{
  uint32_t temp;

  BIAend = 0;

  AD5940PlatformCfg();
  AD5940BIAStructInit();
  AppBIAInit(AppBuff, APPBUFF_SIZE);
  AppBIACtrl(BIACTRL_START, 0);
  AD5940_ClrMCUIntFlag();

  while (!BIAend) {
    if (AD5940_GetMCUIntFlag()) {
      AD5940_ClrMCUIntFlag();
      temp = APPBUFF_SIZE;
      AppBIAISR(AppBuff, &temp);
      if (temp > 0) {
        BIAShowResult(AppBuff, temp);
      }
    }
    k_usleep(100);
  }
  BIAend = 0;
  DEBUG_PRINT("\n=== AD5940 MEASUREMENT COMPLETE ===\n");
  AD5940_ShutDownS();
  DEBUG_PRINT("AD5940 shutdown - chip in hibernation\n");
}

/**
 * @}
 * @}
 * */