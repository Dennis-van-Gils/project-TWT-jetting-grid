/**
 * @file    ProtocolManager.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    02-12-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"
#include "halt.h"
#include "translations.h"

/*------------------------------------------------------------------------------
  P "Point in the Protocol Coordinate System (PCS)"
------------------------------------------------------------------------------*/

void P::print() {
  snprintf(buf, BUF_LEN, "(%d, %d)", x, y);
  Serial.print(buf);
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

void Line::print() {
  snprintf(buf, BUF_LEN, "%d ms\n", duration);
  Serial.print(buf);

  for (auto &p : points) {
    if (p.is_null()) {
      break; // Reached the end sentinel
    }
    p.print();
  }
  Serial.write('\n');
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
      // There is a mask > 0, so there must be at least one PCS point to unpack
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

ProtocolManager::ProtocolManager(CentipedeManager *cp_mgr) {
  _cp_mgr = cp_mgr;
  clear();
}

void ProtocolManager::clear() {
  for (auto packed_line = _program.begin(); packed_line != _program.end();
       ++packed_line) {
    packed_line->duration = 0;
    packed_line->masks.fill(0);
  }
  set_name("cleared");
  _N_lines = 0;
  _pos = 0;
}

bool ProtocolManager::add_line(const Line &line) {
  if (_N_lines == PROTOCOL_MAX_LINES) {
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

void ProtocolManager::goto_line(uint16_t line_no) {
  if (_N_lines > 0) {
    _pos = min(line_no, _N_lines - 1);
    _program[_pos].unpack_into(_line_buffer);
  }
}

void ProtocolManager::goto_start() { goto_line(0); }

void ProtocolManager::goto_next_line() {
  if (_N_lines > 0) {
    if (_pos == _N_lines - 1) {
      _pos = 0;
    } else {
      _pos++;
    }
    goto_line(_pos);
  }
}

void ProtocolManager::goto_prev_line() {
  if (_N_lines > 0) {
    if (_pos == 0) {
      _pos = _N_lines - 1;
    } else {
      _pos--;
    }
    goto_line(_pos);
  }
}

void ProtocolManager::activate_line() {
  _tick = millis();

  // Recolor the LEDs of previously active valves from red to blue
  for (auto &p : _last_activated_line.points) {
    if (p.is_null()) {
      break; // Reached the end sentinel
    }
    leds[p2led(p)] = CRGB::Blue;
  }

  // Backup the current line buffer
  _last_activated_line.duration = _line_buffer.duration;
  _last_activated_line.points = _line_buffer.points;

  // Parse the line
  _cp_mgr->clear_masks();
  for (auto &p : _line_buffer.points) {
    if (p.is_null()) {
      break; // Reached the end sentinel
    }

    // Add valve to be opened to the Centipede masks
    _cp_mgr->add_to_masks(valve2cp(p2valve(p)));

    // Color all active valve LEDs in red
    leds[p2led(p)] = CRGB::Red;
  }

  if (!NO_PERIPHERALS) {
    _cp_mgr->send_masks(); // Activate valves
  }

  Serial.println(_pos);
  if (DEBUG) {
    print_buffer();
  }
}

void ProtocolManager::update() {
  if (millis() - _tick >= _last_activated_line.duration) {
    goto_next_line();
    activate_line();
  }
}

void ProtocolManager::print_program() {
  Serial.println(_name);
  Serial.println(_N_lines);

  /*
  Line line;
  Serial.write('\n');
  for (uint16_t i = 0; i < _N_lines; ++i) {
    snprintf(buf, BUF_LEN, "#%d\t", i);
    Serial.print(buf);
    _program[i].unpack_into(line);
    line.print();
  }
  Serial.write('\n');
  */
}

void ProtocolManager::print_buffer() {
  snprintf(buf, BUF_LEN, "#%d\t", _pos);
  Serial.print(buf);
  _line_buffer.print();
  Serial.write('\n');
}