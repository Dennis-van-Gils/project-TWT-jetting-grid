/**
 * @file    ProtocolManager.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    31-08-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"
#include "halt.h"

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

void P::print(Stream &stream) {
  snprintf(buf, BUF_LEN, "(%d, %d)", x, y);
  stream.print(buf);
}

/*------------------------------------------------------------------------------
  Line
------------------------------------------------------------------------------*/

void Line::pack_into(PackedLine &output) const {
  // Pack array of PCS points into bitmasks
  for (auto p = points.begin(); p != points.end(); ++p) {
    if (p->is_null()) {
      break; // Reached the end sentinel
    }

    int8_t tmp_x = p->x - PCS_X_MIN;
    int8_t tmp_y = PCS_Y_MAX - p->y;
    if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
        (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Out-of-bounds index (%d, %d)", p->x,
               p->y);
      halt(2, buf);
    }
    output.masks[tmp_y] |= (1U << tmp_x);
    output.duration = duration;
  }
}

void Line::print(Stream &stream) {
  snprintf(buf, BUF_LEN, "%d [ms]\n", duration);
  stream.print(buf);

  for (auto &p : points) {
    if (p.is_null()) {
      break; // Reached the end sentinel
    }
    p.print(stream);
  }
}

/*------------------------------------------------------------------------------
  PackedLine
------------------------------------------------------------------------------*/

void PackedLine::unpack_into(Line &output) const {
  uint16_t idx_P = 0; // Index of newly unpacked point
  P p;                // Unpacked point

  // Unpack array of PCS points from bitmasks
  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (masks[row]) {
      // There is a mask > 0, so there must be at least one coordinate to unpack
      p.y = PCS_Y_MAX - row;
      for (uint8_t bit = 0; bit < NUMEL_PCS_AXIS; ++bit) {
        if ((masks[row] >> (bit)) & 0x01) {
          p.x = PCS_X_MIN + bit;
          output.points[idx_P] = p;
          idx_P++;
        }
      }
    }
  }
  output.points[idx_P].set_null(); // Add end sentinel
  output.duration = duration;
}

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager::ProtocolManager() { clear(); }

void ProtocolManager::clear() {
  for (auto packed_line = _program.begin(); packed_line != _program.end();
       ++packed_line) {
    packed_line->duration = 0;
    packed_line->masks.fill(0);
  }
  _N_lines = 0;
  _pos = -1; // -1 indicates we're at start-up of program
}

bool ProtocolManager::add_line(const Line &line) {
  if (_N_lines == MAX_LINES) {
    return false;
  }

  line.pack_into(_program[_N_lines]);
  _N_lines++;
  return true;
}

bool ProtocolManager::add_line(const uint16_t duration,
                               const PointsArray &points) {
  Line line(duration, points);
  return add_line(line);
}

void ProtocolManager::transfer_next_line_to_buffer() {
  _pos++;
  if (_pos == _N_lines) {
    _pos = 0;
  }

  _program[_pos].unpack_into(line_buffer);
}

void ProtocolManager::print(Stream &stream) {
  Line line;

  for (uint16_t i = 0; i < _N_lines; ++i) {
    snprintf(buf, BUF_LEN, "*** Line %d | ", i);
    stream.print(buf);
    _program[i].unpack_into(line);
    line.print();
    stream.write('\n');
    stream.write('\n');
  }
}

void ProtocolManager::print_buffer(Stream &stream) {
  snprintf(buf, BUF_LEN, "*** Line %d | ", _pos);
  stream.print(buf);
  line_buffer.print();
  stream.write('\n');
  stream.write('\n');
}