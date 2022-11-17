/**
 * @file    Main.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    21-10-2022
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

#include "Adafruit_SleepyDog.h"
#include "DvG_StreamCommand.h"
#include "FastLED.h"
#include "FiniteStateMachine.h"
#include "MIKROE_4_20mA_RT_Click.h"
#include "MemoryFree.h"
#include "halt.h"

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <array>

// Serial port listener for receiving ASCII commands
const uint8_t CMD_BUF_LEN = 64;  // Length of the ASCII command buffer
char cmd_buf[CMD_BUF_LEN]{'\0'}; // The ASCII command buffer
char *str_cmd;                   // Incoming serial ASCII-command string
DvG_StreamCommand sc(Serial, cmd_buf, CMD_BUF_LEN);

// Serial port listener for receiving binary data decoding a protocol program
const uint8_t BIN_BUF_LEN = 229;          // Length of the binary data buffer
uint8_t bin_buf[BIN_BUF_LEN];             // The binary data buffer
const uint8_t EOL[] = {0xff, 0xff, 0xff}; // End-of-line sentinel
DvG_BinaryStreamCommand bsc(Serial, bin_buf, BIN_BUF_LEN, EOL, sizeof(EOL));

// Will be used externally
const uint8_t BUF_LEN = 128; // Common character buffer for string formatting
char buf[BUF_LEN]{'\0'};     // Common character buffer for string formatting

// Debugging flags
const bool DEBUG = false;  // Print debug info over serial?
uint32_t utick = micros(); // DEBUG timer

// DEBUG: Allows developing code on a bare Arduino without sensors & actuators
// attached
#define DEVELOPER_MODE_WITHOUT_PERIPHERALS 0

/*------------------------------------------------------------------------------
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager protocol_mgr;

/*------------------------------------------------------------------------------
  Readings
------------------------------------------------------------------------------*/

struct Readings {
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
Readings readings; // Structure holding the sensor readings and actuator states

/*------------------------------------------------------------------------------
  Macetech Centipede boards
------------------------------------------------------------------------------*/

// One object controls both Centipede boards over ports 0 to 7
CentipedeManager cp_mgr;

/*------------------------------------------------------------------------------
  LEDs
------------------------------------------------------------------------------*/

bool alive_blinker = true; // Blinker for the 'alive' status LED
CRGB alive_blinker_color = CRGB::Green;
CRGB onboard_led[1]; // Onboard NeoPixel of the Adafruit Feather M4 board
CRGB leds[N_LEDS];   // LED matrix, 16x16 RGB NeoPixel (Adafruit #2547)
uint16_t idx_led;    // Frequently used LED index

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
  uint32_t now_us = micros();
  float alpha; // Derived smoothing factor of the exponential moving average

  if ((now_us - tick) >= DAQ_DT) {
    // Enough time has passed -> Acquire a new reading.
    // Calculate the smoothing factor every time because an exact time interval
    // is not garantueed.
    readings.DAQ_obtained_DT = now_us - tick;
    alpha = 1.f - exp(-float(readings.DAQ_obtained_DT) * DAQ_LP * 1e-6);

    if (at_startup) {
      at_startup = false;
      readings.EMA_1 = R_click_1.read_bitval();
      readings.EMA_2 = R_click_2.read_bitval();
      readings.EMA_3 = R_click_3.read_bitval();
      readings.EMA_4 = R_click_4.read_bitval();
    } else {
      // Block takes 94 µs @ 1 MHz SPI clock
      // utick = micros();
      readings.EMA_1 += alpha * (R_click_1.read_bitval() - readings.EMA_1);
      readings.EMA_2 += alpha * (R_click_2.read_bitval() - readings.EMA_2);
      readings.EMA_3 += alpha * (R_click_3.read_bitval() - readings.EMA_3);
      readings.EMA_4 += alpha * (R_click_4.read_bitval() - readings.EMA_4);
      // Serial.println(micros() - utick);
    }
    tick = now_us;
    return true;

  } else {
    return false;
  }
}

/*------------------------------------------------------------------------------
  immediately_open_all_valves
------------------------------------------------------------------------------*/

void immediately_open_all_valves() {
  cp_mgr.clear_masks();
  for (uint8_t idx_valve = 0; idx_valve < N_VALVES; ++idx_valve) {
    cp_mgr.add_to_masks(valve2cp(idx_valve + 1));
    leds[p2led(valve2p(idx_valve + 1))] = CRGB::Red;
  }

#if DEVELOPER_MODE_WITHOUT_PERIPHERALS == 0
  cp_mgr.send_masks(); // Activate valves
#endif
  FastLED.show();
}

/*------------------------------------------------------------------------------
  set_LED_matrix_fixed_grid_nodes
------------------------------------------------------------------------------*/

void set_LED_matrix_fixed_grid_nodes() {
  // Set LED colors at PCS points without a valve to yellow
  for (int8_t x = PCS_X_MIN; x <= PCS_X_MAX; x++) {
    for (int8_t y = PCS_Y_MIN; y <= PCS_Y_MAX; y++) {
      if ((x + y) % 2 == 0) {
        leds[p2led(P{x, y})] = CRGB::Yellow;
      }
    }
  }
  // Set LED color at PCS center point to off-white
  leds[p2led(P{0, 0})] = CRGB::DarkSalmon;
}

/*------------------------------------------------------------------------------
  Finite state machine
------------------------------------------------------------------------------*/

uint32_t now;              // Timestamp [ms]
uint32_t tick_program = 0; // Timestamp [ms] of last run protocol line
uint8_t idx_valve;         // Frequently used valve index

// Switches the ASCII-command listener momentarily off to allow for loading in a
// new protocol program via a binary-command listener.
bool loading_program = false;

/*------------------------------------------------------------------------------
  FSM: Idle

  Leaving any previously activated valves untouched
------------------------------------------------------------------------------*/

void fun_idle__ent();
void fun_idle__upd();
State state_idle(fun_idle__ent, fun_idle__upd);
FiniteStateMachine fsm(state_idle);

void fun_idle__ent() {
  Serial.println("State: Idling...");
  alive_blinker_color = CRGB::Yellow;
}

void fun_idle__upd() {}

/*------------------------------------------------------------------------------
  FSM: Single valve mode
------------------------------------------------------------------------------*/

// void fun_single_valve__upd() {}

/*------------------------------------------------------------------------------
  FSM: Run program

  Run the protocol program, advancing line for line when it is time.
  Will activate solenoid valves and will drive the LED matrix.
------------------------------------------------------------------------------*/

void fun_run_program__ent();
void fun_run_program__upd();
State state_run_program(fun_run_program__ent, fun_run_program__upd);

void fun_run_program__ent() {
  Serial.println("State: Running protocol program...");
  alive_blinker_color = CRGB::Green;

  // Clear all valve leds
  for (idx_valve = 0; idx_valve < N_VALVES; ++idx_valve) {
    leds[p2led(valve2p(idx_valve + 1))] = 0;
  }
}

void fun_run_program__upd() {
  now = millis();
  if (now - tick_program >= protocol_mgr.line_buffer.duration) {
    // It is time to advance to the next line in the protocol program

    // Recolor the LEDs of previously active valves from red to blue
    for (auto &p : protocol_mgr.line_buffer.points) {
      if (p.is_null()) {
        break;
      }
      leds[p2led(p)] = CRGB::Blue;
    }

    // Read in the next line
    protocol_mgr.transfer_next_line_to_buffer();
    Serial.println(protocol_mgr.get_position());
    if (DEBUG) {
      protocol_mgr.print_buffer(Serial);
    }

    // Parse the line
    cp_mgr.clear_masks();
    for (auto &p : protocol_mgr.line_buffer.points) {
      if (p.is_null()) {
        break; // Reached the end sentinel
      }

      // Add valve to be opened to the Centipede masks
      idx_valve = p2valve(p);
      cp_mgr.add_to_masks(valve2cp(idx_valve));

      // Color all active valve LEDs in red
      leds[p2led(p)] = CRGB::Red;
    }

#if DEVELOPER_MODE_WITHOUT_PERIPHERALS == 0
    cp_mgr.send_masks(); // Activate valves
#endif

    tick_program = now;
  }
}

/*------------------------------------------------------------------------------
  FSM: Load program

  Load a new protocol program into Arduino memory
------------------------------------------------------------------------------*/

// Stage 0: Load in via ASCII the name of the protocol program.
// Stage 1: Load in via ASCII the total number of protocol lines to be send.
// Stage 2: Load in via binary the protocol program line-by-line until the
//          end-of-program (EOP) sentinel is received. The EOP is signalled by
//          receiving two end-of-line (EOL) sentinels directly after each other.
uint8_t loading_stage = 0;

void fun_load_program__ent();
void fun_load_program__upd();
State state_load_program(fun_load_program__ent, fun_load_program__upd);

void fun_load_program__ent() {
  Serial.println("State: Loading in protocol program...");
  alive_blinker_color = CRGB::Blue;

  immediately_open_all_valves();
  loading_program = true;
  loading_stage = 0;
  protocol_mgr.clear();
}

void fun_load_program__upd() {
  static uint16_t promised_N_lines;
  Line line;

  if (loading_stage == 0) {
    // Load in via ASCII the name of the protocol program
    if (sc.available()) {
      str_cmd = sc.getCommand();
      protocol_mgr.set_name(str_cmd);
      Serial.println(protocol_mgr.get_name()); // Echo the name back
      loading_stage++;
    }
  }

  if (loading_stage == 1) {
    // Load in via ASCII the total number of protocol lines to be send
    if (sc.available()) {
      str_cmd = sc.getCommand();
      promised_N_lines = atoi(str_cmd);

      if (promised_N_lines <= PROTOCOL_MAX_LINES) {
        Serial.println("Loading stage 1: Success");
        loading_stage++;
      } else {
        // Protocol program will not fit inside pre-allocated memory
        snprintf(buf, BUF_LEN,
                 "ERROR: Protocol program exceeds maximum number of lines. "
                 "Requested was %d, but maximum is %d.",
                 promised_N_lines, PROTOCOL_MAX_LINES);
        Serial.println(buf);
        loading_program = false;
        fsm.transitionTo(state_idle);
        return;
      }
    }
  }

  if (loading_stage == 2) {
    // Load in via binary the protocol program line-by-line

    // Binary stream command availability status
    int8_t bsc_available = bsc.available();
    if (bsc_available == -1) {
      halt(8, "Stream command buffer overrun in `load_program()`");
    }

    if (bsc_available) {
      // Incoming binary data length in bytes
      uint16_t data_len = bsc.getCommandLength();

      if (data_len == 0) {
        // Found just the EOL sentinel without further information on the line
        // --> This signals the end-of-program EOP.
        if (DEBUG) {
          Serial.println("Found EOP");
        }

        // Check if the number of received lines matches the expectation
        if (protocol_mgr.get_N_lines() == promised_N_lines) {
          Serial.println("Loading stage 2: Success");
        } else {
          snprintf(buf, BUF_LEN,
                   "ERROR: Protocol program received incorrect number of "
                   "lines. Promised was %d, but received %d.",
                   promised_N_lines, protocol_mgr.get_N_lines());
          Serial.println(buf);
          protocol_mgr.clear();
        }

        // Exit
        loading_program = false;
        fsm.transitionTo(state_idle);
        return;
      }

      // Try to parse the newly send line of the protocol program
      // Expecting a binary stream as follows:
      // 1 x 2 bytes: uint16_t time duration in [ms]
      // N x 1 byte : byte-encoded PCS coordinate where
      //              upper 4 bits = PCS.x, lower 4 bits = PCS.y
      line.duration = (uint16_t)bin_buf[0] << 8 | //
                      (uint16_t)bin_buf[1];

      uint16_t idx_P = 0; // Index of newly unpacked point
      for (uint16_t idx = 2; idx < data_len; ++idx) {
        line.points[idx_P].unpack_byte(bin_buf[idx]);
        idx_P++;
      }
      line.points[idx_P].set_null(); // Add end sentinel

      protocol_mgr.add_line(line);
      if (DEBUG) {
        line.print();
      }
    }
  }

  // Time-out check
  const uint16_t LOADING_TIMEOUT = 4000; // [ms]
  if (fsm.timeInCurrentState() > LOADING_TIMEOUT) {
    // Exit
    Serial.println("ERROR: Loading in protocol program timed out.");
    loading_program = false;
    fsm.transitionTo(state_idle);
  }
}

/*------------------------------------------------------------------------------
  setup
------------------------------------------------------------------------------*/

void setup() {
  // To enable float support in `snprintf()` we must add the following
  asm(".global _printf_float");

  // Watchdog timer
  Watchdog.enable(WATCHDOG_TIMEOUT);

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
  if (DEBUG) {
    while (!Serial) {}
    Serial.print("Free mem @ setup: ");
    Serial.println(freeMemory());
  }

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
#if DEVELOPER_MODE_WITHOUT_PERIPHERALS == 0
  cp_mgr.begin();
#endif

  // Finished setup, so prepare LED matrix for regular operation
  FastLED.clearData();
  set_LED_matrix_fixed_grid_nodes();
  FastLED.show();

  // ---------------------
  // Protocol manager
  // ---------------------

  protocol_mgr.clear();

  /*
  // DEMO: Growing center square
  // ---------------------------
  Line line;

  for (uint8_t rung = 0; rung < 7; rung++) {
    uint8_t idx_P = 0;
    for (int8_t x = -7; x < 8; ++x) {
      for (int8_t y = -7; y < 8; ++y) {
        if ((x + y) & 1) {
          if (abs(x) + abs(y) == rung * 2 + 1) {
            line.points[idx_P].set(x, y);
            line.duration = 200; // [ms]
            idx_P++;
          }
        }
      }
    }
    line.points[idx_P].set_null(); // Add end sentinel
    protocol_mgr.add_line(line);
  }

  protocol_mgr.set_name("Demo growing center square");
  // ---------------------------
  */

  // DEMO: Single valve run
  // ---------------------------
  Line line;

  for (uint8_t idx_P = 0; idx_P < N_VALVES; idx_P++) {
    line.points[idx_P] = valve2p(idx_P + 1);
    line.duration = 200; // [ms]
    protocol_mgr.add_line(line);
  }
  line.points[N_VALVES].set_null(); // Add end sentinel
  protocol_mgr.add_line(line);

  protocol_mgr.set_name("Demo single valve run");
  // ---------------------------

  if (DEBUG) {
    Serial.print("Free mem @ loop : ");
    Serial.println(freeMemory());
  }
}

/*------------------------------------------------------------------------------
  loop
------------------------------------------------------------------------------*/

void loop() {
  EVERY_N_SECONDS(1) { // Slowed down, because of overhead otherwise
    Watchdog.reset();
  }

  // ---------------------------------------------------------------------------
  //   Process incoming serial commands
  // ---------------------------------------------------------------------------

  if (!loading_program) {
    EVERY_N_MILLISECONDS(10) {
      if (sc.available()) {
        str_cmd = sc.getCommand();

        if (strcmp(str_cmd, "id?") == 0) {
          // Report identity
          Serial.println("Arduino, TWT jetting grid");

        } else if (strcmp(str_cmd, "on") == 0) {
          fsm.transitionTo(state_run_program);

        } else if (strcmp(str_cmd, "off") == 0) {
          fsm.transitionTo(state_idle);

        } else if (strcmp(str_cmd, "load") == 0) {
          fsm.transitionTo(state_load_program);

        } else if (strcmp(str_cmd, "pos?") == 0) {
          // Print current protocol program position to serial
          snprintf(buf, BUF_LEN, "%d of %d\n", protocol_mgr.get_position(),
                   protocol_mgr.get_N_lines() - 1);
          Serial.print(buf);

        } else if (strcmp(str_cmd, "b?") == 0) {
          // Print current line buffer to serial, useful for debugging
          Serial.println("Line buffer");
          Serial.println("-----------");
          protocol_mgr.print_buffer();

        } else if (strcmp(str_cmd, "p?") == 0) {
          // Print current protocol program to serial
          protocol_mgr.print_program();

        } else if (strcmp(str_cmd, "halt") == 0) {
          // Trigger a halt, useful for debugging
          halt(0, "Halted by user command.");

        } else if (strcmp(str_cmd, "?") == 0) {
          // Report pressure readings

#if DEVELOPER_MODE_WITHOUT_PERIPHERALS == 0
          readings.pres_1_mA = R_click_1.bitval2mA(readings.EMA_1);
          readings.pres_2_mA = R_click_2.bitval2mA(readings.EMA_2);
          readings.pres_3_mA = R_click_3.bitval2mA(readings.EMA_3);
          readings.pres_4_mA = R_click_4.bitval2mA(readings.EMA_4);
          readings.pres_1_bar = mA2bar(readings.pres_1_mA, OMEGA_1_CALIB);
          readings.pres_2_bar = mA2bar(readings.pres_2_mA, OMEGA_2_CALIB);
          readings.pres_3_bar = mA2bar(readings.pres_3_mA, OMEGA_3_CALIB);
          readings.pres_4_bar = mA2bar(readings.pres_4_mA, OMEGA_4_CALIB);
#else
          // Generate fake pressure data
          float sin_value = 16.f + sin(2.f * PI * .1f * millis() / 1.e3f);
          readings.pres_1_mA = sin_value;
          readings.pres_2_mA = sin_value + .5;
          readings.pres_3_mA = sin_value + 1.;
          readings.pres_4_mA = sin_value + 1.5;
          readings.pres_1_bar = mA2bar(readings.pres_1_mA, OMEGA_1_CALIB);
          readings.pres_2_bar = mA2bar(readings.pres_2_mA, OMEGA_2_CALIB);
          readings.pres_3_bar = mA2bar(readings.pres_3_mA, OMEGA_3_CALIB);
          readings.pres_4_bar = mA2bar(readings.pres_4_mA, OMEGA_4_CALIB);
#endif

          // NOTE:
          //   Using `snprintf()` to print a large array of formatted values
          //   to a buffer followed by a single `Serial.print(buf)` is many
          //   times faster than multiple dumb `Serial.print(value, 3);
          //   Serial.write('\t')` statements. The latter is > 3400 µs, the
          //   former just ~ 320 µs !!!
          // clang-format off
          snprintf(buf, BUF_LEN,
                   "%.2f\t%.2f\t%.2f\t%.2f\t"
                   "%.3f\t%.3f\t%.3f\t%.3f\n",
                   readings.pres_1_mA,
                   readings.pres_2_mA,
                   readings.pres_3_mA,
                   readings.pres_4_mA,
                   readings.pres_1_bar,
                   readings.pres_2_bar,
                   readings.pres_3_bar,
                   readings.pres_4_bar);
          // clang-format on
          Serial.print(buf); // Takes 320 µs per call
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  //   Update R click readings
  // ---------------------------------------------------------------------------

#if DEVELOPER_MODE_WITHOUT_PERIPHERALS == 0
  if (R_click_poll_EMA_collectively()) {
    /*
    if (DEBUG) {
      // DEBUG info: Show warning when obtained interval is too large.
      // Not necessarily problematic though. The EMA will adjust for this.
      if (readings.DAQ_obtained_DT > DAQ_DT * 1.05) {
        Serial.print("WARNING: Large DAQ DT ");
        Serial.println(readings.DAQ_obtained_DT);
      }
    }
    */
  }
#endif

  // Fade out all purely blue LEDs over time, i.e. previously active valves.
  // Keep in front of any other LED color assignments.
  EVERY_N_MILLIS(20) {
    for (idx_led = 0; idx_led < N_LEDS; idx_led++) {
      if (leds[idx_led].b && !leds[idx_led].r && !leds[idx_led].g) {
        leds[idx_led].nscale8(255 - 10);
        // ↑ equivalent to but faster `fadeToBlackBy(&leds[idx_led], 1, 10);`
      }
    }
  }

  // ---------------------------------------------------------------------------
  //   Handle the finite state machine
  // ---------------------------------------------------------------------------

  fsm.update();

  // ---------------------------------------------------------------------------
  //   Send out LED data to the matrix
  // ---------------------------------------------------------------------------
  //
  // NOTE:
  //   It takes 30 µs to write to one WS2812 LED. Hence, for the full 16x16
  //   LED matrix is takes 7680 µs. I actually measure 8000 µs, using
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
  //   advised, because this makes `FastLED.show()` blocking while it is
  //   waiting for the correct time to pass. Hence, we simply put the call to
  //   `FastLED.show()` inside an `EVERY_N_MILLIS()` call to leave it
  //   unblocking, while still capping the framerate.

  EVERY_N_MILLIS(500) {
    // Blink the 'alive' status LEDs
    leds[255] = alive_blinker ? alive_blinker_color : CRGB::Black;
    onboard_led[0] = alive_blinker ? alive_blinker_color : CRGB::Black;
    alive_blinker = !alive_blinker;
  }

  EVERY_N_MILLIS(20) {
    // utick = micros();
    FastLED.show(); // Takes 8003 µs per call
    // Serial.println("show");
    // Serial.println(micros() - utick);
  }
}
