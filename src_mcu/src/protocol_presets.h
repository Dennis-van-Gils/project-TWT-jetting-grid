/**
 * @file    protocol_presets.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    14-04-2023
 *
 * @brief   Predefined protocol program presets for the TWT jetting grid.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"

// See `main.cpp`
extern ProtocolManager protocol_mgr;

/**
 * @brief Load a protocol preset into Arduino memory:
 *   0: Open all valves
 *   1: Walk over all valves
 *   2: Walk over all manifolds
 *   3: Alternating checkerboard
 *   4: Alternating even/odd valves
 */
void load_protocol_preset(uint16_t idx_preset);