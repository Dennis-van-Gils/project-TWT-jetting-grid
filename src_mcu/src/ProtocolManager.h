/**
 * @file    ProtocolManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    20-10-2022
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

#include "constants.h"
#include <Arduino.h>
#include <array>

// Common character buffer for string formatting, see `main.cpp`
extern const uint8_t BUF_LEN;
extern char buf[];

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
   * @brief Pack the PCS coordinate into a single byte.
   *
   * The upper 4 bits decode the PCS x-coordinate.
   * The lower 4 bits decode the PCS y-coordinate.
   *
   * @return The byte-encoded PCS coordinate
   */
  inline uint8_t pack_into_byte() {
    return (uint8_t)((x - PCS_X_MIN) << 4) | //
           (uint8_t)((y - PCS_Y_MIN) & 0xF);
  }

  /**
   * @brief Unpack the packed PCS coordinate and store it.
   *
   * The upper 4 bits decode the PCS x-coordinate.
   * The lower 4 bits decode the PCS y-coordinate.
   *
   * @param c The byte-encoded PCS coordinate
   */
  inline void unpack_byte(uint8_t c) {
    x = (c >> 4) + PCS_X_MIN;
    y = (c & 0xF) + PCS_Y_MIN;
  }

  /**
   * @brief Pretty print the PCS coordinate as "(x, y)", useful for debugging.
   *
   * @param stream The stream to print to. Default: Serial.
   */
  void print(Stream &stream = Serial);

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
   *
   * @param stream The stream to print to. Default: Serial.
   */
  void print(Stream &stream = Serial);

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
  ProtocolManager();

  /**
   * @brief Clear the protocol program stored in memory.
   *
   * Operations takes less than 3 ms to complete.
   */
  void clear();

  /**
   * @brief Reset the playback position of the protocol program back to start.
   */
  inline void restart() { _pos = -1; }

  /**
   * @return True when the end of the protocol has been reached, false otherwise
   */
  inline bool reached_end() { return (_pos == (_N_lines - 1)); }

  /**
   * @brief Adds a new Line to the protocol program.
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
   * @brief Retrieves the next available Line from the stored protocol
   * program and puts the information in the public member @p line_buffer.
   *
   * Warning: The member @p line_buffer will be overwritten with new data
   * when a new call to @p transfer_next_line_to_buffer() is made.
   */
  void transfer_next_line_to_buffer();

  /**
   * @brief Pretty print the protocol program.
   *
   * @param stream The stream to print to. Default: Serial.
   */
  void print_program(Stream &stream = Serial);

  /**
   * @brief Pretty print the current line buffer, useful for debugging.
   *
   * @param stream The stream to print to. Default: Serial.
   */
  void print_buffer(Stream &stream = Serial);

  /**
   * @brief Buffer containing the @p Line as retreived by method
   * @p transfer_next_line_to_buffer().
   *
   * One can go through each PCS point of the Line object as follows:
   *
   * @code{.cpp}
   * for (auto &p : protocol_mgr.line_buffer.points) {
   *   if (p.is_null()) {
   *     break; // Reached the end sentinel
   *   }
   *   // Code goes here to handle each PCS point `p`
   * }
   * @endcode
   */
  Line line_buffer;

  inline void set_name(const char *name) { strncpy(_name, name, 64); }
  inline char *get_name() { return _name; }
  inline uint16_t get_N_lines() { return _N_lines; }
  inline int16_t get_position() { return _pos; }

private:
  Program _program;        // The protocol program
  char _name[64] = {'\0'}; // Name of the protocol
  uint16_t _N_lines;       // Total number of lines making up the program
  int16_t _pos; // Playback position, where -1 indicates a fresh start
};

#endif