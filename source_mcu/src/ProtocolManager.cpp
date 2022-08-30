/**
 * @file    ProtocolManager.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    30-08-2022
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

void P::print(Stream &stream) {
  snprintf(buf, BUF_LEN, "(%d, %d)", x, y);
  stream.print(buf);
}

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager::ProtocolManager() { clear(); }

/*------------------------------------------------------------------------------
  ProtocolManager::clear
------------------------------------------------------------------------------*/

void ProtocolManager::clear() {
  for (auto t_packed = _program.begin(); t_packed != _program.end();
       ++t_packed) {
    t_packed->duration = 0;
    t_packed->packed.fill(0);
  }
  _N_lines = 0;
  _pos = -1; // -1 indicates we're at start-up of program
}

/*------------------------------------------------------------------------------
  ProtocolManager::add_line
------------------------------------------------------------------------------*/

bool ProtocolManager::add_line(const uint16_t duration, const Line &line) {
  if (_N_lines == MAX_LINES) {
    return false;
  }

  // Pack array of PCS points into bitmasks
  for (auto p = line.begin(); p != line.end(); ++p) {
    if (p->is_null()) {
      // Reached the end of the list as indicated by the end sentinel
      break;
    }

    int8_t tmp_x = p->x - PCS_X_MIN;
    int8_t tmp_y = PCS_Y_MAX - p->y;
    if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
        (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Out-of-bounds index (%d, %d)", p->x,
               p->y);
      halt(2, buf);
    }
    _program[_N_lines].packed[tmp_y] |= (1U << tmp_x);
  }
  // End of pack

  _program[_N_lines].duration = duration;
  _N_lines++;

  return true;
}

bool ProtocolManager::add_line(const TimedLine &timed_line) {
  return add_line(timed_line.duration, timed_line.line);
}

/*------------------------------------------------------------------------------
  ProtocolManager::transfer_next_line_to_buffer
------------------------------------------------------------------------------*/

void ProtocolManager::transfer_next_line_to_buffer() {
  _pos++;
  if (_pos == _N_lines) {
    _pos = 0;
  }

  // Unpack array of PCS points from bitmasks
  uint16_t idx_P = 0; // Index of newly unpacked point
  P p;                // Unpacked point

  for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
    if (_program[_pos].packed[row]) {
      // There is a mask > 0, so there must be at least one coordinate to unpack
      p.y = PCS_Y_MAX - row;
      for (uint8_t bit = 0; bit < NUMEL_PCS_AXIS; ++bit) {
        if ((_program[_pos].packed[row] >> (bit)) & 0x01) {
          p.x = PCS_X_MIN + bit;
          timed_line_buffer.line[idx_P] = p;
          idx_P++;
        }
      }
    }
  }
  timed_line_buffer.line[idx_P].set_null(); // Add end sentinel
  timed_line_buffer.duration = _program[_pos].duration;
}

/*------------------------------------------------------------------------------
  ProtocolManager::print
------------------------------------------------------------------------------*/

void ProtocolManager::print(Stream &stream) {
  P p; // Unpacked point

  for (uint16_t i = 0; i < _N_lines; ++i) {
    snprintf(buf, BUF_LEN, "*** Line %d | %d [ms]\n", i, _program[i].duration);
    stream.print(buf);

    for (uint8_t row = 0; row < NUMEL_PCS_AXIS; ++row) {
      if (_program[i].packed[row]) {
        // There is a mask > 0, so there must be at least one coordinate to
        // unpack
        p.y = PCS_Y_MAX - row;
        for (uint8_t bit = 0; bit < NUMEL_PCS_AXIS; ++bit) {
          if ((_program[i].packed[row] >> (bit)) & 0x01) {
            p.x = PCS_X_MIN + bit;
            p.print(stream);
          }
        }
      }
    }

    stream.write('\n');
    stream.write('\n');
  }
}

/*------------------------------------------------------------------------------
  ProtocolManager::print_buffer
------------------------------------------------------------------------------*/

void ProtocolManager::print_buffer(Stream &stream) {
  snprintf(buf, BUF_LEN, "*** Line %d | %d [ms]\n", _pos,
           timed_line_buffer.duration);
  stream.print(buf);

  for (auto &p : timed_line_buffer.line) {
    if (p.is_null()) {
      break; // Reached the end of the list as indicated by the end sentinel
    }
    p.print(stream);
  }

  stream.write('\n');
  stream.write('\n');
}
