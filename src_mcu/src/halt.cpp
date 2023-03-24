/**
 * @file    halt.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    23-03-2023
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "halt.h"
#include "Adafruit_SleepyDog.h"
#include "DvG_StreamCommand.h"

extern DvG_StreamCommand sc;

void halt(uint8_t halt_ID, const char *msg) {
  const uint8_t arr_halt[] = {21,  38,  39,  40,  41,  42,  53,  70,  89,  102,
                              103, 104, 105, 106, 134, 135, 136, 137, 138, 149,
                              151, 166, 167, 168, 169, 170, 198, 199, 200, 201,
                              202, 215, 230, 231, 232, 233, 234};
  const uint8_t arr_bars[] = {
      14,  15,  16,  17,  46,  47,  48,  49,  78,  79,  80,  81,  110,
      111, 112, 113, 142, 143, 144, 145, 174, 175, 176, 177, 206, 207,
      208, 209, 238, 239, 240, 241, 0,   1,   30,  31,  32,  33,  62,
      63,  64,  65,  94,  95,  96,  97,  126, 127, 128, 129, 158, 159,
      160, 161, 190, 191, 192, 193, 222, 223, 224, 225, 254, 255};

  // Display 'HALT' on LED matrix
  fill_solid(leds, 256, CRGB::Black);                    // Clear all
  for (uint8_t idx = 0; idx < sizeof(arr_bars); idx++) { // Top & bottom bars
    leds[arr_bars[idx]] = CRGB::Red;
  }
  for (uint8_t idx = 0; idx < sizeof(arr_halt); idx++) { // Text 'HALT'
    leds[arr_halt[idx]] = CRGB::Red;
  }
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