/**
 * @file    halt.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    10-08-2022
 *
 * @brief   Gracefully halt the microcontroller of the TWT jetting grid.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef HALT_H_
#define HALT_H_

#include "FastLED.h"
#include <Arduino.h>

// See `main.cpp`
extern CRGB leds[256];

/**
 * @brief Halt execution and flash the text 'HALT' on the LED matrix and repeat
 * a given text message over the Serial port in an infinite loop.
 *
 * Can be used to gracefully catch an illegal operation, like trying to address
 * an out-of-bounds index of an array. Clearly, this function should never get
 * executed in "properly" working code and when it does, it is a message to the
 * programmer to add more stringent checks on passed function parameters.
 *
 * @param halt_ID Optional ID to identify where in the source code the `halt`
 * function got called. The ID number will show up as extra lit LEDs underneath
 * the 'HALT' text.
 * @param msg Optional text to display over the serial output.
 */
void halt(uint8_t halt_ID = 0, const char *msg = NULL);

#endif