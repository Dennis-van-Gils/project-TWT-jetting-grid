/*
DvG_RT_click_mA

A library for the 4-20 mA current controllers of MIKROE:
  - 4-20 mA R click (receiver)
  - 4-20 mA T click (transmitter)

Both controllers operate over the SPI bus. Maximal SPI clock frequency for
MCP3204 (R click) and MCP3201 (T click) running at 3.3V is 1 MHz.

Single R click readings tend to fluctuate a lot. To combat the large
fluctuations this library also allows for oversampling and subsequently low-pass
filtering the R click readings. The applied low-pass filter is a single-pole
infinite-impulse response (IIR) filter, which is very memory efficient.

EXAMPLE 1: R click usage WITHOUT OVERSAMPLING
  '''
  #include "DvG_RT_Click_mA.h"

  R_Click R_click(6, RT_Click_Calibration{3.99, 20.00, 791, 3971});

  void setup() {
    R_click.begin();
  }

  void loop() {
    R_click.read_mA();
  }
  '''

EXAMPLE 2: R click usage WITH OVERSAMPLING
  '''
  include "DvG_RT_Click_mA.h"

  const uint32_t DAQ_DT = 2; // Desired oversampling interval [ms]
  const float DAQ_LP = 2.;   // Low-pass filter cut-off frequency [Hz]
  R_Click R_click(6, RT_Click_Calibration{3.99, 20.00, 791, 3971},
                  DAQ_DT, DAQ_LP);

  void setup() {
    R_click.begin();
  }

  void loop() {
    R_click.poll_oversampling();
    R_click.get_LP_mA();
  }
  '''

Dennis van Gils, 19-07-2022
*/

#ifndef DVG_RT_CLICK_MA_H_
#define DVG_RT_CLICK_MA_H_

#include <Arduino.h>
#include <SPI.h>

// Maximal SPI clock frequency for the MCP3201 ADC chip (R click) and MCP4921
// DAC chip (T click) running at 3.3V is 1 MHz
const SPISettings RT_CLICK_SPI(1000000, MSBFIRST, SPI_MODE0);

// Junk byte
const byte RT_CLICK_JUNK = 0xFF;

// Currents less than this value are considered to signal a fault state, such as
// a broken wire or a disconnected device. Typical value is 3.8 mA.
const float R_CLICK_FAULT_mA = 3.8;

/*******************************************************************************
  RT_Click_Calibration
*******************************************************************************/

// Structure to hold the [bitval] to [mA] calibration points of R and T click
// boards. Will be linearly interpolated. Point 1 should lie somewhere around
// 4 mA and point 2 around 20 mA.
//   param 1: Calibration point 1, float [mA]
//   param 2: Calibration point 2, float [mA]
//   param 3: Calibration point 1, uint16_t [bitval]
//   param 4: Calibration point 2, uint16_t [bitval]
struct RT_Click_Calibration {
  float p1_mA;        // Calibration point 1 [mA]
  float p2_mA;        // Calibration point 2 [mA]
  uint16_t p1_bitval; // Calibration point 1 [bitval]
  uint16_t p2_bitval; // Calibration point 2 [bitval]
};

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

class T_Click {
private:
  uint8_t CS_pin_;             // Cable select pin
  RT_Click_Calibration calib_; // Calibration parameters [bitval] to [mA]
  uint16_t set_bitval_;        // Last set bit value

public:
  // Constructor
  //   CS_pin: Cable select SPI pin to the T click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  T_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
    CS_pin_ = CS_pin;
    calib_ = calib;
  }

  // Start SPI and set up the cable select SPI pin
  void begin() {
    SPI.begin();
    digitalWrite(CS_pin_, HIGH); // Disable the slave SPI device for now
    pinMode(CS_pin_, OUTPUT);

    // Force output to 4 mA at the start
    set_mA(4.0);
  }

  // Set the output current [mA]
  void set_mA(float mA_value) {
    uint16_t bitval;
    byte bitval_HI;
    byte bitval_LO;

    // Transform current [mA] to [bitval]
    bitval =
        (int)round((mA_value - calib_.p1_mA) / (calib_.p2_mA - calib_.p1_mA) *
                       (calib_.p2_bitval - calib_.p1_bitval) +
                   calib_.p1_bitval);
    set_bitval_ = bitval;

    // The standard Arduino SPI library handles data of 8 bits long.
    // The MIKROE T Click shield is 12 bits, hence transfer in two steps.
    bitval_HI = (bitval >> 8) & 0x0F; // 0x0F = 15
    bitval_HI |= 0x30;                // 0x30 = 48
    bitval_LO = bitval;

    SPI.beginTransaction(RT_CLICK_SPI);
    digitalWrite(CS_pin_, LOW);  // Enable slave device
    SPI.transfer(bitval_HI);     // Transfer high byte
    SPI.transfer(bitval_LO);     // Transfer low byte
    digitalWrite(CS_pin_, HIGH); // Disable slave device
    SPI.endTransaction();
  }

  // Return the bit value belonging to the last set current
  uint16_t get_last_set_bitval() { return set_bitval_; }
};

/*******************************************************************************
  R_Click
*******************************************************************************/

class R_Click {
private:
  uint8_t CS_pin_;             // Cable select pin
  RT_Click_Calibration calib_; // Calibration parameters [bitval] to [mA]

  // Optional data-acquistion (DAQ) using oversampling and low-pass (LP)
  // filtering
  uint32_t DAQ_interval_ms_ = 10; // Desired oversampling interval [ms]
  float DAQ_LP_filter_Hz_ = 1.;   // Low-pass filter cut-off frequency [Hz]
  float DAQ_LP_value_ = NAN;      // Filter output value
  bool DAQ_at_startup_ = true;    // Are we at startup?
  uint32_t DAQ_tick_ = micros();  // Time of last oversampled reading [us]
  uint32_t DAQ_obtained_DT_;      // Last obtained oversampling interval [us]

public:
  // Constructor
  // Params:
  //   CS_pin: Cable select SPI pin to the R click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib) {
    CS_pin_ = CS_pin;
    calib_ = calib;
  }

  // Constructor
  // Params:
  //   CS_pin: Cable select SPI pin to the R click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  //   DAQ_interval_ms : Desired oversampling interval [ms]
  //   DAQ_LP_filter_Hz: Low-pass filter cut-off frequency [Hz]
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
          uint32_t DAQ_interval_ms, float DAQ_LP_filter_Hz) {
    CS_pin_ = CS_pin;
    calib_ = calib;
    DAQ_interval_ms_ = DAQ_interval_ms;
    DAQ_LP_filter_Hz_ = DAQ_LP_filter_Hz;
  }

  // Start SPI and set up the cable select SPI pin
  void begin() {
    SPI.begin();
    digitalWrite(CS_pin_, HIGH); // Disable the slave SPI device for now
    pinMode(CS_pin_, OUTPUT);
  }

  // Transform the bit value into a current [mA] given the calibration params.
  // Currents less than 3.8 mA are considered to signal a fault state, such as
  // a broken wire or a disconnected device. In that case the return value will
  // be NAN.
  float bitval2mA(float bitval) {
    // NB: Keep input argument of type 'float' to accomodate for a running
    // average that could have been applied to the bit value, hence making it
    // fractional.
    float mA = calib_.p1_mA + (bitval - calib_.p1_bitval) /
                                  float(calib_.p2_bitval - calib_.p1_bitval) *
                                  (calib_.p2_mA - calib_.p1_mA);
    return (mA > R_CLICK_FAULT_mA ? mA : NAN);
  }

  // Read out the R click once and return the bit value
  uint32_t read_bitval() {
    byte data_HI;
    byte data_LO;

    // The standard Arduino SPI library handles data of 8 bits long
    // The MIKROE R Click shield is 12 bits, hence transfer in two steps
    SPI.beginTransaction(RT_CLICK_SPI);
    digitalWrite(CS_pin_, LOW); // Enable slave device
    data_HI = SPI.transfer(RT_CLICK_JUNK) & 0x1F;
    data_LO = SPI.transfer(RT_CLICK_JUNK);
    digitalWrite(CS_pin_, HIGH); // Disable slave device
    SPI.endTransaction();

    // Reconstruct bit value
    return (uint32_t)((data_HI << 8) | data_LO) >> 1;
  }

  // Read out the R click once and return the current in [mA], unless the R
  // click is in a fault state (e.g, a broken wire or disconnected device) in
  // which case the return value will be NAN.
  float read_mA() { return bitval2mA(R_Click::read_bitval()); }

  // This method should be called frequently inside the main loop to allow for
  // oversampling and subsequent low-pass filtering of the R click readings.
  // Returns true when a new sample has been read out and added to the filter.
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set in
  // the constructor.
  bool poll_oversampling() {
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

  // Return the current low-pass filter output value of the oversampled R click
  // readings as [bitval].
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set in
  // the constructor and `poll_oversampling()` must be repeatedly called.
  float get_LP_bitval() { return DAQ_LP_value_; }

  // Return the current low-pass filter output value of the oversampled R click
  // readings as [mA], unless the R click is in a fault state (e.g, a broken
  // wire or disconnected device) in which case the return value will be NAN.
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set in
  // the constructor and `poll_oversampling()` must be repeatedly called.
  float get_LP_mA() { return bitval2mA(DAQ_LP_value_); }

  // Return the last obtained interval of the oversampled R click readings in
  // [us].
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set in
  // the constructor and `poll_oversampling()` must be repeatedly called.
  uint32_t get_last_obtained_DAQ_DT() { return DAQ_obtained_DT_; }
};

#endif
