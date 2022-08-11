/**
 * @file    ProtocolManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    11-08-2022
 *
 * @brief   ...
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
 * @brief The maximum number of protocol lines that a full protocol program can
 * be made of.
 *
 * Make it as large as free RAM allows.
 */
const uint16_t MAX_LINES = 5000;

/**
 * @brief The maximum number of PCS points that a single protocol line can hold.
 *
 * Technically, the maximum number should equal the total number of valid valve
 * locations, so equal to `N_VALVES`. However, we deliberately make it able to
 * hold the full PCS space for array-indexing safety.
 *
 * Also, we add one extra spot at the end to allow for a sentinel to signal the
 * end point of the protocol line, i.e. the value `P{P_NULL_VAL, P_NULL_VAL}`.
 */
const uint16_t MAX_POINTS_PER_LINE = NUMEL_PCS_AXIS * NUMEL_PCS_AXIS + 1;

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

/**
 * @brief Special value denoting an uninitialized point in the PCS.
 *
 * Also used as a sentinel to signal the end point of a protocol line.
 */
const int8_t P_NULL_VAL = -128;

/**
 * @brief Class to hold and manage a single PCS point.
 *
 * Default initialization value is `{P_NULL_VAL, P_NULL_VAL}`.
 */
class P {
public:
  P(int8_t x_ = P_NULL_VAL, int8_t y_ = P_NULL_VAL);

  inline bool isNull() const {
    return ((x == P_NULL_VAL) || (y == P_NULL_VAL));
  }

  inline void setNull() {
    x = P_NULL_VAL;
    y = P_NULL_VAL;
  }

  void print(Stream &mySerial);

  // Public members
  int8_t x; // x-coordinate
  int8_t y; // y-coordinate
};

/*------------------------------------------------------------------------------
  Structures and typedefs
------------------------------------------------------------------------------*/

/**
 * @brief TODO descr
 *
 * An `std::array` for elements of a class type calls their default constructor.
 * Hence, the default initialization here is an array full with special valued
 * `P` objects: `P{P_NULL_VAL, P_NULL_VAL`}.
 * See, https://cplusplus.com/reference/array/array/array/.
 */
using Line = std::array<P, MAX_POINTS_PER_LINE>;

/**
 * @brief TODO descr
 *
 * Is a bitmask, in essence, decoding all the active points of the PCS.
 * Benefit to packing is the constant array dimension and less memory footprint
 * than using `Line` when using a large number of points `P`.
 *
 * An `std::array` for elements of fundamental types are left uninitialized,
 * unless the array object has static storage, in which case they are zero-
 * initialized. Hence, the default initialization here is zero-initialized
 * only when declared non-local.
 * See, https://cplusplus.com/reference/array/array/array/.
 */
using PackedLine = std::array<uint16_t, NUMEL_PCS_AXIS>;

struct TimeLine {
  uint32_t time;
  Line line;
};

struct PackedTimeLine {
  uint32_t time;
  PackedLine packed;
};

using Program = std::array<PackedTimeLine, MAX_LINES>;

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

/**
 * @brief
 *
 */
class ProtocolManager {
public:
  ProtocolManager();

  void clear();

  PackedLine pack_and_add(const Line &line);
  void pack_and_add2(const Line &line);

  /**
   * @brief
   *
   * Danger: The member `line_buffer` is valid as long as no other call to
   * `unpack()` is made.
   *
   * @param packed
   */
  void unpack(const PackedLine &packed);

  /**
   * @brief
   *
   * Danger: The member `line_buffer` is valid as long as no other call to
   * `unpack()` is made.
   */
  void unpack2();

  // Public members
  Line line_buffer; // For use with `unpack()`

private:
  Program program_;
  uint16_t N_program_lines_;
  uint16_t current_pos_;
};

#endif
