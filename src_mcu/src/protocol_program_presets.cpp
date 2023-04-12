/**
 * @file    protocol_program_presets.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    12-04-2023
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "protocol_program_presets.h"
#include "constants.h"
#include "translations.h"

void load_protocol_program_preset_0() {
  // All valves open
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset 0: All valves open");

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.points[idx_valve - 1] = valve2p(idx_valve);
  }

  line.points[N_VALVES].set_null(); // Add end sentinel
  line.duration = 1000;             // [ms]
  protocol_mgr.add_line(line);
  protocol_mgr.prime_start();
}

void load_protocol_program_preset_1() {
  // Walk over each single valve
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset 1: Walk over each single valve");

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.points[0] = valve2p(idx_valve);
    line.points[1].set_null(); // Add end sentinel
    line.duration = 500;       // [ms]
    protocol_mgr.add_line(line);
  }

  protocol_mgr.prime_start();
}

void load_protocol_program_preset_2() {
  // Alternating checkerboard
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset 2: Alternating checkerboard");

  // Valves 1 to 84
  for (uint8_t idx_valve = 1; idx_valve <= 84; ++idx_valve) {
    line.points[idx_valve - 1] = valve2p(idx_valve);
  }
  line.points[84].set_null(); // Add end sentinel
  line.duration = 1000;       // [ms]
  protocol_mgr.add_line(line);

  // Valves 85 to 112
  for (uint8_t idx_valve = 85; idx_valve <= 112; ++idx_valve) {
    line.points[idx_valve - 1] = valve2p(idx_valve);
  }
  line.points[112].set_null(); // Add end sentinel
  line.duration = 1000;        // [ms]
  protocol_mgr.add_line(line);

  protocol_mgr.prime_start();
}

void load_protocol_program_preset_3() {
  // Alternating even/odd valves
  Line line;
  protocol_mgr.clear();
  protocol_mgr.set_name("Preset 3: Alternating even/odd valves");
  uint8_t idx_P = 0;

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    if (idx_valve % 2 == 0) {
      line.points[idx_P] = valve2p(idx_valve);
      idx_P++;
    }
  }
  line.points[idx_P].set_null(); // Add end sentinel
  line.duration = 1000;          // [ms]
  protocol_mgr.add_line(line);

  idx_P = 0;
  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    if (idx_valve % 2 == 1) {
      line.points[idx_P] = valve2p(idx_valve);
      idx_P++;
    }
  }
  line.points[idx_P].set_null(); // Add end sentinel
  line.duration = 1000;          // [ms]
  protocol_mgr.add_line(line);

  protocol_mgr.prime_start();
}