/**
 * @file    halt.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    18-10-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "halt.h"
#include "Adafruit_SleepyDog.h"
#include "DvG_StreamCommand.h"

extern DvG_StreamCommand sc;

void halt(uint8_t halt_ID, const char *msg) {
  const uint8_t arr_halt[] = {81,  83,  85,  86,  87,  89,  92,  93,  94,  98,
                              102, 104, 106, 108, 110, 113, 114, 115, 117, 118,
                              119, 121, 125, 130, 134, 136, 138, 140, 142, 145,
                              147, 149, 151, 153, 154, 155, 157};

  // Display 'HALT' on LED matrix
  fill_solid(leds, 256, CRGB::Black);      // Clear all
  fill_solid(leds, 32, CRGB::Red);         // Top bar
  fill_solid(&leds[224], 32, CRGB::Red);   // Bottom bar
  for (uint8_t idx = 0; idx < 37; idx++) { // Text 'HALT'
    leds[arr_halt[idx]] = CRGB::Red;
  }
  fill_solid(&leds[177], halt_ID, CRGB::Red); // Halt ID
  fill_solid(onboard_led, 1, CRGB::Red);

  // Shorten Watchdog timeout
  Watchdog.disable();
  Watchdog.enable(1000);

  while (1) {
    char *str_cmd; // Incoming serial ASCII-command string
    static bool blinker = false;

    Watchdog.reset();

    if (sc.available()) {
      str_cmd = sc.getCommand();
      if (strcmp(str_cmd, "reset") == 0) {
        Serial.println("Resetting...");
        delay(2000);
      }
    }

    EVERY_N_MILLIS(1000) {
      blinker = !blinker;
      if (blinker) {
        Serial.print("EXECUTION HALTED, ID: ");
        Serial.println(halt_ID);
        if (msg != NULL) {
          Serial.println(msg);
        }
        FastLED.setBrightness(30);
      } else {
        FastLED.setBrightness(5);
      }
      FastLED.show();
    }
  }
}