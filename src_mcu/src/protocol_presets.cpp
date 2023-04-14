/**
 * @file    protocol_presets.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    14-04-2023
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "protocol_presets.h"
#include "constants.h"
#include "translations.h"

/**
 * @brief Open all valves
 */
static void generate_preset_0() {
  protocol_mgr.set_name("Open all valves");
  Line line;

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.points[idx_valve - 1] = valve2p(idx_valve);
  }

  line.points[N_VALVES].set_null(); // Add end sentinel
  line.duration = 1000;             // [ms]
  protocol_mgr.add_line(line);
}

/**
 * @brief Walk over all valves
 */
static void generate_preset_1() {
  protocol_mgr.set_name("Walk over valves");
  Line line;

  for (uint8_t idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    line.points[0] = valve2p(idx_valve);
    line.points[1].set_null(); // Add end sentinel
    line.duration = 500;       // [ms]
    protocol_mgr.add_line(line);
  }
}

/**
 * @brief Walk over all manifolds
 */
static void generate_preset_2() {
  protocol_mgr.set_name("Walk over manifolds");
  Line line;
  uint8_t idx_valve;
  uint8_t idx_point;

  // Manifold 1: Valves 1 to 28
  idx_point = 0;
  for (idx_valve = 1; idx_valve <= 28; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);

  // Manifold 2: Valves 29 to 56
  idx_point = 0;
  for (idx_valve = 29; idx_valve <= 56; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);

  // Manifold 3: Valves 57 to 84
  idx_point = 0;
  for (idx_valve = 57; idx_valve <= 84; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);

  // Manifold 4: Valves 85 to 112
  idx_point = 0;
  for (idx_valve = 85; idx_valve <= 112; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);
}

/**
 * @brief Alternating checkerboard
 */
static void generate_preset_3() {
  protocol_mgr.set_name("Checkerboard");
  Line line;
  uint8_t idx_valve;
  uint8_t idx_point;

  // First half of checkboard: Valves 1 to 28
  idx_point = 0;
  for (idx_valve = 1; idx_valve <= 28; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  // First half of checkboard: Valves 57 to 84
  for (idx_valve = 57; idx_valve <= 84; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);

  // Second half of checkboard: Valves 29 to 56
  idx_point = 0;
  for (idx_valve = 29; idx_valve <= 56; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  // Second half of checkboard: Valves 85 to 112
  for (idx_valve = 85; idx_valve <= 112; ++idx_valve) {
    line.points[idx_point] = valve2p(idx_valve);
    idx_point++;
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);
}

/**
 * @brief Alternating even/odd valves
 */
static void generate_preset_4() {
  protocol_mgr.set_name("Even/odd valves");
  Line line;
  uint8_t idx_valve;
  uint8_t idx_point;

  idx_point = 0;
  for (idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    if (idx_valve % 2 == 0) {
      line.points[idx_point] = valve2p(idx_valve);
      idx_point++;
    }
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);

  idx_point = 0;
  for (idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
    if (idx_valve % 2 == 1) {
      line.points[idx_point] = valve2p(idx_valve);
      idx_point++;
    }
  }
  line.points[idx_point].set_null(); // Add end sentinel
  line.duration = 1000;              // [ms]
  protocol_mgr.add_line(line);
}

void load_protocol_preset(uint16_t idx_preset) {
  protocol_mgr.clear();

  switch (idx_preset) {
    case 0:
      generate_preset_0();
      break;
    case 1:
      generate_preset_1();
      break;
    case 2:
      generate_preset_2();
      break;
    case 3:
      generate_preset_3();
      break;
    case 4:
      generate_preset_4();
      break;
    default:
      generate_preset_0();
      break;
  }

  protocol_mgr.prime_start();
}