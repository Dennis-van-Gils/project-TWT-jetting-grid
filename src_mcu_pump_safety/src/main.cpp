/**
 * @file    Main.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    21-11-2022
 *
 * @brief   Firmware for the pump safety microcontroller.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

/*------------------------------------------------------------------------------
  PURPOSE
--------------------------------------------------------------------------------

There are two microcontroller (MCU) boards used in the TWT jetting grid. The
main MCU (Adafruit M4 Feather Express) is responsible for driving the solenoid
valves and LED matrix and communicates via USB to the Python main program
running on a PC. The second MCU (Adafruit M0 Feather Express) acts as a safety
controller, governing the relay that allows turning the jetting pump on and off
via terminal X1 of its frequency inverter.

The main MCU should send a digital 'safety' pulse once every N ms over to the
safety MCU as indication that the main MCU is still operating all right. As long
as the safety MCU receives pulses within the set time period, the 'pump on'
relay will be engaged.
*/

#include "Adafruit_SleepyDog.h"
#include <Arduino.h>

const uint8_t PIN_PUMP_RELAY = 5;
const uint8_t PIN_SAFETY_PULSE_IN = A0;

const uint16_t SAFETY_PULSE_TIMEOUT = 100; // [ms]
const uint16_t WATCHDOG_TIMEOUT = 200;     // [ms]

volatile bool received_pulse = false;
void my_isr() { received_pulse = true; }

/*------------------------------------------------------------------------------
  setup
------------------------------------------------------------------------------*/

void setup() {
  pinMode(PIN_PUMP_RELAY, OUTPUT);
  digitalWrite(PIN_PUMP_RELAY, LOW);

  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH);

  pinMode(PIN_SAFETY_PULSE_IN, INPUT_PULLDOWN);
  attachInterrupt(digitalPinToInterrupt(PIN_SAFETY_PULSE_IN), my_isr, RISING);

  Watchdog.enable(WATCHDOG_TIMEOUT);
}

/*------------------------------------------------------------------------------
  loop
------------------------------------------------------------------------------*/

void loop() {
  uint32_t now = millis();
  static uint32_t tick_watchdog = now;
  static uint32_t tick_safety_pulse = now;
  static bool engage_relay = false;
  static bool prev_state_relay = false;

  noInterrupts();
  if (received_pulse) {
    received_pulse = false;
    tick_safety_pulse = now;
    engage_relay = true;
  }
  interrupts();

  if (now - tick_safety_pulse > SAFETY_PULSE_TIMEOUT) {
    engage_relay = false;
  }

  if (prev_state_relay != engage_relay) {
    digitalWrite(PIN_PUMP_RELAY, engage_relay);
    prev_state_relay = engage_relay;
  }

  if (now - tick_watchdog > 1) { // Slowed down, because of overhead otherwise
    Watchdog.reset();
    tick_watchdog = now;
  }
}