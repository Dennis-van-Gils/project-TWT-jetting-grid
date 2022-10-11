# MIKROE 4-20 mA R & T Click ![Latest release](https://img.shields.io/github/v/release/Dennis-van-Gils/MIKROE_4_20mA_RT_Click) [![License:MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://github.com/Dennis-van-Gils/MIKROE_4_20mA_RT_Click/blob/master/LICENSE) [![Documentation](https://img.shields.io/badge/Docs-Doxygen-blue)](https://dennis-van-gils.github.io/MIKROE_4_20mA_RT_Click)

An Arduino library for the 4-20 mA R & T Click Boards of MIKROE.

Supported:
- 4-20 mA R Click (MIKROE-1387)
    - 4-20 mA current loop receiver
    - MCP3201 12-bit ADC SPI chip
    - max SPI clock 1.6 MHz
    - max 100 ksps

- 4-20 mA T Click (MIKROE-1296)
    - 4-20 mA current loop transmitter
	- MCP4921 12-bit DAC SPI chip
	- max SPI clock 20 MHz
	- settling time of 4.5 μs

Single R Click readings tend to fluctuate a lot. To combat the large
fluctuations this library optionally provides an exponential moving average
(EMA) applied to the R Click readings. It does not rely on storing an array
of data and is hence very memory efficient.

It does this by oversampling the R Click readings at a user-supplied
interval. Subsequently, it will low-pass filter the readings using a
smoothing factor that is calculated from a user-supplied low-pass filter
cut-off frequency. Technically, the exponential moving average is a
single-pole infinite-impulse response (IIR) filter.

The API documentation can be found here: https://dennis-van-gils.github.io/MIKROE_4_20mA_RT_Click

# Example: T Click
```cpp
#include <Arduino.h>
#include "MIKROE_4_20mA_RT_Click.h"

// The cable select pin of the T Click
const uint8_t PIN_T_CLICK = 6;

// Adjust the calibration parameters as needed
T_Click T_click(PIN_T_CLICK, RT_Click_Calibration{4.02, 19.99, 800, 3980});

void setup() {
  Serial.begin(9600);
  T_click.begin();
  T_click.set_mA(12.);
}
```

# Example: R Click
```cpp
#include <Arduino.h>
#include "MIKROE_4_20mA_RT_Click.h"

// The cable select pin of the R Click
const uint8_t PIN_R_CLICK = 5;

// Adjust the calibration parameters as needed
R_Click R_click(PIN_R_CLICK, RT_Click_Calibration{4.03, 19.93, 832, 3999});

void setup() {
  Serial.begin(9600);
  R_click.begin();
}

void loop() {
  uint32_t now = millis();
  static uint32_t tick = now;

  // Report readings over serial every 0.1 sec
  if (now - tick > 100) {
    tick = now;
    Serial.println(R_click.read_mA());
  }
}
```

# Example: R Click with exponential moving average
```cpp
#include <Arduino.h>
#include "MIKROE_4_20mA_RT_Click.h"

// The cable select pin of the R Click
const uint8_t PIN_R_CLICK = 5;

// Exponential moving average (EMA) parameters of the R Click readings
const uint32_t EMA_INTERVAL = 2000; // Desired oversampling interval [µs]
const float EMA_LP_FREQ = 10.;      // Low-pass filter cut-off frequency [Hz]

// Adjust the calibration parameters as needed
R_Click R_click(PIN_R_CLICK, RT_Click_Calibration{4.03, 19.93, 832, 3999});

void setup() {
  Serial.begin(9600);
  R_click.begin();
}

void loop() {
  uint32_t now = millis();
  static uint32_t tick = now;

  R_click.poll_EMA();

  // Report readings over serial every 1 sec
  if (now - tick > 1000) {
    tick = now;
    Serial.println(R_click.get_EMA_mA());
  }
}
```
