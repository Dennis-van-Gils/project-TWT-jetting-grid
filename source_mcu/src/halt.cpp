/**
 * @file    halt.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    25-08-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "halt.h"

void halt(uint8_t halt_ID, const char *msg) {
  const uint8_t arr_halt[] = {81,  83,  85,  86,  87,  89,  92,  93,  94,  98,
                              102, 104, 106, 108, 110, 113, 114, 115, 117, 118,
                              119, 121, 125, 130, 134, 136, 138, 140, 142, 145,
                              147, 149, 151, 153, 154, 155, 157};

  // LED matrix
  fill_solid(leds, 256, CRGB::Black);      // Clear all
  fill_solid(leds, 32, CRGB::Red);         // Top bar
  fill_solid(&leds[224], 32, CRGB::Red);   // Bottom bar
  for (uint8_t idx = 0; idx < 37; idx++) { // Text 'HALT'
    leds[arr_halt[idx]] = CRGB::Red;
  }
  fill_solid(&leds[177], halt_ID, CRGB::Red); // Halt ID

  // Onboard LED
  fill_solid(onboard_led, 1, CRGB::Red);

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