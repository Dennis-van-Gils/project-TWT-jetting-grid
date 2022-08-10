/**
 * @file    ProtocolManager.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    10-08-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"
#include "halt.h"

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

P::P(int8_t x_, int8_t y_) {
  x = x_;
  y = y_;
}

void P::print(Stream &mySerial) {
  snprintf(buf, BUF_LEN, "(%d, %d)", x, y);
  mySerial.print(buf);
}

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager::ProtocolManager() {}

void ProtocolManager::clear() {
  // We clear the program by setting the first entry of the program to contain
  // only PCS points with the special value of `P_NULL_VAL`.
  // program_[0].fill(P_NULL_VAL);

  // Reset the current position
  current_pos_ = 0;
}

PackedLine ProtocolManager::pack_and_add(const Line &line) {
  PackedLine packed;
  packed.fill(0);

  for (auto p = line.begin(); p != line.end(); ++p) {
    if (p->isNull()) {
      break;
    }
    // p->print(Serial);
    snprintf(buf, BUF_LEN, "(%d, %d)", p->x, p->y);
    Serial.print(buf);

    int8_t tmp_x = p->x + 7;
    int8_t tmp_y = 7 - p->y;
    if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
        (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Out-of-bounds index (%d, %d)", p->x,
               p->y);
      halt(2, buf);
    }
    packed[tmp_y] |= (1U << tmp_x);
  }

  // TODO: For now simply write to first row. Later, keep track of written
  // lines
  // program_[0] = packed;

  return packed; // TODO: Do not return, keep void
}

P ProtocolManager::unpack(const PackedLine &packed) {
  // Returns another PCS point of the current line for as long as they exist.
  // Returns `P{P_NULL_VAL, P_NULL_VAL}` when the end has been reached.
  static uint8_t row = 0;
  static uint8_t bit = 0;
  P p;

  while (row < NUMEL_PCS_AXIS) {
    if (packed[row]) {
      // There is a mask > 0, so there must be at least one PCS point
      p.y = 7 - row;
      while (bit < 16) {
        if ((packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          bit++;
          return p; // Return the PCS point
        }
        bit++;
      }
    }
    row++;
    bit = 0;
  }

  row = 0;
  bit = 0;
  return p;
}

Line ProtocolManager::unpack2(const PackedLine &packed) {
  Line line;
  uint16_t idx_coord = 0;
  P p;

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate
      p.y = 7 - row;
      for (uint8_t bit = 0; bit < 16; ++bit) {
        if ((packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          line_[idx_coord] = p;
          idx_coord++;
        }
      }
    }
  }

  return line_;
}

Line *ProtocolManager::unpack3(const PackedLine &packed) {
  uint16_t idx_coord = 0;
  P p;

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate
      p.y = 7 - row;
      for (uint8_t bit = 0; bit < 16; ++bit) {
        if ((packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          line_[idx_coord] = p;
          idx_coord++;
        }
      }
    }
  }

  // TODO: Add extra spot for end sentinel `P_NULL`
  line_[idx_coord].setNull();

  return &line_;
}

void ProtocolManager::unpack4(const PackedLine &packed) {
  uint16_t idx_coord = 0;
  P p;

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate
      p.y = 7 - row;
      for (uint8_t bit = 0; bit < 16; ++bit) {
        if ((packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          line_buffer[idx_coord] = p;
          idx_coord++;
        }
      }
    }
  }

  // Extra spot added for end sentinel `P_NULL`
  line_buffer[idx_coord].setNull();
}
