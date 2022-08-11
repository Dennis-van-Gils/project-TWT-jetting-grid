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
  // TODO: Fill with special value denoting end-of-program
  program_[0].packed.fill(0); // TODO: fill(0) is incorrect, leave for now

  // Reset the current position
  current_pos_ = 0;
}

PackedLine ProtocolManager::pack_and_add(const Line &line) {
  PackedLine packed;
  packed.fill(0); // Crucial

  for (auto p = line.begin(); p != line.end(); ++p) {
    if (p->isNull()) {
      break;
    }

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

  return packed;
}

void ProtocolManager::pack_and_add2(const Line &line) {
  program_[0].packed.fill(0);

  for (auto p = line.begin(); p != line.end(); ++p) {
    if (p->isNull()) {
      break;
    }

    int8_t tmp_x = p->x + 7;
    int8_t tmp_y = 7 - p->y;
    if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
        (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Out-of-bounds index (%d, %d)", p->x,
               p->y);
      halt(2, buf);
    }
    program_[0].packed[tmp_y] |= (1U << tmp_x);
  }
}

void ProtocolManager::unpack(const PackedLine &packed) {
  uint16_t idx_P = 0;
  P p;

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate
      p.y = 7 - row;
      for (uint8_t bit = 0; bit < 16; ++bit) {
        if ((packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          line_buffer[idx_P] = p;
          idx_P++;
        }
      }
    }
  }

  // Add end sentinel
  line_buffer[idx_P].setNull();
}

void ProtocolManager::unpack() {
  uint16_t idx_P = 0;
  P p;

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (program_[0].packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate
      p.y = 7 - row;
      for (uint8_t bit = 0; bit < 16; ++bit) {
        if ((program_[0].packed[row] >> (bit)) & 0x01) {
          p.x = bit - 7;
          line_buffer[idx_P] = p;
          idx_P++;
        }
      }
    }
  }

  // Add end sentinel
  line_buffer[idx_P].setNull();
}