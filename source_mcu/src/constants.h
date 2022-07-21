/*
Constants of the TWT jetting grid

Dennis van Gils
21-07-2022
*/

#ifndef CONSTANTS_H_
#define CONSTANTS_H_

#include "MIKROE_4_20mA_RT_Click.h"

/*------------------------------------------------------------------------------
  MIKROE 4-20 mA R click boards for reading out the OMEGA pressure sensors
------------------------------------------------------------------------------*/

// Cable select pins
const uint8_t PIN_R_CLICK_1 = 10;
const uint8_t PIN_R_CLICK_2 = 9;
const uint8_t PIN_R_CLICK_3 = 5;
const uint8_t PIN_R_CLICK_4 = 6;

// Calibrated against a multimeter @ 14-07-2022 by DPM van Gils
const RT_Click_Calibration R_CLICK_1_CALIB{3.99, 20.00, 791, 3971};
const RT_Click_Calibration R_CLICK_2_CALIB{3.98, 19.57, 784, 3881};
const RT_Click_Calibration R_CLICK_3_CALIB{3.96, 19.68, 774, 3908};
const RT_Click_Calibration R_CLICK_4_CALIB{3.98, 19.83, 828, 3981};

// Single R click readings fluctuate a lot and so will be oversampled and
// subsequently low-pass filtered as data-acquisition (DAQ) routine.
const uint32_t DAQ_DT = 2; // Desired oversampling interval [ms]
const float DAQ_LP = 2.;   // Low-pass filter cut-off frequency [Hz]

/*------------------------------------------------------------------------------
  OMEGA pressure sensors, type PXM309-007GI
------------------------------------------------------------------------------*/

// Structure to hold the Omega pressure sensor calibration parameters
struct Omega_Calib {
  float balance_mA;
  float sensitivity_mA;
  float full_range_bar;
};

// Omega calibration parameters supplied with the pressure transducers
//   sensor #1 - Serial BG042821D030, Job WHS0059544, Date 30-03-22022
//   sensor #2 - Serial BG042821D032, Job WHS0059544, Date 30-03-22022
//   sensor #3 - Serial BG042821D034, Job WHS0059544, Date 30-03-22022
//   sensor #4 - Serial BG042821D041, Job WHS0059544, Date 30-03-22022
const Omega_Calib OMEGA_1_CALIB{4.035, 16.015, 7.0};
const Omega_Calib OMEGA_2_CALIB{4.024, 16.002, 7.0};
const Omega_Calib OMEGA_3_CALIB{4.004, 16.057, 7.0};
const Omega_Calib OMEGA_4_CALIB{3.995, 16.001, 7.0};

float mA2bar(float mA, const Omega_Calib calib) {
  return (mA - calib.balance_mA) / calib.sensitivity_mA * calib.full_range_bar;
}

#endif