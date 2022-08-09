/**
 * @file    ProtocolManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    09-08-2022
 *
 * @brief   ...
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef PROTOCOL_MANAGER_H_
#define PROTOCOL_MANAGER_H_

#include <Arduino.h> // Only included for Serial access

#include <algorithm>
#include <array>
using namespace std;

#include "constants.h"
#include "halt.h"

// Common character buffer for string formatting, see `main.cpp`
extern const uint8_t BUF_LEN;
extern char buf[];

/**
 * @brief Special value denoting an uninitialized protocol coordinate (PC)
 */
const int8_t PC_NULL = -128;

const uint16_t MAX_COORDS_PER_PROTO_LINE =
    NUMEL_PCS_AXIS * NUMEL_PCS_AXIS;   // TODO: descr
const uint16_t MAX_PROTO_LINES = 5000; // TODO: descr

/*------------------------------------------------------------------------------
  PC "ProtocolCoordinate"
------------------------------------------------------------------------------*/

/**
 * @brief Class to hold and manage a single protocol coordinate (PC).
 */
class PC {
public:
  PC(int8_t x_ = PC_NULL, int8_t y_ = PC_NULL) {
    x = x_;
    y = y_;
  };

  bool isNull() { return ((x == PC_NULL) || (y == PC_NULL)); }

  void print(Stream &mySerial) {
    snprintf(buf, BUF_LEN, "(%d, %d)", x, y);
    mySerial.print(buf);
  }

  int8_t x;
  int8_t y;
};

/*------------------------------------------------------------------------------
  Typedefs
------------------------------------------------------------------------------*/

using ProtoLine = std::array<PC, MAX_COORDS_PER_PROTO_LINE>;
using PackedProtoLine = std::array<uint16_t, NUMEL_PCS_AXIS>;
using ProtoProgram = std::array<PackedProtoLine, MAX_PROTO_LINES>;

/*------------------------------------------------------------------------------
  Protocol coordinate transformations
------------------------------------------------------------------------------*/

/**
 * @brief Translate protocol coordinate to valve number.
 *
 * @param pc The protocol coordinate
 * @return The valve numbered 1 to 112, with 0 indicating 'no valve'
 * @throw Halts when the protocol coordinate is out-of-bounds
 */
uint8_t pc2valve(PC pc) {
  int8_t tmp_x = pc.x + 7;
  int8_t tmp_y = 7 - pc.y;
  if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
      (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds index (%d, %d) in `pc2valve()`", pc.x,
             pc.y);
    halt(1, buf);
  }
  return PC2VALVE[tmp_y][tmp_x];
}

/**
 * @brief Translate protocol coordinate to LED index.
 *
 * @param pc The protocol coordinate
 * @return The LED index
 * @throw Halts when the protocol coordinate is out-of-bounds
 */
uint8_t pc2led(PC pc) {
  int8_t tmp_x = pc.x + 7;
  int8_t tmp_y = 7 - pc.y;
  if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
      (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds index (%d, %d) in `pc2led()`", pc.x,
             pc.y);
    halt(2, buf);
  }
  return PC2LED[tmp_y][tmp_x];
}

/**
 * @brief Translate valve number to protocol coordinate.
 *
 * @param valve The valve numbered 1 to 112
 * @return The protocol coordinate
 * @throw Halts when the valve number is out-of-bounds
 */
PC valve2pc(uint8_t valve) {
  if ((valve == 0) || (valve > N_VALVES)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds valve number %d in `valve2pc()`", valve);
    halt(3, buf);
  }
  return PC{VALVE2PC[valve][0], VALVE2PC[valve][1]};
}

/**
 * @brief Build the reverse look-up table in order for `valve2pc()` to
 * work.
 *
 * The reverse look-up table will get build from the source array `PC2VALVE`. A
 * check will be performed to see if all valves from 1 to 112 are accounted for.
 *
 * @throw Halts when not all valve numbers from 1 to 112 are accounted for
 */
void init_valve2pc() {
  uint8_t valve;
  int8_t x;
  int8_t y;

  // Initialize array with special value `PC_NULL` to be able to check
  // if valves are missing from the reverse look-up table.
  std::fill(*VALVE2PC, *VALVE2PC + (N_VALVES + 1) * 2, PC_NULL);

  // Build the reverse look-up table
  for (y = 7; y > -8; y--) {
    for (x = -7; x < 8; x++) {
      valve = PC2VALVE[7 - y][x + 7];
      if (valve > 0) {
        VALVE2PC[valve][0] = x;
        VALVE2PC[valve][1] = y;
      }
    }
  }

  // Check if all valves from 1 to 112 are accounted for
  for (valve = 1; valve < N_VALVES + 1; valve++) {
    x = VALVE2PC[valve][0];
    y = VALVE2PC[valve][1];
    if ((x == PC_NULL) || (y == PC_NULL)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Valve number %d is not accounted for",
               valve);
      halt(4, buf);
    }
  }
}

/*------------------------------------------------------------------------------
  Valve to Centipede transformations
------------------------------------------------------------------------------*/

/**
 * @brief Translate valve number to Centipede port and bit address.
 *
 * @param valve The valve numbered 1 to 112
 * @return The Centipede port and bit address
 * @throw Halts when the valve number is out-of-bounds
 */
CP_Address valve2cp(uint8_t valve) {
  if ((valve == 0) || (valve > N_VALVES)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds valve number %d in `valve2cp()`", valve);
    halt(6, buf);
  }
  return CP_Address{VALVE2CP_PORT[valve - 1], VALVE2CP_BIT[valve - 1]};
}

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

/**
 * @brief
 *
 */
class ProtocolManager {
public:
  ProtocolManager() {}

  void clear() {
    // We clear the program by setting the first entry of the program to contain
    // only protocol coordinates with the special value of `PC_NULL`.
    program_[0].fill(PC_NULL);

    // Reset the current position
    current_pos_ = 0;
  }

  PackedProtoLine pack_and_add(const ProtoLine &line) {
    PackedProtoLine packed;
    packed.fill(0);

    for (auto pc = line.begin(); pc != line.end(); ++pc) {
      if (pc->x == PC_NULL || pc->y == PC_NULL) {
        break;
      }
      // pc->print(Serial);
      snprintf(buf, BUF_LEN, "(%d, %d)", pc->x, pc->y);
      Serial.print(buf);

      int8_t tmp_x = pc->x + 7;
      int8_t tmp_y = 7 - pc->y;
      if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
          (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
        snprintf(buf, BUF_LEN, "CRITICAL: Out-of-bounds index (%d, %d)", pc->x,
                 pc->y);
        halt(2, buf);
      }
      packed[tmp_y] |= (1U << tmp_x);
    }

    // TODO: For now simply write to first row. Later, keep track of written
    // lines
    program_[0] = packed;

    return packed; // TODO: Do not return, keep void
  }

  PC unpack(const PackedProtoLine &packed_line) {
    // Returns another protocol coordinate of the current line for as long as
    // they exist. Returns `{CP_NULL, CP_NULL}` when the end has been reached.
    static uint8_t row = 0;
    static uint8_t bit = 0;
    PC pc;

    while (row < NUMEL_PCS_AXIS) {
      // Serial.println("");
      // Serial.print(row);
      // Serial.write('\t');
      // Serial.println(bit);
      // Serial.println("");
      if (packed_line[row]) {
        pc.y = 7 - row;
        while (bit < 16) {
          if ((packed_line[row] >> (bit)) & 0x01) {
            pc.x = bit - 7;
            bit++;
            return pc;
          }
          bit++;
        }
      }
      row++;
      bit = 0;
    }

    row = 0;
    bit = 0;
    return pc;
  }

private:
  ProtoProgram program_;
  uint16_t N_program_lines_;
  uint16_t current_pos_;
};

#endif
