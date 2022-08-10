/**
 * @file    translations.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    10-08-2022
 *
 * @brief   Contains the translation functions for points P in the Protocol
 * Coordinate System (PCS), valves, LEDs and Centipede (CP) addresses.
 *
 * Will gracefully halt the microcontroller when out-of-bounds indices are
 * supplied.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef TRANSLATIONS_H_
#define TRANSLATIONS_H_

#include <Arduino.h>

#include "CentipedeManager.h"
#include "ProtocolManager.h"

// Common character buffer for string formatting, see `main.cpp`
extern const uint8_t BUF_LEN;
extern char buf[];

// Translation matrix: Valve number to PCS point.
// Reverse look-up. Must be build from the source array `P2VALVE` by calling
// `init_valve2p()` during `setup()`.
//   [dim 1]: The valve numbered 1 to 112, with 0 indicating 'no valve'
//   [dim 2]: PCS axis [0: x, 1: y]
//   Returns: The x or y-coordinate of the valve
int8_t VALVE2P[N_VALVES + 1][2] = {0};

/**
 * @brief Translate PCS point to valve number.
 *
 * @param p The PCS point
 * @return The valve numbered 1 to 112, with 0 indicating 'no valve'
 * @throw Halts when the PCS point is out-of-bounds
 */
uint8_t p2valve(P p);

/**
 * @brief Translate PCS point to LED index.
 *
 * @param p The PCS point
 * @return The LED index
 * @throw Halts when the PCS point is out-of-bounds
 */
uint8_t p2led(P p);

/**
 * @brief Translate valve number to PCS point.
 *
 * @param valve The valve numbered 1 to 112
 * @return The PCS point
 * @throw Halts when the valve number is out-of-bounds
 */
P valve2p(uint8_t valve);

/**
 * @brief Build the reverse look-up table in order for `valve2p()` to work.
 *
 * The reverse look-up table will get build from the source array `P2VALVE`. A
 * check will be performed to see if all valves from 1 to 112 are accounted for.
 *
 * @throw Halts when not all valve numbers from 1 to 112 are accounted for
 */
void init_valve2p();

/**
 * @brief Translate valve number to Centipede port and bit address.
 *
 * @param valve The valve numbered 1 to 112
 * @return The Centipede port and bit address
 * @throw Halts when the valve number is out-of-bounds
 */
CP_Address valve2cp(uint8_t valve);

#endif