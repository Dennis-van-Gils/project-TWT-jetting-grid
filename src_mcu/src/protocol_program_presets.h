/**
 * @file    protocol_program_presets.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    12-04-2023
 *
 * @brief   Predefined protocol program presets for the TWT jetting grid.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"

// See `main.cpp`
extern ProtocolManager protocol_mgr;

/**
 * @brief All valves open
 */
void load_protocol_program_preset_0();

/**
 * @brief Walk over each single valve
 */
void load_protocol_program_preset_1();

/**
 * @brief Alternating checkerboard
 */
void load_protocol_program_preset_2();

/**
 * @brief Alternating even/odd valves
 */
void load_protocol_program_preset_3();

/**
 * @brief Walk over each manifold
 */
void load_protocol_program_preset_4();