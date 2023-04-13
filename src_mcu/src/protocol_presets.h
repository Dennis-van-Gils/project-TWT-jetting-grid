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
 * @brief Open all valves
 */
void load_protocol_preset_0();

/**
 * @brief Walk over all valves
 */
void load_protocol_preset_1();

/**
 * @brief Walk over all manifolds
 */
void load_protocol_preset_2();

/**
 * @brief Alternating checkerboard
 */
void load_protocol_preset_3();

/**
 * @brief Alternating even/odd valves
 */
void load_protocol_preset_4();