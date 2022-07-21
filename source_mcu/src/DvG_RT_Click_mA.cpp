/**
 * @file DvG_RT_Click_mA.cpp
 */

#include "DvG_RT_Click_mA.h"

/*******************************************************************************
  T_Click
*******************************************************************************/

/*
Additional notes from John Cabrer, wildseyed@gmail.com

According to other code examples for PIC, the 4-20 mA T click takes values from
~ 800 to ~ 4095 for the current control. The four most significant bits are for
control, and should be 0011 where:

bit 15
  1 = Ignore this command
  0 = Write to DAC register

bit 14 - BUF: VREF Input Buffer Control bit
  1 = Buffered
  0 = Unbuffered

bit 13 - GA: Output Gain Selection bit
  1 = 1x (VOUT = VREF * D/4096)
  0 = 2x (VOUT = 2 * VREF * D/4096)

bit 12 - SHDN: Output Shutdown Control bit
  1 = Active mode operation. VOUT is available.
  0 = Shutdown the device. Analog output is not available. VOUT pin is
      connected to 500 kOhm (typical)

bits 11 to 0 - D11:D0: DAC Input Data bits. Bit x is ignored
*/

T_Click::T_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
  CS_pin_ = CS_pin;
  calib_ = calib;
}

void T_Click::adjust_SPI_clock_frequency(uint32_t clk_freq_Hz) {
  SPI_settings_ = SPISettings(clk_freq_Hz, MSBFIRST, SPI_MODE0);
}

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

  // The standard Arduino SPI library handles data of 8 bits long.
  // The MIKROE T Click shield is 12 bits, hence transfer in two steps.
  bitval_ = mA2bitval(mA);
  bitval_HI = (bitval_ >> 8) & 0x0F; // 0x0F = 15
  bitval_HI |= 0x30;                 // 0x30 = 48
  bitval_LO = bitval_;

  SPI.beginTransaction(SPI_settings_);
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

R_Click::R_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
  CS_pin_ = CS_pin;
  calib_ = calib;
}

R_Click::R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
                 uint32_t DAQ_interval_ms, float DAQ_LP_filter_Hz) {
  CS_pin_ = CS_pin;
  calib_ = calib;
  DAQ_interval_ms_ = DAQ_interval_ms;
  DAQ_LP_filter_Hz_ = DAQ_LP_filter_Hz;
}

void R_Click::adjust_SPI_clock_frequency(uint32_t clk_freq_Hz) {
  SPI_settings_ = SPISettings(clk_freq_Hz, MSBFIRST, SPI_MODE0);
}

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

  // The standard Arduino SPI library handles data of 8 bits long
  // The MIKROE R Click shield is 12 bits, hence transfer in two steps
  SPI.beginTransaction(SPI_settings_);
  digitalWrite(CS_pin_, LOW); // Enable slave device
  data_HI = SPI.transfer(0xFF) & 0x1F;
  data_LO = SPI.transfer(0xFF);
  digitalWrite(CS_pin_, HIGH); // Disable slave device
  SPI.endTransaction();

  // Reconstruct bit value
  return (uint16_t)((data_HI << 8) | data_LO) >> 1;
}

float R_Click::read_mA() { return bitval2mA(read_bitval()); }

bool R_Click::poll_oversampling() {
  uint32_t now = micros();
  float alpha; // Derived smoothing factor of the IIR filter

  if ((now - DAQ_tick_) >= DAQ_interval_ms_ * 1e3) {
    // Enough time has passed -> Acquire a new reading.
    // Calculate the smoothing factor every time because an exact DAQ interval
    // time is not garantueed.
    DAQ_obtained_DT_ = now - DAQ_tick_;
    alpha = 1.0f - exp(-float(DAQ_obtained_DT_) * 1e-6f * DAQ_LP_filter_Hz_);

    if (DAQ_at_startup_) {
      DAQ_LP_value_ = read_bitval();
      DAQ_at_startup_ = false;
    } else {
      DAQ_LP_value_ += alpha * (read_bitval() - DAQ_LP_value_);
    }
    DAQ_tick_ = now;
    return true;

  } else {
    return false;
  }
}

float R_Click::get_oversampled_bitval() { return DAQ_LP_value_; }

float R_Click::get_oversampled_mA() { return bitval2mA(DAQ_LP_value_); }

uint32_t R_Click::get_last_obtained_DAQ_DT() { return DAQ_obtained_DT_; }
