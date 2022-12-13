/**
 * @file    protocol_program_presets.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    13-12-2022
 *
 * @brief   Predefined protocol program presets for the TWT jetting grid.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "ProtocolManager.h"

// See `main.cpp`
extern ProtocolManager protocol_mgr;

/**
 * @brief Loop over each single valve
 */
void load_protocol_program_preset_0();

/**
 * @brief Growing center square
 */
void load_protocol_program_preset_1();

/**
 * @brief All open
 */
void load_protocol_program_preset_2();
