/**
 * @file    MIKROE_4_20mA_RT_Click.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/MIKROE_4_20mA_RT_Click
 * @version 1.1.0
 * @date    25-07-2022
 *
 * @mainpage An Arduino library for the 4-20 mA R & T Click Boards of MIKROE.
 *
 * @section Introduction
 * Supported:
 *
 *  - 4-20 mA R Click (MIKROE-1387)
 *    - 4-20 mA current loop receiver
 *    - MCP3201 12-bit ADC SPI chip
 *    - max SPI clock 1.6 MHz
 *    - max 100 ksps
 *
 *  - 4-20 mA T Click (MIKROE-1296)
 *    - 4-20 mA current loop transmitter
 *    - MCP4921 12-bit DAC SPI chip
 *    - max SPI clock 20 MHz
 *    - settling time of 4.5 μs
 *
 * Single R Click readings tend to fluctuate a lot. To combat the large
 * fluctuations this library optionally provides an exponential moving average
 * (EMA) applied to the R Click readings. It does not rely on storing an array
 * of data and is hence very memory efficient.
 *
 * It does this by oversampling the R Click readings at a user-supplied
 * interval. Subsequently, it will low-pass filter the readings using a
 * smoothing factor that is calculated from a user-supplied low-pass filter
 * cut-off frequency. Technically, the exponential moving average is a
 * single-pole infinite-impulse response (IIR) filter.
 *
 * See the examples in the examples folder.
 *
 * @section author Author
 * Dennis van Gils (vangils.dennis@gmail.com)
 *
 * @section version Version
 * - https://github.com/Dennis-van-Gils/MIKROE_4_20mA_RT_Click
 * - v1.1.0
 *
 * @section Changelog
 * - v1.1.0 - Fixed SPI settings not getting initialized properly in Arduino IDE
 * - v1.0.0 - Initial release
 *
 * @section license License
 * MIT License. See the LICENSE file for details.
 */

#include "MIKROE_4_20mA_RT_Click.h"

/*******************************************************************************
  T_Click
*******************************************************************************/

/*
From the MCP4921 DAC chip datasheet.

Write command register is 16 bits as follows
upper half:  [~A/B , BUF  , ~GA  , ~SHDN, D11  , D10  , D09  , D08  ]
lower half:  [D07  , D06  , D05  , D04  , D03  , D02  , D01  , D00  ]

bit 15 - ~A/B: DAC_A or DAC_B Select bit
  1 = Write to DAC_A
  0 = Write to DAC_B

bit 14 - BUF: V_REF Input Buffer Control bit
  1 = Buffered
  0 = Unbuffered

bit 13 - ~GA: Output Gain Select bit
  1 = 1x (VOUT = VREF * D/4096)
  0 = 2x (VOUT = 2 * VREF * D/4096)

bit 12 - ~SHDN: Output Power Down Control bit
  1 = Output buffer enabled
      "Active mode operation. VOUT is available."
  0 = Output buffer disabled, Output is high impedance
      "Output amplifiers are shut down. VOUT pin is connected to analog ground
      via 500 kOhm (typical)."

bit 11 to 0 - D11:D00: DAC Data bits
  12 bit number D which sets the output value. Contains a value between 0 and
  4095.

Here:
  bit 15 = 0 -> Write to DAC_B
  bit 14 = 0 -> Unbuffered
  bit 13 = 1 -> 1x gain
  bit 12 = 1 -> Output buffer enabled

  00110000 = 0x30
*/

T_Click::T_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
  CS_pin_ = CS_pin;
  calib_ = calib;
}

void T_Click::set_SPI_clock(uint32_t clk_freq_Hz) { SPI_clock_ = clk_freq_Hz; }

void T_Click::begin() {
  SPI.begin();
  digitalWrite(CS_pin_, HIGH); // Disable the slave SPI device for now
  pinMode(CS_pin_, OUTPUT);
  set_mA(4.0);
}

uint16_t T_Click::mA2bitval(float mA) {
  return (uint16_t)round((mA - calib_.p1_mA) / (calib_.p2_mA - calib_.p1_mA) *
                             (calib_.p2_bitval - calib_.p1_bitval) +
                         calib_.p1_bitval);
}

void T_Click::set_mA(float mA) {
  byte bitval_HI;
  byte bitval_LO;

  // The standard Arduino SPI library handles data of 8 bits long. The value
  // decoding the DAC output is 12 bits, hence transfer in two steps.
  bitval_ = mA2bitval(mA);
  bitval_HI = (bitval_ >> 8) & 0x0F; // 0x0F = b00001111
  bitval_HI |= 0x30;                 // 0x30 = b00110000
  bitval_LO = bitval_;

  SPI.beginTransaction(SPISettings(SPI_clock_, MSBFIRST, SPI_MODE0));
  digitalWrite(CS_pin_, LOW);  // Enable slave device
  SPI.transfer(bitval_HI);     // Transfer high byte
  SPI.transfer(bitval_LO);     // Transfer low byte
  digitalWrite(CS_pin_, HIGH); // Disable slave device
  SPI.endTransaction();
}

uint16_t T_Click::get_last_set_bitval() { return bitval_; }

/*******************************************************************************
  R_Click
*******************************************************************************/

/*
From the MCP3201 ADC chip datasheet. See figure 6.1 on the byte transfers.

The MCP3201 has a strange way of formatting data with 5 bits in the first
byte (data_HI) and the lowest order 7 bits in the second byte (data_LO).
*/

R_Click::R_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
  CS_pin_ = CS_pin;
  calib_ = calib;
}

R_Click::R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
                 uint32_t EMA_interval, float EMA_LP_freq) {
  CS_pin_ = CS_pin;
  calib_ = calib;
  EMA_interval_ = EMA_interval;
  EMA_LP_freq_ =
      EMA_LP_freq * 1e-6f; // Transform [Hz] to [MHz] to reduce computations
}

void R_Click::set_SPI_clock(uint32_t clk_freq_Hz) { SPI_clock_ = clk_freq_Hz; }

void R_Click::begin() {
  SPI.begin();
  digitalWrite(CS_pin_, HIGH); // Disable the slave SPI device for now
  pinMode(CS_pin_, OUTPUT);
}

float R_Click::bitval2mA(float bitval) {
  // NB: Keep input argument of type 'float' to accomodate for a running
  // average that could have been applied to the bit value, hence making it
  // fractional.
  float mA = calib_.p1_mA + (bitval - calib_.p1_bitval) /
                                float(calib_.p2_bitval - calib_.p1_bitval) *
                                (calib_.p2_mA - calib_.p1_mA);
  return (mA > R_CLICK_FAULT_mA ? mA : NAN);
}

uint16_t R_Click::read_bitval() {
  byte data_HI;
  byte data_LO;

  // The standard Arduino SPI library handles data of 8 bits long. The value
  // decoding the ADC input is 12 bits, hence transfer in two steps.
  SPI.beginTransaction(SPISettings(SPI_clock_, MSBFIRST, SPI_MODE0));
  digitalWrite(CS_pin_, LOW);          // Enable slave device
  data_HI = SPI.transfer(0xFF) & 0x1F; // 0x1F = b00011111
  data_LO = SPI.transfer(0xFF);        // 0xFF = b11111111
  digitalWrite(CS_pin_, HIGH);         // Disable slave device
  SPI.endTransaction();

  // Reconstruct bit value
  return (uint16_t)((data_HI << 8) | data_LO) >> 1;
}

float R_Click::read_mA() { return bitval2mA(read_bitval()); }

bool R_Click::poll_EMA() {
  uint32_t now = micros();
  float alpha; // Derived smoothing factor of the exponential moving average

  if ((now - EMA_tick_) >= EMA_interval_) {
    // Enough time has passed -> Acquire a new reading.
    // Calculate the smoothing factor every time because an exact interval time
    // is not garantueed.
    EMA_obtained_interval_ = now - EMA_tick_;
    alpha = 1.f - exp(-float(EMA_obtained_interval_) * EMA_LP_freq_);

    if (EMA_at_startup_) {
      EMA_at_startup_ = false;
      EMA_bitval_ = read_bitval();
    } else {
      EMA_bitval_ += alpha * (read_bitval() - EMA_bitval_);
    }
    EMA_tick_ = now;
    return true;

  } else {
    return false;
  }
}

float R_Click::get_EMA_bitval() { return EMA_bitval_; }

float R_Click::get_EMA_mA() { return bitval2mA(EMA_bitval_); }

uint32_t R_Click::get_EMA_obtained_interval() { return EMA_obtained_interval_; }
