/**
 * @file    ProtocolManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    11-04-2023
 *
 * @brief   Provides classes `P`, `Line`, `PackedLine` and `ProtocolManager`,
 * needed for reading in and playing back a protocol program for the jetting
 * grid of the Twente Water Tunnel.
 *
 * @section Abbrevations
 * - PCS: Protocol Coordinate System
 * - P  : Point in the PCS
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef PROTOCOL_MANAGER_H_
#define PROTOCOL_MANAGER_H_

#include "CentipedeManager.h"
#include "FastLED.h"
#include "constants.h"

#include <Arduino.h>
#include <array>

// See `main.cpp`
extern const uint8_t BUF_LEN; // Common character buffer for string formatting
extern char buf[];            // Common character buffer for string formatting
extern CRGB leds[256];        // LED matrix
extern const bool DEBUG;      // Print debug info over serial?
extern const bool NO_PERIPHERALS; // Allows developing code on a bare Arduino
                                  // without sensors & actuators attached

/**
 * @brief The maximum number of protocol lines that a protocol program can
 * contain. Make it as large as free RAM allows.
 */
const uint16_t PROTOCOL_MAX_LINES = 5000;

/**
 * @brief The maximum number of PCS points that a single protocol line can
 * contain.
 *
 * Technically, the maximum number should equal the total number of valid valve
 * locations, so equal to `N_VALVES`. However, we deliberately make it able to
 * hold the full PCS space for array-indexing safety.
 */
const uint16_t MAX_POINTS_PER_LINE = NUMEL_PCS_AXIS * NUMEL_PCS_AXIS;

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

/**
 * @brief Special value denoting an uninitialized point in the PCS.
 *
 * Also used as a sentinel to signal the end of a @p PointsArray.
 */
const int8_t P_NULL_VAL = -128;

/**
 * @brief Class to hold a single point in the PCS.
 *
 * Default initialization value is `{P_NULL_VAL, P_NULL_VAL}`.
 */
class P {
public:
  P(int8_t x_ = P_NULL_VAL, int8_t y_ = P_NULL_VAL) : x(x_), y(y_) {}

  inline void set(int8_t x_, int8_t y_) {
    x = x_;
    y = y_;
  }

  inline void set_null() {
    x = P_NULL_VAL;
    y = P_NULL_VAL;
  }

  inline bool is_null() const {
    return ((x == P_NULL_VAL) || (y == P_NULL_VAL));
  }

  /**
   * @brief Pack the PCS point into a single byte.
   *
   * The upper 4 bits decode the PCS x-coordinate.
   * The lower 4 bits decode the PCS y-coordinate.
   *
   * @return The byte-encoded PCS point
   */
  inline uint8_t pack_into_byte() {
    return (uint8_t)((x - PCS_X_MIN) << 4) | //
           (uint8_t)((y - PCS_Y_MIN) & 0xF);
  }

  /**
   * @brief Unpack the packed PCS point and store it.
   *
   * The upper 4 bits decode the PCS x-coordinate.
   * The lower 4 bits decode the PCS y-coordinate.
   *
   * @param c The byte-encoded PCS point
   */
  inline void unpack_byte(uint8_t c) {
    x = (c >> 4) + PCS_X_MIN;
    y = (c & 0xF) + PCS_Y_MIN;
  }

  /**
   * @brief Pretty print the PCS point as "(x, y)", useful for debugging.
   */
  void print();

  // Public members
  int8_t x; // x-coordinate
  int8_t y; // y-coordinate
};

/*------------------------------------------------------------------------------
  PointsArray
------------------------------------------------------------------------------*/

/**
 * @brief List of PCS points (objects of class `P`).
 *
 * The coordinates of each point `P` should correspond to a valve that needs to
 * be turned open. All unmentioned valves will remain/be set closed. The maximum
 * number of points must not exceed `MAX_POINTS_PER_LINE`.
 *
 * After the last point a sentinel must be placed to indicate the end of the
 * list. This end sentinel takes the form of a special value for `P`, namely
 * `P{P_NULL_VAL, P_NULL_VAL}`. You can also call the method `set_null()` on the
 * `P` object.
 *
 * https://cplusplus.com/reference/array/array/array:
 * An `std::array` for elements of a class type calls their default constructor.
 *
 * Hence, the default initialization here is an array full with special valued
 * `P` objects: `P{P_NULL_VAL, P_NULL_VAL}`.
 */
using PointsArray = std::array<P, MAX_POINTS_PER_LINE + 1>;
// +1 for the end sentinel

/*------------------------------------------------------------------------------
  Line
------------------------------------------------------------------------------*/

// Forward declaration
class PackedLine;

/**
 * @brief Class to manage a duration-timed list of PCS points, corresponding to
 * valves that need to be turned open all at once for the specified duration.
 *
 * See @p PointsArray for more details.
 */
class Line {
public:
  Line() {}
  Line(uint16_t duration_, PointsArray points_)
      : duration(duration_), points(points_) {}

  /**
   * @brief Pack the list of PCS points into 16-bit bitmasks.
   *
   * @param output Reference to a `PackedLine` to pack into.
   */
  void pack_into(PackedLine &output) const;

  /**
   * @brief Pretty print the list of PCS points.
   */
  void print();

  // Public members
  uint16_t duration;  // Time duration in [ms]
  PointsArray points; // List of PCS points
};

/*------------------------------------------------------------------------------
  PackedLine
------------------------------------------------------------------------------*/

/**
 * @brief Class to manage a packed version of a @p Line object.
 *
 * Packing a `Line` means that the full list of PCS points that make up that
 * line will get encoded into 16-bit bitmasks, one for each PCS row.
 *
 * Benefit to packing is the constant array dimension and less memory footprint
 * than using `Line` when using a large number of points `P`. This allows for
 * more lines that make up a protocol program to be stored into memory.
 *
 * https://cplusplus.com/reference/array/array/array:
 * An `std::array` for elements of fundamental types are left uninitialized,
 * unless the array object has static storage, in which case they are zero-
 * initialized.
 *
 * Hence, the default initialization here is zero-initialized only when declared
 * non-local.
 */
class PackedLine {
public:
  PackedLine() {}

  /**
   * @brief Unpack the bitmasks into a list of PCS points.
   *
   * @param output Reference to a `Line` to unpack into.
   */
  void unpack_into(Line &output) const;

  // Public members
  uint16_t duration; // Time duration in [ms]

  // List of PCS points packed into bitmasks
  std::array<uint16_t, NUMEL_PCS_AXIS> masks;
};

/*------------------------------------------------------------------------------
  Program
------------------------------------------------------------------------------*/

/**
 * @brief The protocol program fully stored in memory.
 *
 * It is an array containing timed protocol lines, each line containing the
 * valves to be opened for the time duration as specified. Each protocol line
 * is actually packed into a bitmask to save on memory. Method @p unpack_into()
 * must be called on the @p PackedLine object to get the list of PCS points
 * (which we then loop over in @p main.cpp to 1: finally open the referred
 * valves and close the others and 2: to light up the appropiate LEDs of the
 * 16x16 LED matrix).
 */
using Program = std::array<PackedLine, PROTOCOL_MAX_LINES>;

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

/**
 * @brief Class to manage reading in and playing back a protocol program. Only
 * one protocol program can be in memory at a time.
 */
class ProtocolManager {
public:
  ProtocolManager(CentipedeManager *cp_mgr);

  /**
   * @brief Clear the protocol program.
   *
   * Operation takes less than 3 ms to complete.
   */
  void clear();

  /**
   * @brief Add a new Line to the protocol program.
   *
   * @param duration Time duration in ms
   * @param points List of PCS points of which the corresponding valves will be
   * set open for the given duration. All other valves will be set closed.
   * @return True when the new line is successfully added. False otherwise,
   * because the maximum number of lines has been reached.
   */
  bool add_line(uint16_t duration, const PointsArray &points);
  bool add_line(const Line &line);

  /**
   * @brief Prime the start of the protocol program such that `update()` will
   * start the program directly at line position 0 wihout any delay.
   *
   * Note: Calling this method will /not/ activate any solenoid valves just yet.
   * `update()` must be called subsequently to trigger activation of line 0.
   */
  void prime_start();

  /**
   * @brief Go to Line number @p line_no of the protocol program (index starts
   * at 0) and immediately activate the solenoid valves and color the LED
   * matrix.
   */
  void goto_line(uint16_t line_no);

  /**
   * @brief Go to the next Line of the protocol program and
   * immediately activate the solenoid valves and color the LED matrix.
   */
  void goto_next_line();

  /**
   * @brief Go to the previous Line of the protocol program and
   * immediately activate the solenoid valves and color the LED matrix.
   */
  void goto_prev_line();

  /**
   * @brief Immediately activate the solenoid valves and color the LED matrix,
   * based on the current @p _line_buffer contents.
   */
  void activate_buffer();

  /**
   * @brief Run the timer of the protocol program.
   *
   * It will automatically activate the solenoid valves and color the LED matrix
   * accordingly, going line for line through the protocol program on its
   * specified time track.
   */
  void update();

  /**
   * @brief Pretty print the protocol program.
   */
  void print_program();

  /**
   * @brief Pretty print the current line buffer, useful for debugging.
   */
  void print_buffer();

  inline void set_name(const char *name) { strncpy(_name, name, 64); }
  inline char *get_name() { return _name; }
  inline uint16_t get_N_lines() { return _N_lines; }

  /**
   * @brief Get the playback position; current line number (index starts at 0)
   */
  inline int16_t get_position() { return _pos; }

private:
  Program _program;        // Protocol program currently loaded into memory
  char _name[64] = {'\0'}; // Name of the protocol program
  uint16_t _N_lines;       // Total number of lines in the protocol program
  uint16_t _pos; // Playback position; current line number (index starts at 0)
  uint32_t _tick = 0;        // Timestamp [ms] of last activated protocol line
  Line _last_activated_line; // The Line data that was last activated

  /**
   * @brief Buffer containing the current @p Line to be activated.
   *
   * One can go through each PCS point of the Line object as follows:
   *
   * @code{.cpp}
   * for (auto &p : _line_buffer.points) {
   *   if (p.is_null()) {
   *     break; // Reached the end sentinel
   *   }
   *   // Code goes here to handle each PCS point `p`
   * }
   * @endcode
   */
  Line _line_buffer;

  CentipedeManager *_cp_mgr;
};

#endif
