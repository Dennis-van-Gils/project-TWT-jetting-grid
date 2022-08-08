/**
 * @file    halt.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @brief   Halt execution specific to the TWT jetting grid
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef HALT_H_
#define HALT_H_

#include "FastLED.h"

extern CRGB leds[256];

/**
 * @brief Halt execution and flash the text 'HALT' on the LED matrix in an
 * infinite loop.
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
void halt(uint8_t halt_ID = 0, const char *msg = NULL) {
  const uint8_t arr_halt[] = {81,  83,  85,  86,  87,  89,  92,  93,  94,  98,
                              102, 104, 106, 108, 110, 113, 114, 115, 117, 118,
                              119, 121, 125, 130, 134, 136, 138, 140, 142, 145,
                              147, 149, 151, 153, 154, 155, 157};

  fill_solid(leds, 256, CRGB::Black);      // Clear all
  fill_solid(leds, 32, CRGB::Red);         // Top bar
  fill_solid(&leds[224], 32, CRGB::Red);   // Bottom bar
  for (uint8_t idx = 0; idx < 37; idx++) { // Text 'HALT'
    leds[arr_halt[idx]] = CRGB::Red;
  }
  fill_solid(&leds[177], halt_ID, CRGB::Red); // Halt ID

  while (1) {
    Serial.print("EXECUTION HALTED, ID: ");
    Serial.println(halt_ID);
    if (msg != NULL) {
      Serial.println(msg);
    }

    FastLED.setBrightness(30);
    FastLED.show();
    delay(1000);
    FastLED.setBrightness(5);
    FastLED.show();
    delay(1000);
  }
}

#endif