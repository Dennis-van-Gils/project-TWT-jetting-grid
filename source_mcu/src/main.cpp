/**
 * @file    Main.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    16-08-2022
 *
 * @brief   Main control of the TWT jetting grid. See `constants.h` for a
 * detailed description.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "CentipedeManager.h"
#include "ProtocolManager.h"
#include "constants.h"
#include "translations.h"

#include "DvG_SerialCommand.h"
#include "FastLED.h"
#include "MIKROE_4_20mA_RT_Click.h"
#include "MemoryFree.h"

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <array>

// Serial command listener
DvG_SerialCommand sc(Serial);

// Will be used externally
const uint8_t BUF_LEN = 128; // Common character buffer for string formatting
char buf[BUF_LEN]{'\0'};     // Common character buffer for string formatting

// DEBUG: timer
uint32_t utick = micros();

// DEBUG: Allows developing code on a bare Arduino without sensors & actuators
// attached
#define DEVELOPER_MODE_WITHOUT_PERIPHERALS 0

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager protocol_mgr;

/*------------------------------------------------------------------------------
  State
------------------------------------------------------------------------------*/

struct State {
  // Exponential moving averages (EMA) of the R Click boards
  uint32_t DAQ_obtained_DT; // Obtained oversampling interval [µs]
  float EMA_1;              // Exponential moving average of R Click 1 [bitval]
  float EMA_2;              // Exponential moving average of R Click 2 [bitval]
  float EMA_3;              // Exponential moving average of R Click 3 [bitval]
  float EMA_4;              // Exponential moving average of R Click 4 [bitval]

  // OMEGA pressure sensors
  float pres_1_mA = NAN;  // OMEGA pressure sensor 1 [mA]
  float pres_2_mA = NAN;  // OMEGA pressure sensor 2 [mA]
  float pres_3_mA = NAN;  // OMEGA pressure sensor 3 [mA]
  float pres_4_mA = NAN;  // OMEGA pressure sensor 4 [mA]
  float pres_1_bar = NAN; // OMEGA pressure sensor 1 [bar]
  float pres_2_bar = NAN; // OMEGA pressure sensor 2 [bar]
  float pres_3_bar = NAN; // OMEGA pressure sensor 3 [bar]
  float pres_4_bar = NAN; // OMEGA pressure sensor 4 [bar]
};
State state; // Structure holding the sensor readings and actuator states

/*------------------------------------------------------------------------------
  Macetech Centipede boards
------------------------------------------------------------------------------*/

// One object controls both Centipede boards over ports 0 to 7
CentipedeManager cp_mgr;

/*------------------------------------------------------------------------------
  LEDs
------------------------------------------------------------------------------*/

bool alive_blinker = true; // Blinker for the 'alive' status LED
CRGB onboard_led[1];       // Onboard NeoPixel of the Adafruit Feather M4 board
CRGB leds[N_LEDS];         // LED matrix, 16x16 RGB NeoPixel (Adafruit #2547)

/*------------------------------------------------------------------------------
  MIKROE 4-20 mA R Click boards for reading out the OMEGA pressure sensors
------------------------------------------------------------------------------*/

R_Click R_click_1(PIN_R_CLICK_1, R_CLICK_1_CALIB);
R_Click R_click_2(PIN_R_CLICK_2, R_CLICK_2_CALIB);
R_Click R_click_3(PIN_R_CLICK_3, R_CLICK_3_CALIB);
R_Click R_click_4(PIN_R_CLICK_4, R_CLICK_4_CALIB);

/**
 * @brief Perform an exponential moving average (EMA) on each R Click reading by
 * using oversampling and subsequent low-pass filtering.
 *
 * This function should be repeatedly called in the main loop, ideally at a
 * faster pace than the given oversampling interval `DAQ_DT` as set in
 * `constants.h`.
 *
 * @return True when a new sample has been read and added to the moving
 * average. False otherwise, because it was not yet time to read out a new
 * sample.
 */
bool R_click_poll_EMA_collectively() {
  static bool at_startup = true;
  static uint32_t tick = micros();
  uint32_t now = micros();
  float alpha; // Derived smoothing factor of the exponential moving average

  if ((now - tick) >= DAQ_DT) {
    // Enough time has passed -> Acquire a new reading.
    // Calculate the smoothing factor every time because an exact time interval
    // is not garantueed.
    state.DAQ_obtained_DT = now - tick;
    alpha = 1.f - exp(-float(state.DAQ_obtained_DT) * DAQ_LP * 1e-6);

    if (at_startup) {
      at_startup = false;
      state.EMA_1 = R_click_1.read_bitval();
      state.EMA_2 = R_click_2.read_bitval();
      state.EMA_3 = R_click_3.read_bitval();
      state.EMA_4 = R_click_4.read_bitval();
    } else {
      // Block takes 94 µs @ 1 MHz SPI clock
      // utick = micros();
      state.EMA_1 += alpha * (R_click_1.read_bitval() - state.EMA_1);
      state.EMA_2 += alpha * (R_click_2.read_bitval() - state.EMA_2);
      state.EMA_3 += alpha * (R_click_3.read_bitval() - state.EMA_3);
      state.EMA_4 += alpha * (R_click_4.read_bitval() - state.EMA_4);
      // Serial.println(micros() - utick);
    }
    tick = now;
    return true;

  } else {
    return false;
  }
}

// -----------------------------------------------------------------------------
//  setup
// -----------------------------------------------------------------------------

void setup() {
  // To enable float support in `snprintf()` we must add the following
  asm(".global _printf_float");

  // Onboard LED & LED matrix
  //
  // NOTE:
  //   Don't call `FastLED.setMaxRefreshRate()`, because it will turn
  //   `FastLED.show()` into a blocking call.
  // NOTE:
  //   Type `NEOPIXEL` is internally `WS2812Controller800Khz`, so already
  //   running at the max clock frequency of 800 kHz.

  FastLED.addLeds<NEOPIXEL, PIN_NEOPIXEL>(onboard_led, 1);
  FastLED.addLeds<NEOPIXEL, PIN_LED_MATRIX>(leds, N_LEDS);
  FastLED.setCorrection(UncorrectedColor);
  // FastLED.setCorrection(TypicalSMD5050);
  FastLED.setBrightness(30);
  fill_solid(onboard_led, 1, CRGB::Blue);
  fill_rainbow(leds, N_LEDS, 0, 1);
  FastLED.show();

  Serial.begin(9600);
  // while (!Serial) {}

  Serial.println(F("@ setup"));
  Serial.print(F("Free mem: "));
  Serial.println(freeMemory());

  // Build reverse look-up table
  init_valve2p();

  // R Click
  R_click_1.begin();
  R_click_2.begin();
  R_click_3.begin();
  R_click_4.begin();

  // Centipedes
  //
  // Supported I2C clock speeds:
  //   MCP23017 datasheet: 100 kHz, 400 kHz, 1.7 MHz
  //   SAMD51   datasheet: 100 kHz, 400 kHz, 1 MHz, 3.4 MHz
  // Arduino's default I2C clock speed is 100 kHz.
  //
  // Resulting timings of the following code block:
  //   ```
  //   for (cp_port = 0; cp_port < 8; cp_port++) {
  //     cp.portWrite(cp_port, cp_data);
  //   }
  //   ```
  //   100 kHz: 3177 µs
  //   400 kHz:  908 µs
  //   1   MHz:  457 µs  <------- Chosen
  //   1.7 MHz: fails, too fast

  Wire.begin();
  Wire.setClock(1000000); // 1 MHz
#if DEVELOPER_MODE_WITHOUT_PERIPHERALS != 1
  cp_mgr.begin();
#endif

  // Finished setup, so clear all LEDs
  FastLED.clearData();
  FastLED.show();

  // ---------------------
  // Protocol manager test
  // ---------------------

  utick = micros();
  protocol_mgr.clear();
  Serial.println(micros() - utick);
  Serial.println(F("Cleared protocol"));

  utick = micros();
  // clang-format off
  /*
  // Clock-face style
  // ---------------------
  protocol_mgr.add_line(1000,
      Line{P{-6, 7}, P{-5, 6}, P{-4, 5}, P{-3, 4}, P{-2, 3}, P{-1, 2}, P{0, 1}});
  protocol_mgr.add_line(1000,
      Line{P{0, 7}, P{0, 5}, P{0, 3}, P{0, 1}});
  protocol_mgr.add_line(1000,
      Line{P{6, 7}, P{5, 6}, P{4, 5}, P{3, 4}, P{2, 3}, P{1, 2}, P{0, 1}});
  protocol_mgr.add_line(1000,
      Line{P{1, 0}, P{3, 0}, P{5, 0}, P{7, 0}});
  protocol_mgr.add_line(1000,
      Line{P{6, -7}, P{5, -6}, P{4, -5}, P{3, -4}, P{2, -3}, P{1, -2}, P{0, -1}});
  protocol_mgr.add_line(1000,
      Line{P{0, -1}, P{0, -3}, P{0, -5}, P{0, -7}});
  protocol_mgr.add_line(1000,
      Line{P{-6, -7}, P{-5, -6}, P{-4, -5}, P{-3, -4}, P{-2, -3}, P{-1, -2}, P{0, -1}});
  protocol_mgr.add_line(1000,
      Line{P{-7, 0}, P{-5, 0}, P{-3, 0}, P{-1, 0}});
  // ---------------------
  */
  // clang-format on

  // Growing center square
  // ---------------------
  for (uint8_t rung = 0; rung < 7; rung++) {
    Line line = {};
    uint8_t idx_P = 0;
    for (int8_t x = -7; x < 8; ++x) {
      for (int8_t y = -7; y < 8; ++y) {
        if ((x + y) & 1) {
          if (abs(x) + abs(y) == rung * 2 + 1) {
            line[idx_P].x = x;
            line[idx_P].y = y;
            idx_P++;
          }
        }
      }
    }
    protocol_mgr.add_line(500, line);
  }
  // ---------------------

  Serial.println(micros() - utick);
  Serial.println(F("Wrote protocol"));

  Serial.println(F("@ loop"));
  Serial.print(F("Free mem: "));
  Serial.println(freeMemory());
}

// -----------------------------------------------------------------------------
//  loop
// -----------------------------------------------------------------------------

void loop() {
  char *str_cmd; // Incoming serial command string
  uint32_t now;
  static uint32_t tick_program = 0; // Timestamp [ms] of last run protocol line
  uint16_t idx_valve;
  uint16_t idx_led;

  // ---------------------------------------------------------------------------
  //   Process incoming serial commands
  // ---------------------------------------------------------------------------

  EVERY_N_MILLISECONDS(50) {
    if (sc.available()) {
      str_cmd = sc.getCmd();

      if (strcmp(str_cmd, "id?") == 0) {
        Serial.println("Arduino, TWT jetting grid");
      }
    }
  }

  // ---------------------------------------------------------------------------
  //   Update R click readings
  // ---------------------------------------------------------------------------

#if DEVELOPER_MODE_WITHOUT_PERIPHERALS != 1
  if (R_click_poll_EMA_collectively()) {
    /*
    // DEBUG info: Show warning when obtained interval is too large
    if (state.DAQ_obtained_DT > DAQ_DT * 1.05) {
      Serial.print("WARNING: Large DAQ DT ");
      Serial.println(state.DAQ_obtained_DT);
    }
    */
  }
#endif

  // ---------------------------------------------------------------------------
  //   Report readings over serial
  // ---------------------------------------------------------------------------

  EVERY_N_MILLIS(1000) {
    /*
    static uint32_t t_start = 0;
    if (!t_start) {
      t_start = millis();
    }
    Serial.println(millis() - t_start);
    */

    state.pres_1_mA = R_click_1.bitval2mA(state.EMA_1);
    state.pres_2_mA = R_click_2.bitval2mA(state.EMA_2);
    state.pres_3_mA = R_click_3.bitval2mA(state.EMA_3);
    state.pres_4_mA = R_click_4.bitval2mA(state.EMA_4);
    state.pres_1_bar = mA2bar(state.pres_1_mA, OMEGA_1_CALIB);
    state.pres_2_bar = mA2bar(state.pres_2_mA, OMEGA_2_CALIB);
    state.pres_3_bar = mA2bar(state.pres_3_mA, OMEGA_3_CALIB);
    state.pres_4_bar = mA2bar(state.pres_4_mA, OMEGA_4_CALIB);

    // NOTE:
    //   Using `snprintf()` to print a large array of formatted values to a
    //   buffer followed by a single `Serial.print(buf)` is many times faster
    //   than multiple dumb `Serial.print(value, 3); Serial.write('\t')`
    //   statements. The latter is > 3400 µs, the former just ~ 320 µs !!!
    // clang-format off
    snprintf(buf, BUF_LEN,
             "%.2f\t%.2f\t%.2f\t%.2f\t\t"
             "%.3f\t%.3f\t%.3f\t%.3f\n",
             state.pres_1_mA,
             state.pres_2_mA,
             state.pres_3_mA,
             state.pres_4_mA,
             state.pres_1_bar,
             state.pres_2_bar,
             state.pres_3_bar,
             state.pres_4_bar);
    // clang-format on
    Serial.print(buf); // Takes 320 µs per call
    // Serial.println(FastLED.getFPS());
  }

  // Fade LED matrix. Keep in front of any other LED color assignments.
  // Only blue LEDs will fade.
  EVERY_N_MILLIS(20) {
    // utick = micros();
    for (idx_led = 0; idx_led < N_LEDS; idx_led++) {
      if (leds[idx_led].b) {
        fadeToBlackBy(&leds[idx_led], 1, 10);
      }
    }
    // Serial.println(micros() - utick);
  }

  // ---------------------------------------------------------------------------
  //   Handle the protocol program
  // ---------------------------------------------------------------------------

  now = millis();
  if (now - tick_program >= protocol_mgr.timed_line_buffer.duration) {
    // It is time to advance to the next line in the protocol program

    // Recolor any previously red LEDs to blue
    for (idx_led = 0; idx_led < N_LEDS; idx_led++) {
      if (leds[idx_led].r) {
        leds[idx_led] = CRGB(0, 0, leds[idx_led].r);
      }
    }

    // Read in the next line
    protocol_mgr.transfer_next_line_to_buffer();

    // Parse the line
    cp_mgr.clear_masks();
    for (auto &p : protocol_mgr.timed_line_buffer.line) {
      if (p.is_null()) {
        // Reached the end of the list as indicated by the end sentinel
        break;
      }

      idx_valve = p2valve(p);
      cp_mgr.add_to_masks(valve2cp(idx_valve));

      // Color all active valve LEDs in red
      idx_led = p2led(p);
      leds[idx_led] = CRGB::Red;
    }

    // Activate valves
#if DEVELOPER_MODE_WITHOUT_PERIPHERALS != 1
    cp_mgr.send_masks();
#endif

    tick_program = now;
  }

  // ---------------------------------------------------------------------------
  //   Send out LED data to the matrix
  // ---------------------------------------------------------------------------
  //
  // NOTE:
  //   It takes 30 µs to write to one WS2812 LED. Hence, for the full 16x16 LED
  //   matrix is takes 7680 µs. I actually measure 8000 µs, using
  //   '''
  //     utick = micros();
  //     FastLED.show();
  //     Serial.println(micros() - utick);
  //   '''
  //   Hence, we must limit the framerate to a theoretical max of 125 Hz in
  //   order to prevent flickering of the LEDs. Actually measured limit is
  //   <= 80 Hz.
  //
  // NOTE:
  //   Capping the framerate by calling `FastLED.setMaxRefreshRate(80)` is not
  //   advised, because this makes `FastLED.show()` blocking while it is waiting
  //   for the correct time to pass. Hence, we simply put the call to
  //   `FastLED.show()` inside an `EVERY_N_MILLIS()` call to leave it
  //   unblocking, while still capping the framerate.

  EVERY_N_MILLIS(500) {
    // Blink the 'alive' status LED
    leds[255] = alive_blinker ? CRGB::Green : CRGB::Black;
    onboard_led[0] = alive_blinker ? CRGB::Green : CRGB::Black;
    alive_blinker = !alive_blinker;
  }

  EVERY_N_MILLIS(20) {
    // utick = micros();
    FastLED.show(); // Takes 8003 µs per call
    // Serial.println("show");
    // Serial.println(micros() - utick);
  }
}
