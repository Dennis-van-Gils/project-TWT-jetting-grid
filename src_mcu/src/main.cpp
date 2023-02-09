/**
 * @file    Main.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    09-02-2023
 *
 * @brief   Firmware for the main microcontroller of the TWT jetting grid. See
 * `constants.h` for a detailed description.
 *
 * This firmware is written with safety in mind:
 * 1) Out-of-bounds array operations are caught gracefully by displaying 'HALT'
 *    on the LED matrix and printing an error to the Serial console. The jetting
 *    pump will be disabled.
 * 2) When no solenoid valves are open the jetting pump will be disabled.
 * 3) Only when the MCU is running okay and at least a single solenoid valve is
 *    open, will safety pulses be send to the safety MCU, enabling the jetting
 *    pump.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#include "CentipedeManager.h"
#include "ProtocolManager.h"
#include "constants.h"
#include "protocol_program_presets.h"
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

// This flag controls whether safety pulses should be send out to the safety
// microcontroller, which in turn will engage the safety relay that enables the
// jetting pump. This flag is autonomously set to `false` when none of the
// valves are currently open. If any valve is open the flag is set to `true`.
// This safety procedure can be overriden by flag `override_pump_safety`.
bool safety__allow_jetting_pump_to_run = false;

// WARNING: Safety override to always allow the jetting pump to run.
bool override_pump_safety = false;

// Debugging flags
uint32_t utick = micros();         // DEBUG timer
const bool DEBUG = false;          // Print debug info over serial?
const bool NO_PERIPHERALS = false; // Allows developing code on a bare Arduino
                                   // without sensors & actuators attached

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
  ProtocolManager
------------------------------------------------------------------------------*/

ProtocolManager protocol_mgr(&cp_mgr);

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
  set_LED_matrix_data_fixed_grid
------------------------------------------------------------------------------*/

/**
 * @brief Set the LED colors at PCS points without a valve
 */
void set_LED_matrix_data_fixed_grid() {
  for (int8_t x = PCS_X_MIN; x <= PCS_X_MAX; x++) {
    for (int8_t y = PCS_Y_MIN; y <= PCS_Y_MAX; y++) {
      if ((x + y) % 2 == 0) {
        leds[p2led(P{x, y})] = CRGB(64, 64, 64);
      }
    }
  }
  leds[p2led(P{0, 0})] = CRGB(0, 32, 0); // Center (0, 0)
}

/*------------------------------------------------------------------------------
  Finite state machine
------------------------------------------------------------------------------*/

uint32_t now;      // Timestamp [ms]
uint8_t idx_valve; // Frequently used valve index

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
  // DEBUG: Necessary?
  for (idx_valve = 0; idx_valve < N_VALVES; ++idx_valve) {
    leds[p2led(valve2p(idx_valve + 1))] = 0;
  }
}

void fun_run_program__upd() { protocol_mgr.update(); }

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
bool loading_successful = false;

void fun_load_program__ent();
void fun_load_program__upd();
void fun_load_program__ext();
State state_load_program(fun_load_program__ent, fun_load_program__upd,
                         fun_load_program__ext);

void fun_load_program__ent() {
  Serial.println("State: Loading in protocol program...");
  alive_blinker_color = CRGB::Blue;

  loading_program = true;
  loading_stage = 0;
  loading_successful = false;
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
        }

        // Succesful exit
        loading_program = false;
        loading_successful = true;
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
    Serial.println("ERROR: Loading in protocol program timed out.");
    loading_program = false;
    fsm.transitionTo(state_idle);
  }
}

void fun_load_program__ext() {
  if (!loading_successful) {
    // Unsuccesful load --> Create a safe protocol program where all valves are
    // always open.
    protocol_mgr.clear();
    protocol_mgr.set_name("All valves open");

    Line line;
    line.duration = 1000; // [ms]
    for (idx_valve = 1; idx_valve <= N_VALVES; ++idx_valve) {
      line.points[idx_valve - 1] = valve2p(idx_valve);
    }
    line.points[N_VALVES].set_null(); // Add end sentinel
    protocol_mgr.add_line(line);
  }

  // Crucial to have the protocol program start at line 0. No valves will be
  // activated just yet. That will happen with the first call to
  // `protocol_mgr.update()`.
  protocol_mgr.prime_start();
}

/*------------------------------------------------------------------------------
  setup
------------------------------------------------------------------------------*/

void setup() {
  // To enable float support in `snprintf()` we must add the following
  asm(".global _printf_float");

  // Safety pulses to be send to the safety MCU
  pinMode(PIN_SAFETY_PULSE_OUT, OUTPUT);
  digitalWrite(PIN_SAFETY_PULSE_OUT, LOW);

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
  fill_rainbow(leds, N_LEDS, 0, 1); // Show rainbow during setup
  FastLED.show();

  Serial.begin(9600);
  if (DEBUG) {
    while (!Serial) {}
    Serial.print("Free mem @ setup: ");
    Serial.println(freeMemory());
  }

  // Build reverse look-up table to be able to translate valve indices to PCS
  // points using function `valve2p()`
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
  if (!NO_PERIPHERALS) {
    cp_mgr.begin();
  }

  // Load protocol program preset
  load_protocol_program_preset_0();

  // Reached the end of setup, so now show the fixed grid in the LED matrix
  FastLED.clearData();
  set_LED_matrix_data_fixed_grid(); // DEBUG: Taken out momentarily
  FastLED.show();

  if (DEBUG) {
    Serial.print("Free mem @ loop : ");
    Serial.println(freeMemory());
  }

  // Start Watchdog timer
  Watchdog.enable(WATCHDOG_TIMEOUT);
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
          // Play the program
          fsm.transitionTo(state_run_program);

        } else if (strcmp(str_cmd, "off") == 0) {
          // Pause the program
          fsm.transitionTo(state_idle);

        } else if (strcmp(str_cmd, "load") == 0) {
          // Load a new program via an incoming Serial stream send by the PC
          fsm.transitionTo(state_load_program);

        } else if (strcmp(str_cmd, "preset0") == 0) {
          // Load a preset program
          load_protocol_program_preset_0();

        } else if (strcmp(str_cmd, "preset1") == 0) {
          // Load a preset program
          load_protocol_program_preset_1();

        } else if (strcmp(str_cmd, "preset2") == 0) {
          // Load a preset program
          load_protocol_program_preset_2();

        } else if (strcmp(str_cmd, "preset3") == 0) {
          // Load a preset program
          load_protocol_program_preset_3();

        } else if (strcmp(str_cmd, ",") == 0) {
          // Go to the previous line of the protocol program and immediately
          // activate the solenoid valves and color the LED matrix.
          protocol_mgr.goto_prev_line();

        } else if (strcmp(str_cmd, ".") == 0) {
          // Go to the next line of the protocol program and immediately
          // activate the solenoid valves and color the LED matrix.
          protocol_mgr.goto_next_line();

        } else if (strncmp(str_cmd, "goto", 4) == 0) {
          // Go to the specified line of the protocol program and immediately
          // activate the solenoid valves and color the LED matrix.
          protocol_mgr.goto_line(parseIntInString(str_cmd, 4));

        } else if (strcmp(str_cmd, "pos?") == 0) {
          // Print current program position to serial
          snprintf(buf, BUF_LEN, "%d of %d\n", protocol_mgr.get_position(),
                   protocol_mgr.get_N_lines() - 1);
          Serial.print(buf);

        } else if (strcmp(str_cmd, "b?") == 0) {
          // Print current line buffer to serial, useful for debugging
          protocol_mgr.print_buffer();

        } else if (strcmp(str_cmd, "p?") == 0) {
          // Print current program to serial
          protocol_mgr.print_program();

        } else if (strcmp(str_cmd, "override_safety") == 0) {
          // WARNING: Will force the jetting pump to enabled, regardless of
          // whether any valves are actually open or not. This function should
          // be used for troubleshooting only.
          override_pump_safety = true;

        } else if (strcmp(str_cmd, "restore_safety") == 0) {
          // Revert back from the "override_safety" command and restore the
          // regular safety procedure to enable the jetting pump.
          override_pump_safety = false;

        } else if (strcmp(str_cmd, "halt") == 0) {
          // Trigger a halt, useful for debugging
          halt(0, "Halted by user command.");

        } else if (strcmp(str_cmd, "?") == 0) {
          // Report pressure readings

          if (!NO_PERIPHERALS) {
            readings.pres_1_mA = R_click_1.bitval2mA(readings.EMA_1);
            readings.pres_2_mA = R_click_2.bitval2mA(readings.EMA_2);
            readings.pres_3_mA = R_click_3.bitval2mA(readings.EMA_3);
            readings.pres_4_mA = R_click_4.bitval2mA(readings.EMA_4);
            readings.pres_1_bar = mA2bar(readings.pres_1_mA, OMEGA_1_CALIB);
            readings.pres_2_bar = mA2bar(readings.pres_2_mA, OMEGA_2_CALIB);
            readings.pres_3_bar = mA2bar(readings.pres_3_mA, OMEGA_3_CALIB);
            readings.pres_4_bar = mA2bar(readings.pres_4_mA, OMEGA_4_CALIB);
          } else {
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
          }

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

  if (!NO_PERIPHERALS) {
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
  }

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

  // ---------------------------------------------------------------------------
  //   Safety pulses
  // ---------------------------------------------------------------------------

  if (override_pump_safety) {
    // WARNING! SAFETY OVERRIDE! FOR DEBUGGING ONLY!
    safety__allow_jetting_pump_to_run = true;

  } else {
    // Final safety check in effect:
    // Don't allow the jetting pump to run when none of the valves are open
    if (cp_mgr.all_masks_are_zero()) {
      safety__allow_jetting_pump_to_run = false;
    } else {
      safety__allow_jetting_pump_to_run = true;
    }
  }

  if (safety__allow_jetting_pump_to_run) {
    // Send out safety pulses to the safety MCU
    EVERY_N_MILLIS(PERIOD_SAFETY_PULSES / 2) {
      // static uint32_t tick = millis();
      // Serial.print("----> ");
      // Serial.println(millis() - tick);
      // tick = millis();
      static bool toggler = false;
      toggler = !toggler;
      digitalWrite(PIN_SAFETY_PULSE_OUT, toggler);
    }
  }
}
