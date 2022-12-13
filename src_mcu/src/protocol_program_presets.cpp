/**
 * @file    protocol_program_presets.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    13-12-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "protocol_program_presets.h"
#include "constants.h"
#include "translations.h"

void load_protocol_program_preset_0() {
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset: Loop over each single valve");

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.duration = 200; // [ms]
    line.points[0] = valve2p(idx_valve);
    line.points[1].set_null(); // Add end sentinel
    protocol_mgr.add_line(line);
  }

  protocol_mgr.prime_start();
}

void load_protocol_program_preset_1() {
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset: Growing center square");

  for (uint8_t rung = 0; rung < 7; rung++) {
    uint8_t idx_P = 0;
    for (int8_t x = -7; x < 8; ++x) {
      for (int8_t y = -7; y < 8; ++y) {
        if ((x + y) & 1) {
          if (abs(x) + abs(y) == rung * 2 + 1) {
            line.points[idx_P].set(x, y);
            line.duration = 200; // [ms]
            idx_P++;
          }
        }
      }
    }
    line.points[idx_P].set_null(); // Add end sentinel
    protocol_mgr.add_line(line);
  }

  protocol_mgr.prime_start();
}

void load_protocol_program_preset_2() {
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset: Loop over each single valve");

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.points[idx_valve - 1] = valve2p(idx_valve);
  }

  line.duration = 200;              // [ms]
  line.points[N_VALVES].set_null(); // Add end sentinel
  protocol_mgr.add_line(line);
  protocol_mgr.prime_start();
}