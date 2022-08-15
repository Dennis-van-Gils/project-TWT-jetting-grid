/**
 * @file    translations.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    15-08-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "translations.h"
#include "constants.h"
#include "halt.h"
#include <algorithm>

// Translation matrix: Valve number to PCS point.
// Reverse look-up. Must be build from the source array `P2VALVE` by calling
// `init_valve2p()` during `setup()`.
//   [dim 1]: The valve numbered 1 to 112, with 0 indicating 'no valve'
//   [dim 2]: PCS axis [0: x, 1: y]
//   Returns: The x or y-coordinate of the valve
int8_t VALVE2P[N_VALVES + 1][2] = {0};

uint8_t p2valve(P p) {
  int8_t tmp_x = p.x + PCS_X_AXIS_MAX;
  int8_t tmp_y = PCS_Y_AXIS_MAX - p.y;
  if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
      (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds index (%d, %d) in `p2valve()`", p.x, p.y);
    halt(1, buf);
  }
  return P2VALVE[tmp_y][tmp_x];
}

uint8_t p2led(P p) {
  int8_t tmp_x = p.x + PCS_X_AXIS_MAX;
  int8_t tmp_y = PCS_Y_AXIS_MAX - p.y;
  if ((tmp_x < 0) || (tmp_x >= NUMEL_PCS_AXIS) || //
      (tmp_y < 0) || (tmp_y >= NUMEL_PCS_AXIS)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds index (%d, %d) in `p2led()`", p.x, p.y);
    halt(2, buf);
  }
  return P2LED[tmp_y][tmp_x];
}

P valve2p(uint8_t valve) {
  if ((valve == 0) || (valve > N_VALVES)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds valve number %d in `valve2p()`", valve);
    halt(3, buf);
  }
  return P{VALVE2P[valve][0], VALVE2P[valve][1]};
}

void init_valve2p() {
  uint8_t valve;
  int8_t x;
  int8_t y;

  // Initialize array with special value `P_NULL_VAL` to be able to check
  // if valves are missing from the reverse look-up table.
  std::fill(*VALVE2P, *VALVE2P + (N_VALVES + 1) * 2, P_NULL_VAL);

  // Build the reverse look-up table
  for (y = PCS_Y_AXIS_MAX; y > PCS_Y_AXIS_MIN - 1; y--) {
    for (x = PCS_X_AXIS_MIN; x < PCS_X_AXIS_MAX + 1; x++) {
      valve = P2VALVE[PCS_Y_AXIS_MAX - y][x + PCS_X_AXIS_MAX];
      if (valve > 0) {
        VALVE2P[valve][0] = x;
        VALVE2P[valve][1] = y;
      }
    }
  }

  // Check if all valves from 1 to 112 are accounted for
  for (valve = 1; valve < N_VALVES + 1; valve++) {
    x = VALVE2P[valve][0];
    y = VALVE2P[valve][1];
    if ((x == P_NULL_VAL) || (y == P_NULL_VAL)) {
      snprintf(buf, BUF_LEN, "CRITICAL: Valve number %d is not accounted for",
               valve);
      halt(4, buf);
    }
  }
}

CP_Address valve2cp(uint8_t valve) {
  if ((valve == 0) || (valve > N_VALVES)) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds valve number %d in `valve2cp()`", valve);
    halt(6, buf);
  }
  return CP_Address{VALVE2CP_PORT[valve - 1], VALVE2CP_BIT[valve - 1]};
}