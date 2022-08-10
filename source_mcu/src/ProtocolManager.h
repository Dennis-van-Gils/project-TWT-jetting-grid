/**
 * @file    ProtocolManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    10-08-2022
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

// TODO: descr
const uint16_t MAX_LINES = 5000;

// TODO: descr
const uint16_t MAX_POINTS_PER_LINE = NUMEL_PCS_AXIS * NUMEL_PCS_AXIS;

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

/**
 * @brief Special value denoting an uninitialized point in the PCS.
 */
const int8_t P_NULL_VAL = -128;

/**
 * @brief Class to hold and manage a single PCS point.
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

  int8_t x;
  int8_t y;
};

/*------------------------------------------------------------------------------
  Structures and typedefs
------------------------------------------------------------------------------*/

using Line = std::array<P, MAX_POINTS_PER_LINE>;
using PackedLine = std::array<uint16_t, NUMEL_PCS_AXIS>;

struct TimeLine {
  uint32_t time;
  Line line;
};

struct PackedTimeLine {
  uint32_t time;
  PackedLine line;
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

  P unpack(const PackedLine &packed);

  /**
   * @brief
   *
   * Copy by value. Slow.
   *
   * @param packed
   * @return ProtoLine
   */
  Line unpack2(const PackedLine &packed);

  /**
   * @brief
   *
   * Copy by reference. Fast.
   *
   * Danger: The return `ProtoLine*` is valid as long as no other call to
   * `unpack3()` is made.
   *
   * @param packed
   * @return ProtoLine*
   */
  Line *unpack3(const PackedLine &packed);

  /**
   * @brief
   *
   * Refer directly to class member
   *
   * Danger: The member `line_buffer` is valid as long as no other call to
   * `unpack4()` is made.
   *
   * @param packed
   * @return ProtoLine*
   */
  std::array<P, MAX_POINTS_PER_LINE + 1>
      line_buffer; // For use with `unpack4`, Extra spot added for end sentinel
                   // `P_NULL`

  void unpack4(const PackedLine &packed);

private:
  Program program_;
  uint16_t N_program_lines_;
  uint16_t current_pos_;
  Line line_; // For use with `unpack3()`
};

#endif
