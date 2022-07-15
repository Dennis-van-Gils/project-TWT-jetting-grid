/*******************************************************************************
  TWT jetting grid

  https://github.com/Dennis-van-Gils/
  Dennis van Gils
  15-07-2022
*******************************************************************************/

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

#include "DvG_IIR_LP_DAQ.h"
#include "DvG_RT_Click_mA.h"
#include "DvG_SerialCommand.h"

// Serial command listener
DvG_SerialCommand sc(Serial);

// Common character buffer
#define BUFLEN 128
char buf[BUFLEN]{'\0'};

/*------------------------------------------------------------------------------
  MIKROE 4-20mA R click boards for reading out the OMEGA pressure sensors
------------------------------------------------------------------------------*/

// Cable Select pins
#define PIN_CS_PRESSURE_1 10
#define PIN_CS_PRESSURE_2 9
#define PIN_CS_PRESSURE_3 5
#define PIN_CS_PRESSURE_4 6

// Calibrated against a multimeter @ 14-07-2022 by DPM van Gils
R_Click R_click_1(PIN_CS_PRESSURE_1, 3.99, 791, 20.00, 3971);
R_Click R_click_2(PIN_CS_PRESSURE_2, 3.98, 784, 19.57, 3881);
R_Click R_click_3(PIN_CS_PRESSURE_3, 3.96, 774, 19.68, 3908);
R_Click R_click_4(PIN_CS_PRESSURE_4, 3.98, 828, 19.83, 3981);

// The R click boards fluctuate a lot in their read-outs and need to be
// oversampled and subsequently low-pass filtered.
#define DAQ_INTERVAL_MS 2  // Polling interval for readings [ms]
#define DAQ_LP_FILTER_Hz 2 // Low-pass filter cut-off frequency [Hz]

uint32_t read_R_click_1() { return R_click_1.read_bitval(); }
uint32_t read_R_click_2() { return R_click_2.read_bitval(); }
uint32_t read_R_click_3() { return R_click_3.read_bitval(); }
uint32_t read_R_click_4() { return R_click_4.read_bitval(); }

IIR_LP_DAQ R_click_1_DAQ(DAQ_INTERVAL_MS, DAQ_LP_FILTER_Hz, read_R_click_1);
IIR_LP_DAQ R_click_2_DAQ(DAQ_INTERVAL_MS, DAQ_LP_FILTER_Hz, read_R_click_2);
IIR_LP_DAQ R_click_3_DAQ(DAQ_INTERVAL_MS, DAQ_LP_FILTER_Hz, read_R_click_3);
IIR_LP_DAQ R_click_4_DAQ(DAQ_INTERVAL_MS, DAQ_LP_FILTER_Hz, read_R_click_4);

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

  if (R_click_1_DAQ.poll_update()) {
    state.pres_1_bitval = R_click_1_DAQ.get_value();
    state.pres_1_mA = R_click_1.bitval2mA(state.pres_1_bitval);

    // Taken from Omega calibration sheet supplied with pressure transducer
    // Serial: BG042821D030
    // Calibration job : WHS0059544
    // Calibration date: 30-03-22022
    state.pres_1_bar = (state.pres_1_mA - 4.035) / 16.015 * 7.0;
  }

  if (R_click_2_DAQ.poll_update()) {
    state.pres_2_bitval = R_click_2_DAQ.get_value();
    state.pres_2_mA = R_click_2.bitval2mA(state.pres_2_bitval);

    // Taken from Omega calibration sheet supplied with pressure transducer
    // Serial: BG042821D032
    // Calibration job : WHS0059544
    // Calibration date: 30-03-22022
    state.pres_2_bar = (state.pres_2_mA - 4.024) / 16.002 * 7.0;
  }

  if (R_click_3_DAQ.poll_update()) {
    state.pres_3_bitval = R_click_3_DAQ.get_value();
    state.pres_3_mA = R_click_3.bitval2mA(state.pres_3_bitval);

    // Taken from Omega calibration sheet supplied with pressure transducer
    // Serial: BG042821D034
    // Calibration job : WHS0059544
    // Calibration date: 30-03-22022
    state.pres_3_bar = (state.pres_3_mA - 4.004) / 16.057 * 7.0;
  }

  if (R_click_4_DAQ.poll_update()) {
    state.pres_4_bitval = R_click_4_DAQ.get_value();
    state.pres_4_mA = R_click_4.bitval2mA(state.pres_4_bitval);

    // Taken from Omega calibration sheet supplied with pressure transducer
    // Serial: BG042821D041
    // Calibration job : WHS0059544
    // Calibration date: 30-03-22022
    state.pres_4_bar = (state.pres_4_mA - 3.995) / 16.001 * 7.0;
  }

  if (now - tick > 1000) {
    tick = now;

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
