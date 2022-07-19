/*
TWT jetting grid

https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
Dennis van Gils
19-07-2022
*/

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

#include "DvG_RT_Click_mA.h"
#include "DvG_SerialCommand.h"
#include "constants.h"

// Serial command listener
DvG_SerialCommand sc(Serial);

// Common character buffer
#define BUFLEN 128
char buf[BUFLEN]{'\0'};

/*------------------------------------------------------------------------------
  MIKROE 4-20 mA R click boards for reading out the OMEGA pressure sensors
------------------------------------------------------------------------------*/

R_Click R_click_1(PIN_R_CLICK_1, R_CLICK_1_CALIB, DAQ_DT, DAQ_LP);
R_Click R_click_2(PIN_R_CLICK_2, R_CLICK_2_CALIB, DAQ_DT, DAQ_LP);
R_Click R_click_3(PIN_R_CLICK_3, R_CLICK_3_CALIB, DAQ_DT, DAQ_LP);
R_Click R_click_4(PIN_R_CLICK_4, R_CLICK_4_CALIB, DAQ_DT, DAQ_LP);

/*------------------------------------------------------------------------------
  Holds actuator states and sensor readings
------------------------------------------------------------------------------*/

struct State {
  // OMEGA pressure sensors
  float pres_1_bitval = NAN; // [0-4095]
  float pres_2_bitval = NAN; // [0-4095]
  float pres_3_bitval = NAN; // [0-4095]
  float pres_4_bitval = NAN; // [0-4095]
  float pres_1_mA = NAN;     // [mA]
  float pres_2_mA = NAN;     // [mA]
  float pres_3_mA = NAN;     // [mA]
  float pres_4_mA = NAN;     // [mA]
  float pres_1_bar = NAN;    // [bar]
  float pres_2_bar = NAN;    // [bar]
  float pres_3_bar = NAN;    // [bar]
  float pres_4_bar = NAN;    // [bar]
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

// -----------------------------------------------------------------------------
//  setup
// -----------------------------------------------------------------------------

void setup() {
  // To enable float support in `snprintf()` we must add the following
  asm(".global _printf_float");

  Serial.begin(9600);

  R_click_1.begin();
  R_click_2.begin();
  R_click_3.begin();
  R_click_4.begin();

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

void loop() {
  char *str_cmd; // Incoming serial command string
  uint32_t now = millis();
  static uint32_t tick = now;

  // Process incoming serial commands
  if (sc.available()) {
    str_cmd = sc.getCmd();

    if (strcmp(str_cmd, "id?") == 0) {
      Serial.println("Arduino, TWT jetting grid");
    }
  }

  // ---------------------------------------------------------------------------
  //   Update R click readings
  // ---------------------------------------------------------------------------

  if (R_click_1.poll_oversampling()) {
    // DEBUG: Show obtained DT interval
    // Serial.println(R_click_1.get_last_obtained_DAQ_DT());
  }
  R_click_2.poll_oversampling();
  R_click_3.poll_oversampling();
  R_click_4.poll_oversampling();

  if (now - tick > 1000) {
    tick = now;

    state.pres_1_bitval = R_click_1.get_LP_bitval();
    state.pres_2_bitval = R_click_2.get_LP_bitval();
    state.pres_3_bitval = R_click_3.get_LP_bitval();
    state.pres_4_bitval = R_click_4.get_LP_bitval();
    state.pres_1_mA = R_click_1.get_LP_mA();
    state.pres_2_mA = R_click_2.get_LP_mA();
    state.pres_3_mA = R_click_3.get_LP_mA();
    state.pres_4_mA = R_click_4.get_LP_mA();
    state.pres_1_bar = mA2bar(state.pres_1_mA, OMEGA_1_CALIB);
    state.pres_2_bar = mA2bar(state.pres_2_mA, OMEGA_2_CALIB);
    state.pres_3_bar = mA2bar(state.pres_3_mA, OMEGA_3_CALIB);
    state.pres_4_bar = mA2bar(state.pres_4_mA, OMEGA_4_CALIB);

    // clang-format off
    snprintf(buf, BUFLEN,
             "%.1f\t%.1f\t%.1f\t%.1f\t\t"
             "%.2f\t%.2f\t%.2f\t%.2f\t\t"
             "%.3f\t%.3f\t%.3f\t%.3f\n",
             state.pres_1_bitval,
             state.pres_2_bitval,
             state.pres_3_bitval,
             state.pres_4_bitval,
             state.pres_1_mA,
             state.pres_2_mA,
             state.pres_3_mA,
             state.pres_4_mA,
             state.pres_1_bar,
             state.pres_2_bar,
             state.pres_3_bar,
             state.pres_4_bar);
    // clang-format on

    Serial.print(buf);
  }

  /*
  // Set RGB LED back to dim green: Measurement is done
  if (neo_flash && (now - t_neo_flash >= NEO_FLASH_DURATION)) {
    neo_flash = false;
    neo.setPixelColor(0, neo.Color(0, NEO_DIM, 0));
    neo.show();
  }
  */
}
