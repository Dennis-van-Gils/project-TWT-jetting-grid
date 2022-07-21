/**
 * @file DvG_RT_Click_mA.h
 * @author Dennis P.M. van Gils (vangils.dennis@gmail.com)
 * @link https://github.com/Dennis-van-Gils/
 * @version 1.0
 * @date 2022-07-21
 *
 * @brief A library for the 4-20 mA R & T Click Boards of MIKROE.
 *
 * - 4-20 mA R Click (MIKROE-1387): 4-20 mA current loop receiver
 * - 4-20 mA T Click (MIKROE-1296): 4-20 mA current loop transmitter
 *
 * Both controllers operate over the SPI bus.
 *
 * Single R Click readings tend to fluctuate a lot. To combat the large
 * fluctuations this library also provides oversampling and subsequently
 * low-pass filtering of the R Click readings. The applied low-pass filter is a
 * single-pole infinite-impulse response (IIR) filter, which is very memory
 * efficient.
 *
 * @copyright Copyright (c) 2022
 * @section license License
 *
 * MIT license, all text here must be included in any redistribution.
 * See the LICENSE.txt file for details.
 */

/**
  EXAMPLE 1: R Click usage WITHOUT OVERSAMPLING
  '''
    #include "DvG_RT_Click_mA.h"

    R_Click R_click(5, RT_Click_Calibration{4.03, 19.93, 832, 3999});

    void setup() { R_click.begin(); }

    void loop() { R_click.read_mA(); }
  '''

  EXAMPLE 2: R Click usage WITH OVERSAMPLING
  '''
    #include "DvG_RT_Click_mA.h"

    const uint32_t DAQ_DT = 2; // Desired oversampling interval [ms]
    const float DAQ_LP = 10.;  // Low-pass filter cut-off frequency [Hz]
    R_Click R_click(5, RT_Click_Calibration{4.03, 19.93, 832, 3999}, DAQ_DT,
                    DAQ_LP);

    void setup() { R_click.begin(); }

    void loop() {
      R_click.poll_oversampling();
      R_click.get_LP_mA();
    }
  '''

  EXAMPLE 3: T Click usage
  '''
    #include "DvG_RT_Click_mA.h"

    T_Click T_click(6, RT_Click_Calibration{4.02, 19.99, 800, 3980});

    void setup() { T_click.begin(); }

    void loop() { T_click.set_mA(12.0); }
  '''
*/

#ifndef DVG_RT_CLICK_MA_H_
#define DVG_RT_CLICK_MA_H_

#include <Arduino.h>
#include <SPI.h>

/**
 * Maximum SPI clock frequencies taken from the datasheets:
 * - MCP3201 ADC chip (R Click): 1.6 MHz
 * - MCP4921 DAC chip (T Click): 20 MHz
 * Hence, we fix the default SPI clock to a comfortable 1 MHz for both.
 */
const SPISettings DEFAULT_RT_CLICK_SPI_SETTINGS(1000000, MSBFIRST, SPI_MODE0);

/**
 * Currents less than this value are considered to indicate a fault state, such
 * as a broken wire, a disconnected device or an error happening at the
 * transmitter side. Typical value is 3.8 mA.
 */
const float R_CLICK_FAULT_mA = 3.8;

/*******************************************************************************
  RT_Click_Calibration
*******************************************************************************/

/**
 * @brief Structure to hold the [bitval] to [mA] calibration points of either an
 * R Click or a T Click Board.
 *
 * Will be linearly interpolated. Point 1 should lie somewhere around 4 mA and
 * point 2 around 20 mA. Use a multimeter to calibrate against. A variable
 * resistor of around 4.7 kOhm can be used on the R Click Board to vary the
 * input current over the range 4 to 20 mA.
 *
 * Typical calibration values are around {4.0, 20.0, 800, 3980}.
 *
 * @param 1 Calibration point 1, float [mA]
 * @param 2 Calibration point 2, float [mA]
 * @param 3 Calibration point 1, uint16_t [bitval]
 * @param 4 Calibration point 2, uint16_t [bitval]
 */
struct RT_Click_Calibration {
  float p1_mA;
  float p2_mA;
  uint16_t p1_bitval;
  uint16_t p2_bitval;
};

/*******************************************************************************
  T_Click
*******************************************************************************/

/**
 * @brief Class to manage a MIKROE 4-20 mA T Click Board (MIKROE-1296).
 */
class T_Click {
public:
  /**
   * @brief Construct a new T Click object.
   *
   * @param CS_pin Cable select SPI pin
   * @param calib Structure holding the [bitval] to [mA] calibration parameters
   */
  T_Click(uint8_t CS_pin, const RT_Click_Calibration calib);

  /**
   * @brief Adjust the initially set SPI clock frequency of 1 MHz to another
   * frequency.
   *
   * The maximum SPI clock frequency listed by the datasheet of the MCP4921
   * DAC chip of the T Click Board is 20 MHz.
   *
   * @param clk_freq_Hz The SPI clock frequency in Hz
   */
  void adjust_SPI_clock_frequency(uint32_t clk_freq_Hz);

  /**
   * @brief Start SPI and set up the cable select pin. The output current will
   * be set to 4 mA.
   */
  void begin();

  /**
   * @brief Transform the current [mA] into a bit value given the calibration
   * parameters.
   *
   * @param mA The current in mA
   * @return The bit value
   */
  uint16_t mA2bitval(float mA);

  /**
   * @brief Set the output current of the T Click Board in mA.
   *
   * @param mA The current to output in mA
   */
  void set_mA(float mA);

  /**
   * @brief Return the bit value belonging to the last set current by
   * @ref set_mA().
   *
   * @return The bit value
   */
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

/**
 * @brief Class to manage a MIKROE 4-20 mA R Click Board (MIKROE-1387).
 */
class R_Click {
public:
  /**
   * @brief Construct a new R Click object without oversampling.
   *
   * @param CS_pin Cable select SPI pin
   * @param calib Structure holding the [bitval] to [mA] calibration parameters
   */
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib);

  /**
   * @brief Construct a new R Click object with oversampling.
   *
   * @param CS_pin Cable select SPI pin
   * @param calib Structure holding the [bitval] to [mA] calibration parameters
   * @param DAQ_interval_ms Desired oversampling interval [ms]
   * @param DAQ_LP_filter_Hz Low-pass filter cut-off frequency [Hz]
   */
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
          uint32_t DAQ_interval_ms, float DAQ_LP_filter_Hz);

  /**
   * @brief Adjust the initially set SPI clock frequency of 1 MHz to another
   * frequency.
   *
   * The maximum SPI clock frequency listed by the datasheet of the MCP3201
   * ADC chip of the R Click Board is 1.6 MHz.
   *
   * @param clk_freq_Hz The SPI clock frequency in Hz
   */
  void adjust_SPI_clock_frequency(uint32_t clk_freq_Hz);

  /**
   * @brief Start SPI and set up the cable select pin.
   */
  void begin();

  /**
   * @brief Transform the bit value into a current [mA] given the calibration
   * parameters.
   *
   * Currents less than 3.8 mA are considered to indicate a fault state, such as
   * a broken wire, a disconnected device or an error happening at the
   * transmitter side. In that case the return value will be NAN.
   *
   * @param bitval The bit value to transform
   *
   * @return The current in mA, or NAN when the device is in a fault state
   */
  float bitval2mA(float bitval);

  /**
   * @brief Read out the R Click once and return the bit value.
   *
   * @return The bit value
   */
  uint16_t read_bitval();

  /**
   * @brief Read out the R Click once and return the current in mA.
   *
   * Currents less than 3.8 mA are considered to indicate a fault state, such as
   * a broken wire, a disconnected device or an error happening at the
   * transmitter side. In that case the return value will be NAN.
   *
   * @return The current in mA, or NAN when the device is in a fault state
   */
  float read_mA();

  /**
   * @brief This method should be called frequently inside the main loop to
   * allow for oversampling and subsequent low-pass filtering of the R Click
   * readings.
   *
   * @return True when a new sample has been read and added to the filter.
   * Otherwise false, because it was not yet time to read out a new sample.
   *
   * @note Args @ref DAQ_interval_ms and @ref DAQ_LP_filter_Hz must have been
   * passed to the constructor.
   */
  bool poll_oversampling();

  /**
   * @brief Return the currently known oversampled and low-pass filtered R Click
   * reading in bit value.
   *
   * @return The fractional bit value
   *
   * @note Args @ref DAQ_interval_ms and @ref DAQ_LP_filter_Hz must have been
   * passed to the constructor and @ref poll_oversampling() must be repeatedly
   * called.
   */
  float get_LP_bitval();

  /**
   * @brief Return the currently known oversampled and low-pass filtered R Click
   * reading in mA.
   *
   * @return The current in mA, or NAN when the device is in a fault state. See
   * @ref read_mA() for more details on the fault state.
   *
   * @note Args @ref DAQ_interval_ms and @ref DAQ_LP_filter_Hz must have
   * been passed to the constructor and @ref poll_oversampling() must be
   * repeatedly called.
   */
  float get_LP_mA();

  /**
   * @brief Return the last obtained interval of the oversampled R Click
   * readings in microseconds.
   *
   * @return The interval in microseconds
   */
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
