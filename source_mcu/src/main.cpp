/*
TWT jetting grid

https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
Dennis van Gils
28-07-2022
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

#include <algorithm>
using namespace std;

// Serial command listener
DvG_SerialCommand sc(Serial);

// Common character buffer
#define BUFLEN 128
char buf[BUFLEN]{'\0'};

// DEBUG: timer
uint32_t utick = micros();

/*------------------------------------------------------------------------------
  LED matrix, 16x16 RGB NeoPixel (Adafruit #2547)
  WS2812 or SK6812 type
------------------------------------------------------------------------------*/

CRGB leds[LED_COUNT];

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
  FastLED.addLeds<NEOPIXEL, PIN_LED_MATRIX>(leds, LED_COUNT);
  FastLED.setCorrection(UncorrectedColor);
  // FastLED.setCorrection(TypicalSMD5050);
  FastLED.setBrightness(150);
  fill_rainbow(leds, LED_COUNT, 0, 1);
  FastLED.show();

  Serial.begin(9600);
  // while (!Serial) {}

  // Populate reverse look-up table MATRIX_VALVE2PCS from source
  // MATRIX_PCS2VALVE.
  // dim 1: Valve number [1 - 112], valve 0 is special case
  // dim 2: PCS axis [0: x, 1: y]
  // Initialize matrix with a value of -128 to be able to check if no valves are
  // missing from the reverser look-up table.
  std::fill(*MATRIX_VALVE2PCS, *MATRIX_VALVE2PCS + 113 * 2, -128);
  for (int8_t y = 7; y > -8; y--) {
    for (int8_t x = -7; x < 8; x++) {
      uint8_t valve = MATRIX_PCS2VALVE[7 - y][x + 7];
      if (valve > 0) {
        MATRIX_VALVE2PCS[valve][0] = x;
        MATRIX_VALVE2PCS[valve][1] = y;
        Serial.print(valve);
        Serial.write('\t');
        Serial.print(x);
        Serial.write('\t');
        Serial.println(y);
      }
    }
  }

  // Check if all valves are accounted for
  bool inverse_lookup_okay = true;
  int8_t x;
  int8_t y;
  Serial.println("\nCheckup\n_______");
  for (uint8_t valve = 1; valve < 113; valve++) {
    x = MATRIX_VALVE2PCS[valve][0];
    y = MATRIX_VALVE2PCS[valve][1];
    Serial.print(valve);
    Serial.write('\t');
    if ((x == -128) || (y == -128)) {
      inverse_lookup_okay = false;
      Serial.println("ERROR: Missing valve index!");
    } else {
      Serial.print(x);
      Serial.write('\t');
      Serial.println(y);
    }
  }

  if (!inverse_lookup_okay) {
    Serial.println("ERROR: Invalid lookup table");
    while (1) {}
  }

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

int8_t pcs_x = -7;
int8_t pcs_y = 7;

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
      // Serial.print("WARNING: Large EMA DT ");
      // Serial.println(EMA_obtained_interval);
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
    snprintf(buf, BUFLEN,
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
    // Serial.print(buf); // Takes 320 µs per call

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
  EVERY_N_MILLIS(20) { fadeToBlackBy(leds, LED_COUNT, 5); }
  /*
  EVERY_N_MILLIS(100) {
    leds[idx_led] = CRGB::Red;
    idx_led++;
  }
  */

  // Centipedes
  // For-loop takes 457 µs in total @ 1 MHz I2C clock
  EVERY_N_MILLIS(100) {
    // utick = micros();

    // Fade any previous red pixels as blue
    for (idx_led = 0; idx_led < LED_COUNT; idx_led++) {
      if (leds[idx_led].r > 0) {
        leds[idx_led] = CRGB(0, 0, leds[idx_led].r);
      }
    }

    /*
    // Progress PCS coordinates
    idx_valve = PCS2valve(pcs_x, pcs_y);
    */

    pcs_x = valve2PCS_x(idx_valve);
    pcs_y = valve2PCS_y(idx_valve);

    cp_port = valve2cp_port(idx_valve);
    cp_value = valve2cp_bit(idx_valve);

    Serial.print("valve: ");
    Serial.print(idx_valve);
    Serial.print(" @ cp ");
    Serial.print(cp_port);
    Serial.print(", ");
    Serial.println(cp_value);

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

    // Serial.println(micros() - utick);

    /*
    // Progress PCS coordinates
    pcs_x++;
    if (pcs_x == 8) {
      pcs_x = -7;
      pcs_y--;
      if (pcs_y == -8) {
        pcs_y = 7;
      }
    }
    */

    idx_valve++;
    if (idx_valve > 112) {
      idx_valve = 1;
    }

    // Color leds
    idx_led = PCS2LED(pcs_x, pcs_y);
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
