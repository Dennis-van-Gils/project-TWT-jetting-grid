/**
 * @file    MIKROE_4_20mA_RT_Click.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @brief   An Arduino library for the 4-20 mA R & T Click Boards of MIKROE.
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef MIKROE_4_20mA_RT_CLICK_H_
#define MIKROE_4_20mA_RT_CLICK_H_

#include <Arduino.h>
#include <SPI.h>

/**
 * @brief Default SPI clock frequency in Hz for the R and T Click Boards
 *
 * Maximum SPI clock frequencies taken from the datasheets:
 * - MCP3201 ADC chip (R Click): 1.6 MHz
 * - MCP4921 DAC chip (T Click): 20 MHz
 *
 * Hence, we fix the default SPI clock to a comfortable 1 MHz for both.
 */
const uint32_t DEFAULT_RT_CLICK_SPI_CLOCK = 1000000;

/**
 * @brief Current threshold in mA below which to indicate a fault state in the R
 * Click reading. The reading will be set to NAN in that case.
 *
 * A fault state can occur due to a broken current loop, a disconnected device
 * or an error happening at the transmitter side. Typical value is 3.8 mA.
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
 */
struct RT_Click_Calibration {
  float p1_mA;        /**< @brief Calibration point 1 in [mA] */
  float p2_mA;        /**< @brief Calibration point 2 in [mA] */
  uint16_t p1_bitval; /**< @brief Calibration point 1 in [bitval] */
  uint16_t p2_bitval; /**< @brief Calibration point 2 in [bitval] */
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
  void set_SPI_clock(uint32_t clk_freq_Hz);

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
  uint32_t SPI_clock_ = DEFAULT_RT_CLICK_SPI_CLOCK; // SPI clock frequency [Hz]
  uint8_t CS_pin_;                                  // Cable select pin
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
   * @brief Construct a new R Click object.
   *
   * Methods @ref read_bitval() and @ref read_mA() can be used to get the
   * instanteneous R Click reading.
   *
   * @param CS_pin Cable select SPI pin
   * @param calib Structure holding the [bitval] to [mA] calibration parameters
   */
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib);

  /**
   * @brief Construct a new R Click object that uses an exponential moving
   * average (EMA) on the R Click readings.
   *
   * It does this by oversampling the R Click readings at a desired interval
   * given by @p EMA_interval. Subsequently, it will low-pass filter the
   * readings using a smoothing factor that is calculated from the low-pass
   * filter cut-off frequency given by @p EMA_LP_freq.
   *
   * Method @ref poll_EMA() should be repeatedly called in the main loop,
   * ideally at a faster pace than the desired oversampling interval.
   *
   * Methods @ref get_EMA_bitval() and @ref get_EMA_mA() can be used to get the
   * moving average value.
   *
   * @param CS_pin Cable select SPI pin
   * @param calib Structure holding the [bitval] to [mA] calibration parameters
   * @param EMA_interval Desired oversampling interval [µs]
   * @param EMA_LP_freq Low-pass filter cut-off frequency [Hz]
   */
  R_Click(uint8_t CS_pin, const RT_Click_Calibration calib,
          uint32_t EMA_interval, float EMA_LP_freq);

  /**
   * @brief Adjust the initially set SPI clock frequency of 1 MHz to another
   * frequency.
   *
   * The maximum SPI clock frequency listed by the datasheet of the MCP3201
   * ADC chip of the R Click Board is 1.6 MHz.
   *
   * @param clk_freq_Hz The SPI clock frequency in Hz
   */
  void set_SPI_clock(uint32_t clk_freq_Hz);

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
   * @return The current in mA, or NAN when the device is in a fault state. See
   * @ref bitval2mA() for more details on the fault state.
   */
  float read_mA();

  /**
   * @brief This method is crucial for the exponential moving average (EMA) to
   * work correctly. It should be repeatedly called in the main loop, ideally at
   * a faster pace than the given oversampling interval @p EMA_interval.
   *
   * @return True when a new sample has been read and added to the moving
   * average. False otherwise, because it was not yet time to read out a new
   * sample.
   *
   * @note Parameters @p EMA_interval and @p EMA_LP_freq must have been passed
   * to the @ref R_Click() constructor.
   */
  bool poll_EMA();

  /**
   * @brief Return the exponential moving average value of the R Click readings
   * in bit value.
   *
   * @return The fractional bit value
   *
   * @note Parameters @p EMA_interval and @p EMA_LP_freq must have been passed
   * to the @ref R_Click() constructor and @ref poll_EMA() must have been
   * repeatedly called.
   */
  float get_EMA_bitval();

  /**
   * @brief Return the exponential moving average value of the R Click readings
   * in mA.
   *
   * @return The current in mA, or NAN when the device is in a fault state. See
   * @ref bitval2mA() for more details on the fault state.
   *
   * @note Parameters @p EMA_interval and @p EMA_LP_freq must have been passed
   * to the @ref R_Click() constructor and @ref poll_EMA() must have been
   * repeatedly called.
   */
  float get_EMA_mA();

  /**
   * @brief Return the last obtained interval of the oversampled R Click
   * readings of the exponential moving average in microseconds.
   *
   * @return The interval in microseconds
   */
  uint32_t get_EMA_obtained_interval();

private:
  uint32_t SPI_clock_ = DEFAULT_RT_CLICK_SPI_CLOCK; // SPI clock frequency [Hz]
  uint8_t CS_pin_;                                  // Cable select pin
  RT_Click_Calibration calib_; // Calibration parameters [bitval] to [mA]

  // Optional exponential moving average (EMA)
  uint32_t EMA_interval_ = 2000;   // Desired oversampling interval [µs]
  float EMA_LP_freq_ = 10e-6;      // Low-pass filter cut-off frequency [MHz]
  float EMA_bitval_ = NAN;         // EMA output value [fractional bitval]
  bool EMA_at_startup_ = true;     // Are we at startup?
  uint32_t EMA_tick_ = micros();   // Time of last oversampled reading [µs]
  uint32_t EMA_obtained_interval_; // Last obtained oversampling interval [µs]
};

#endif
