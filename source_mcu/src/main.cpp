/*
TWT jetting grid

https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
Dennis van Gils
03-08-2022
*/

/*
- Google CPP style guide:
https://google.github.io/styleguide/cppguide.html#Variable_Names
- FastLED API           : http://fastled.io/docs/3.1/index.html
*/

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

#include "Centipede.h"
#include "DvG_SerialCommand.h"
#include "FastLED.h"
#include "MIKROE_4_20mA_RT_Click.h"
#include "constants.h"

// Serial command listener
DvG_SerialCommand sc(Serial);

// Common character buffer
const uint8_t BUF_LEN = 128;
char buf[BUF_LEN]{'\0'};

// DEBUG: timer
uint32_t utick = micros();

/*------------------------------------------------------------------------------
  Holds actuator states and sensor readings
------------------------------------------------------------------------------*/

struct State {
  // OMEGA pressure sensors
  float pres_1_mA = NAN;  // [mA]
  float pres_2_mA = NAN;  // [mA]
  float pres_3_mA = NAN;  // [mA]
  float pres_4_mA = NAN;  // [mA]
  float pres_1_bar = NAN; // [bar]
  float pres_2_bar = NAN; // [bar]
  float pres_3_bar = NAN; // [bar]
  float pres_4_bar = NAN; // [bar]
};
State state;

/*------------------------------------------------------------------------------
  Macetech Centipede boards
------------------------------------------------------------------------------*/

// One object controls both Centipede boards over ports 0 to 7
uint8_t cp_port;
uint8_t cp_value;

uint16_t cp0_value = 0;
uint16_t cp1_value = 0;
uint16_t cp2_value = 0;
uint16_t cp3_value = 0;
uint16_t cp4_value = 0;
uint16_t cp5_value = 0;
uint16_t cp6_value = 0;
uint16_t cp7_value = 0;

Centipede cp;

/*------------------------------------------------------------------------------
  LED matrix, 16x16 RGB NeoPixel (Adafruit #2547)
  WS2812 or SK6812 type
------------------------------------------------------------------------------*/

CRGB leds[N_LEDS];

/*
// On-board NeoPixel RGB LED
#define NEO_DIM 3    // Brightness level for dim intensity [0 -255]
#define NEO_BRIGHT 6 // Brightness level for bright intensity [0 - 255]
#define NEO_FLASH_DURATION 100 // [ms]
bool neo_flash = false;
uint32_t t_neo_flash = 0;
Adafruit_NeoPixel neo(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
*/

/*------------------------------------------------------------------------------
  MIKROE 4-20 mA R click boards for reading out the OMEGA pressure sensors
------------------------------------------------------------------------------*/

R_Click R_click_1(PIN_R_CLICK_1, R_CLICK_1_CALIB);
R_Click R_click_2(PIN_R_CLICK_2, R_CLICK_2_CALIB);
R_Click R_click_3(PIN_R_CLICK_3, R_CLICK_3_CALIB);
R_Click R_click_4(PIN_R_CLICK_4, R_CLICK_4_CALIB);

uint32_t EMA_tick = micros();
uint32_t EMA_obtained_interval;
bool EMA_at_startup = true;
float EMA_1_bitval;
float EMA_2_bitval;
float EMA_3_bitval;
float EMA_4_bitval;

bool R_click_poll_EMA_collectively() {
  uint32_t now = micros();
  float alpha; // Derived smoothing factor of the exponential moving average

  if ((now - EMA_tick) >= DAQ_DT) {
    // Enough time has passed -> Acquire a new reading.
    // Calculate the smoothing factor every time because an exact interval time
    // is not garantueed.
    EMA_obtained_interval = now - EMA_tick;
    alpha = 1.f - exp(-float(EMA_obtained_interval) * DAQ_LP * 1e-6);

    if (EMA_at_startup) {
      EMA_at_startup = false;
      EMA_1_bitval = R_click_1.read_bitval();
      EMA_2_bitval = R_click_2.read_bitval();
      EMA_3_bitval = R_click_3.read_bitval();
      EMA_4_bitval = R_click_4.read_bitval();
    } else {
      // Block takes 94 µs @ 1   MHz SPI clock
      // Block takes 67 µs @ 1.7 MHz SPI clock
      // utick = micros();
      EMA_1_bitval += alpha * (R_click_1.read_bitval() - EMA_1_bitval);
      EMA_2_bitval += alpha * (R_click_2.read_bitval() - EMA_2_bitval);
      EMA_3_bitval += alpha * (R_click_3.read_bitval() - EMA_3_bitval);
      EMA_4_bitval += alpha * (R_click_4.read_bitval() - EMA_4_bitval);
      // Serial.println(micros() - utick);
    }
    EMA_tick = now;
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

  // LED matrix
  /*
  NOTE:
    Don't call `FastLED.setMaxRefreshRate()`, because it will turn
    `FastLED.show()` into a blocking call.

  NOTE:
    Type `NEOPIXEL` is internally `WS2812Controller800Khz`, so already running
    at the max clock frequency of 800 kHz
  */
  FastLED.addLeds<NEOPIXEL, PIN_LED_MATRIX>(leds, N_LEDS);
  FastLED.setCorrection(UncorrectedColor);
  // FastLED.setCorrection(TypicalSMD5050);
  FastLED.setBrightness(30);
  fill_rainbow(leds, N_LEDS, 0, 1);
  FastLED.show();

  Serial.begin(9600);
  // while (!Serial) {}

  init_valve2PCS();

  // R Click
  R_click_1.set_SPI_clock(1700000);
  R_click_2.set_SPI_clock(1700000);
  R_click_3.set_SPI_clock(1700000);
  R_click_4.set_SPI_clock(1700000);
  R_click_1.begin();
  R_click_2.begin();
  R_click_3.begin();
  R_click_4.begin();

  // Centipedes
  /*
  Supported I2C clock speeds:
    MCP23017 datasheet: 100 kHz, 400 kHz, 1.7 MHz
    SAMD51   datasheet: 100 kHz, 400 kHz, 1 MHz, 3.4 MHz
  Default I2C clock speed is 100 kHz.

  Resulting timings of the following code block:
    ```
    for (cp_port = 0; cp_port < 8; cp_port++) {
      cp.portWrite(cp_port, cp_data);
    }
    ```
    100 kHz: 3177 µs
    400 kHz:  908 µs
    1   MHz:  457 µs
    1.7 MHz: fails, too fast
  */
  Wire.begin();
  Wire.setClock(1000000); // 1 MHz
  cp.initialize();

  for (cp_port = 0; cp_port < 8; cp_port++) {
    cp.portMode(cp_port, 0);  // Set all channels to output
    cp.portWrite(cp_port, 0); // Set all channels LOW
  }

  /*
  // Set RGB LED to blue: We're setting up
  neo.begin();
  neo.setPixelColor(0, neo.Color(0, 0, NEO_BRIGHT));
  neo.show();

  // Set RGB LED to dim green: We're all ready to go and idle
  neo.setPixelColor(0, neo.Color(0, NEO_DIM, 0));
  neo.show();
  */
}

// -----------------------------------------------------------------------------
//  loop
// -----------------------------------------------------------------------------

PCS pcs{-7, 7};
uint16_t idx_valve = 1;
uint16_t idx_led = 0;

void loop() {
  char *str_cmd; // Incoming serial command string
  uint32_t now = millis();
  static uint32_t tick = now;
  static uint32_t tock = now;
  static uint32_t tack = now;

  /*
  // Process incoming serial commands
  if (now - tack > 50) {
    tack = now;
    if (sc.available()) {
      str_cmd = sc.getCmd();

      if (strcmp(str_cmd, "id?") == 0) {
        Serial.println("Arduino, TWT jetting grid");
      }
    }
  }
  */

  // ---------------------------------------------------------------------------
  //   Update R click readings
  // ---------------------------------------------------------------------------

  if (R_click_poll_EMA_collectively()) {
    // DEBUG: Alarm when obtained DT interval is too large
    if (EMA_obtained_interval > DAQ_DT * 1.05) {
      Serial.print("WARNING: Large EMA DT ");
      Serial.println(EMA_obtained_interval);
    } else {
      // Serial.println("*");
    }
  }

  if (now - tick > 1000) {
    tick = now;

    state.pres_1_mA = R_click_1.bitval2mA(EMA_1_bitval);
    state.pres_2_mA = R_click_2.bitval2mA(EMA_2_bitval);
    state.pres_3_mA = R_click_3.bitval2mA(EMA_3_bitval);
    state.pres_4_mA = R_click_4.bitval2mA(EMA_4_bitval);
    state.pres_1_bar = mA2bar(state.pres_1_mA, OMEGA_1_CALIB);
    state.pres_2_bar = mA2bar(state.pres_2_mA, OMEGA_2_CALIB);
    state.pres_3_bar = mA2bar(state.pres_3_mA, OMEGA_3_CALIB);
    state.pres_4_bar = mA2bar(state.pres_4_mA, OMEGA_4_CALIB);

    /*
    NOTE:
      Using `snprintf()` to print a large array of formatted values to a buffer
      followed by a single `Serial.print(buf)` is many times faster than
      multiple dumb `Serial.print(value, 3); Serial.write('\t')` statements. The
      former is ~ 320 µs, the latter > 3400 µs !!!
    */
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

  /*
  // Set RGB LED back to dim green: Measurement is done
  if (neo_flash && (now - t_neo_flash >= NEO_FLASH_DURATION)) {
    neo_flash = false;
    neo.setPixelColor(0, neo.Color(0, NEO_DIM, 0));
    neo.show();
  }
  */

  // Animate LED matrix
  EVERY_N_MILLIS(20) { fadeToBlackBy(leds, N_LEDS, 5); }

  // Centipedes
  // For-loop takes 457 µs in total @ 1 MHz I2C clock
  EVERY_N_MILLIS(100) {
    // utick = micros();

    // Fade any previous red pixels as blue
    for (idx_led = 0; idx_led < N_LEDS; idx_led++) {
      if (leds[idx_led].r > 0) {
        leds[idx_led] = CRGB(0, 0, leds[idx_led].r);
      }
    }

    /*
    // Progress PCS coordinates
    idx_valve = PCS2valve(pcs);
    */
    pcs = valve2PCS(idx_valve);

    if (idx_valve > 0) {
      cp_port = valve2cp_port(idx_valve);
      cp_value = valve2cp_bit(idx_valve);

      /*
      Serial.print("valve: ");
      Serial.print(idx_valve);
      Serial.print(" @ cp ");
      Serial.print(cp_port);
      Serial.print(", ");
      Serial.println(cp_value);
      */

      cp0_value = 0;
      cp1_value = 0;
      cp2_value = 0;
      cp3_value = 0;
      cp4_value = 0;
      cp5_value = 0;
      cp6_value = 0;
      cp7_value = 0;

      uint16_t foo = 0;
      bitSet(foo, cp_value);

      switch (cp_port) {
        case 0:
          cp0_value |= foo;
          break;
        case 1:
          cp1_value |= foo;
          break;
        case 2:
          cp2_value |= foo;
          break;
        case 3:
          cp3_value |= foo;
          break;
        case 4:
          cp4_value |= foo;
          break;
        case 5:
          cp5_value |= foo;
          break;
        case 6:
          cp6_value |= foo;
          break;
        case 7:
          cp7_value |= foo;
          break;
      }

      cp.portWrite(0, cp0_value);
      cp.portWrite(1, cp1_value);
      cp.portWrite(2, cp2_value);
      cp.portWrite(3, cp3_value);
      cp.portWrite(4, cp4_value);
      cp.portWrite(5, cp5_value);
      cp.portWrite(6, cp6_value);
      cp.portWrite(7, cp7_value);
    }

    // Serial.println(micros() - utick);

    /*
    // Progress PCS coordinates
    pcs.x++;
    if (pcs.x == 8) {
      pcs.x = -7;
      pcs.y--;
      if (pcs.y == -8) {
        pcs.y = 7;
      }
    }
    */

    ///*
    idx_valve++;
    if (idx_valve > 112) {
      idx_valve = 1;
    }
    //*/

    // Color leds
    idx_led = PCS2LED(pcs);
    leds[idx_led] = CRGB::Red;
  }

  // Send out LED data to the strip.
  /*
  NOTE:
    It takes 30 µs to write to one WS2812 LED. Hence, for the full 16x16 LED
    matrix is takes 7680 µs. I actually measure 8000 µs, using
    '''
      utick = micros();
      FastLED.show();
      Serial.println(micros() - utick);
    '''
    Hence, we must limit the framerate to a theoretical max of 125 Hz in order
    to prevent flickering of the LEDs. Actually measured limit is <= 80 Hz.

  NOTE:
    Capping the framerate by calling `FastLED.setMaxRefreshRate(80)` is not
    advised, because this makes `FastLED.show()` blocking while it is waiting
    for the correct time to pass. Hence, we simply put the call to
    `FastLED.show()` inside an `EVERY_N_MILLIS()` call to leave it unblocking,
    while still capping the framerate.
  */
  EVERY_N_MILLIS(20) {
    // utick = micros();
    FastLED.show(); // Takes 8003 µs per call
    // Serial.println("show");
    //  Serial.println(micros() - utick);
  }
}
