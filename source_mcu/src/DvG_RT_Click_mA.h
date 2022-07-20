/*
  DvG_RT_Click_mA.h

  A library for the 4-20 mA current loop controllers of MIKROE:
    - 4-20 mA R click (MIKROE-1387, receiver)
    - 4-20 mA T click (MIKROE-1296, transmitter)

  Both controllers operate over the SPI bus.

  Single R click readings tend to fluctuate a lot. To combat the large
  fluctuations this library also allows for oversampling and subsequently
  low-pass filtering the R click readings. The applied low-pass filter is a
  single-pole infinite-impulse response (IIR) filter, which is very memory
  efficient.

  Dennis van Gils
  20-07-2022



  TODO:
    x) Apply vscode recommendations
      "recommendations": [
          "platformio.platformio-ide",
          "ms-vscode.cpptools",
          "xaver.clang-format"
      ],

    x) Format docstrings like
         https://developer.lsst.io/cpp/api-docs.html
         https://www.doxygen.nl/manual/commands.html



  EXAMPLE 1: R click usage WITHOUT OVERSAMPLING
    '''
    #include "DvG_RT_Click_mA.h"

    R_Click R_click(5, RT_Click_Calibration{4.03, 19.93, 832, 3999});

    void setup() {
      R_click.begin();
    }

    void loop() {
      R_click.read_mA();
    }
    '''

  EXAMPLE 2: R click usage WITH OVERSAMPLING
    '''
    #include "DvG_RT_Click_mA.h"

    const uint32_t DAQ_DT = 2; // Desired oversampling interval [ms]
    const float DAQ_LP = 10.;  // Low-pass filter cut-off frequency [Hz]
    R_Click R_click(5, RT_Click_Calibration{4.03, 19.93, 832, 3999},
                    DAQ_DT, DAQ_LP);

    void setup() {
      R_click.begin();
    }

    void loop() {
      R_click.poll_oversampling();
      R_click.get_LP_mA();
    }
    '''

  EXAMPLE 3: T click usage
    '''
    #include "DvG_RT_Click_mA.h"

    T_Click T_click(6, RT_Click_Calibration{4.02, 19.99, 800, 3980});

    void setup() {
      T_click.begin();
    }

    void loop() {
      T_click.set_mA(12.0);
    }
    '''
*/

#ifndef DVG_RT_CLICK_MA_H_
#define DVG_RT_CLICK_MA_H_

#include <Arduino.h>
#include <SPI.h>

// Maximum SPI clock frequencies taken from the datasheets:
// - MCP3201 ADC chip (R click): 1.6 MHz
// - MCP4921 DAC chip (T click): 20 MHz
// Hence, we fix the default SPI clock to a comfortable 1 MHz for both.
const SPISettings DEFAULT_RT_CLICK_SPI_SETTINGS(1000000, MSBFIRST, SPI_MODE0);

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
// Typical calibration values: {4.0, 20.0, 800, 3980}
struct RT_Click_Calibration {
  float p1_mA;        // Calibration point 1 [mA]
  float p2_mA;        // Calibration point 2 [mA]
  uint16_t p1_bitval; // Calibration point 1 [bitval]
  uint16_t p2_bitval; // Calibration point 2 [bitval]
};

/*******************************************************************************
  T_Click
*******************************************************************************/

class T_Click {
public:
  // Constructor
  //   CS_pin: Cable select SPI pin to the T click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  T_Click(uint8_t CS_pin, const RT_Click_Calibration calib);

  // Adjust the initially set SPI clock frequency of 1 MHz to another frequency.
  // The maximum SPI clock frequency reported by the datasheet of the MCP4921
  // DAC chip (T click) is 20 MHz.
  void adjust_SPI_clock_frequency(uint32_t clk_freq_Hz);

  // Start SPI and set up the cable select SPI pin. The output is set to 4 mA.
  void begin();

  // Transform the current [mA] into a bit value given the calibration params.
  uint16_t mA2bitval(float mA);

  // Set the output current [mA]
  void set_mA(float mA_value);

  // Return the bit value belonging to the last set current
  uint16_t get_last_set_bitval();

private:
  SPISettings SPI_settings_ = DEFAULT_RT_CLICK_SPI_SETTINGS;
  uint8_t CS_pin_;             // Cable select pin
  RT_Click_Calibration calib_; // Calibration parameters [bitval] to [mA]
  uint16_t bitval_;            // Last set bit value
};

/*******************************************************************************
  R_Click
*******************************************************************************/

// Constructor description goes here
class R_Click {
public:
  // Constructor
  // Params:
  //   CS_pin: Cable select SPI pin to the R click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib);

  // Constructor
  // Params:
  //   CS_pin: Cable select SPI pin to the R click board
  //   calib : Structure containing the [bitval] to [mA] calibration parameters
  //   DAQ_interval_ms : Desired oversampling interval [ms]
  //   DAQ_LP_filter_Hz: Low-pass filter cut-off frequency [Hz]
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
          uint32_t DAQ_interval_ms, float DAQ_LP_filter_Hz);

  // Adjust the initially set SPI clock frequency of 1 MHz to another frequency.
  // The maximum SPI clock frequency reported by the datasheet of the MCP3201
  // ADC chip (R click) is 1.6 MHz.
  void adjust_SPI_clock_frequency(uint32_t clk_freq_Hz);

  // Start SPI and set up the cable select SPI pin
  void begin();

  // Transform the bit value into a current [mA] given the calibration params.
  // Currents less than 3.8 mA are considered to signal a fault state, such as
  // a broken wire or a disconnected device. In that case the return value will
  // be NAN.

  /**
   * \brief Transform the bit value into a current [mA] given the calibration
   * params.
   *
   * Currents less than 3.8 mA are considered to signal a fault state, such as
   * a broken wire or a disconnected device. In that case the return value will
   * be NAN.
   *
   * \param bitval the bit value to transform into a current [mA]
   * \return The current in mA, or NAN when the device is in a fault state.
   *
   */
  float bitval2mA(float bitval);

  // Read out the R click once and return the bit value
  uint16_t read_bitval();

  // Read out the R click once and return the current in [mA], unless the R
  // click is in a fault state (e.g, a broken wire or disconnected device) in
  // which case the return value will be NAN.
  float read_mA();

  // This method should be called frequently inside the main loop to allow for
  // oversampling and subsequent low-pass filtering of the R click readings.
  // Returns true when a new sample has been read out and added to the filter.
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set
  // in the constructor.
  bool poll_oversampling();

  // Return the current low-pass filter output value of the oversampled R click
  // readings as [bitval].
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set
  // in the constructor and `poll_oversampling()` must be repeatedly called.
  float get_LP_bitval();

  // Return the current low-pass filter output value of the oversampled R click
  // readings as [mA], unless the R click is in a fault state (e.g, a broken
  // wire or disconnected device) in which case the return value will be NAN.
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set
  // in the constructor and `poll_oversampling()` must be repeatedly called.
  float get_LP_mA();

  // Return the last obtained interval of the oversampled R click readings in
  // [us].
  // NOTE: Params `DAQ_interval_ms` and `DAQ_LP_filter_Hz` must have been set in
  // the constructor and `poll_oversampling()` must be repeatedly called.
  uint32_t get_last_obtained_DAQ_DT();

private:
  SPISettings SPI_settings_ = DEFAULT_RT_CLICK_SPI_SETTINGS;
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
};

#endif
