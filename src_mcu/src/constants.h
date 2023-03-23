/**
 * @file    constants.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    23-03-2023
 *
 * @brief   Constants of the TWT jetting grid.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef CONSTANTS_H_
#define CONSTANTS_H_

#include "MIKROE_4_20mA_RT_Click.h"

/*------------------------------------------------------------------------------
  PURPOSE
--------------------------------------------------------------------------------

  This project involves the control of a jetting grid used in the Twente Water
  Tunnel (TWT) facility of the University of Twente, Physics of Fluids group.

  Upstream of the TWT measurement section will be the jetting grid consisting of
  112 individual nozzles laid out in a square grid perpendicular to the mean
  flow. All nozzles are powered by a single water pump providing the driving
  pressure for the jets. Each nozzle is controlled by an individual solenoid
  valve that can be programmatically opened or closed. The nozzles will open
  and close following predefined 'protocols' tailored to different turbulent
  statistics inside the measurement section.

  The valves of the grid come in through the 4 side walls of the tunnel section,
  with 28 valves through each side: 4 x 28 = 112 valves. Each set of these 28
  valves shares a common pressure distribution vessel of which we will monitor
  the pressure.

  This code contains the firmware for the Arduino to control the 112 solenoid
  valves, to read out the 4 pressure sensors and to drive a 16x16 LED matrix to
  visually indicate the status of each valve.

--------------------------------------------------------------------------------
  PROTOCOL COORDINATE SYSTEM (PCS)
--------------------------------------------------------------------------------

  The solenoid valves are ultimately opening and closing jetting nozzles that
  are laid out in a square grid, aka the protocol coordinate system (PCS).
  Individual points in the PCS are named P for point.

  ●: Indicates a valve & nozzle
  -: Indicates no nozzle & valve exists

      -7 -6 -5 -4 -3 -2 -1  0  1  2  3  4  5  6  7
     ┌─────────────────────────────────────────────┐
   7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
   1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
   0 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
  -6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
  -7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     └─────────────────────────────────────────────┘

  The PCS spans (-7, -7) to (7, 7) where (0, 0) is the center of the grid.
  Physical valves are numbered 1 to 112, with 0 indicating 'no valve'.
  For the valve numbering, see `docs\jetting_grid_indices.pdf` and the array
  `P2VALVE` as defined farther down in this file.

------------------------------------------------------------------------------*/

const int8_t PCS_X_MIN = -7; // Minimum x-axis coordinate of the PCS
const int8_t PCS_X_MAX = 7;  // Maximum x-axis coordinate of the PCS
const int8_t PCS_Y_MIN = -7; // Minimum y-axis coordinate of the PCS
const int8_t PCS_Y_MAX = 7;  // Maximum y-axis coordinate of the PCS
const uint8_t NUMEL_PCS_AXIS = PCS_X_MAX - PCS_X_MIN + 1;
const uint8_t NUMEL_LED_AXIS = 16; // 16x16 matrix
const uint8_t N_VALVES = 112;      // From 1 to 112, not counting 0
                                   // == floor(NUMEL_PCS_AXIS**2 / 2)

// clang-format off

// Translation matrix: PCS point to valve number.
//   [dim 1]: y-coordinate [0: y =  7, 14: y = -7]
//   [dim 2]: x-coordinate [0: x = -7, 14: x =  7]
//   Returns: The valve numbered 1 to 112, with 0 indicating 'no valve'
const uint8_t P2VALVE[NUMEL_PCS_AXIS][NUMEL_PCS_AXIS] = {
  // -7   -6   -5   -4   -3   -2   -1    0    1    2    3    4    5    6    7
  {   0,   1,   0,   5,   0,   9,   0,  13,   0,  17,   0,  21,   0,  25,   0 }, //  7
  { 109,   0, 110,   0, 111,   0, 112,   0,  32,   0,  31,   0,  30,   0,  29 }, //  6
  {   0,   2,   0,   6,   0,  10,   0,  14,   0,  18,   0,  22,   0,  26,   0 }, //  5
  { 105,   0, 106,   0, 107,   0, 108,   0,  36,   0,  35,   0,  34,   0,  33 }, //  4
  {   0,   3,   0,   7,   0,  11,   0,  15,   0,  19,   0,  23,   0,  27,   0 }, //  3
  { 101,   0, 102,   0, 103,   0, 104,   0,  40,   0,  39,   0,  38,   0,  37 }, //  2
  {   0,   4,   0,   8,   0,  12,   0,  16,   0,  20,   0,  24,   0,  28,   0 }, //  1
  {  97,   0,  98,   0,  99,   0, 100,   0,  44,   0,  43,   0,  42,   0,  41 }, //  0
  {   0,  84,   0,  80,   0,  76,   0,  72,   0,  68,   0,  64,   0,  60,   0 }, // -1
  {  93,   0,  94,   0,  95,   0,  96,   0,  48,   0,  47,   0,  46,   0,  45 }, // -2
  {   0,  83,   0,  79,   0,  75,   0,  71,   0,  67,   0,  63,   0,  59,   0 }, // -3
  {  89,   0,  90,   0,  91,   0,  92,   0,  52,   0,  51,   0,  50,   0,  49 }, // -4
  {   0,  82,   0,  78,   0,  74,   0,  70,   0,  66,   0,  62,   0,  58,   0 }, // -5
  {  85,   0,  86,   0,  87,   0,  88,   0,  56,   0,  55,   0,  54,   0,  53 }, // -6
  {   0,  81,   0,  77,   0,  73,   0,  69,   0,  65,   0,  61,   0,  57,   0 }  // -7
};

// Translation matrix: PCS point to LED index.
// The LED matrix is wired serpentine like.
//   [dim 1]: y-coordinate [0: y =  7, 14: y = -8]
//   [dim 2]: x-coordinate [0: x = -8, 15: x =  7]
//   Returns: The LED index 0 to 255
const uint8_t P2LED[NUMEL_LED_AXIS][NUMEL_LED_AXIS] = {
  // -8   -7   -6   -5   -4   -3   -2   -1    0    1    2    3    4    5    6    7
  { 240, 239, 208, 207, 176, 175, 144, 143, 112, 111,  80,  79,  48,  47,  16,  15 }, //  7
  { 241, 238, 209, 206, 177, 174, 145, 142, 113, 110,  81,  78,  49,  46,  17,  14 }, //  6
  { 242, 237, 210, 205, 178, 173, 146, 141, 114, 109,  82,  77,  50,  45,  18,  13 }, //  5
  { 243, 236, 211, 204, 179, 172, 147, 140, 115, 108,  83,  76,  51,  44,  19,  12 }, //  4
  { 244, 235, 212, 203, 180, 171, 148, 139, 116, 107,  84,  75,  52,  43,  20,  11 }, //  3
  { 245, 234, 213, 202, 181, 170, 149, 138, 117, 106,  85,  74,  53,  42,  21,  10 }, //  2
  { 246, 233, 214, 201, 182, 169, 150, 137, 118, 105,  86,  73,  54,  41,  22,   9 }, //  1
  { 247, 232, 215, 200, 183, 168, 151, 136, 119, 104,  87,  72,  55,  40,  23,   8 }, //  0
  { 248, 231, 216, 199, 184, 167, 152, 135, 120, 103,  88,  71,  56,  39,  24,   7 }, // -1
  { 249, 230, 217, 198, 185, 166, 153, 134, 121, 102,  89,  70,  57,  38,  25,   6 }, // -2
  { 250, 229, 218, 197, 186, 165, 154, 133, 122, 101,  90,  69,  58,  37,  26,   5 }, // -3
  { 251, 228, 219, 196, 187, 164, 155, 132, 123, 100,  91,  68,  59,  36,  27,   4 }, // -4
  { 252, 227, 220, 195, 188, 163, 156, 131, 124,  99,  92,  67,  60,  35,  28,   3 }, // -5
  { 253, 226, 221, 194, 189, 162, 157, 130, 125,  98,  93,  66,  61,  34,  29,   2 }, // -6
  { 254, 225, 222, 193, 190, 161, 158, 129, 126,  97,  94,  65,  62,  33,  30,   1 }, // -7
  { 255, 224, 223, 192, 191, 160, 159, 128, 127,  96,  95,  64,  63,  32,  31,   0 }, // -8
};

// clang-format on

/*------------------------------------------------------------------------------
  HARDWARE WIRING
--------------------------------------------------------------------------------

  TABLE 1: Wiring scheme

    |-------------------------------------------------------|
    |               Fixed wiring               |  Flexible  |
    |------------------------------------------|------------|
    |      Centipedes      |   MOSFET boards   |   valves   |
    |----------------------|-------------------|------------|
    |  port° |   channels° |  #° |   channels° |         #¹ |
    |--------|-------------|-----|-------------|------------|
    |     0  |    0 -  15  |  0  |    0 -  15  |   1 -  14  |
    |     1  |   16 -  31  |  1  |   16 -  31  |  15 -  28  |
    |     2  |   32 -  47  |  2  |   32 -  47  |  29 -  42  |
    |     3  |   48 -  63  |  3  |   48 -  63  |  43 -  56  |
    |     4  |   64 -  79  |  4  |   64 -  79  |  57 -  70  |
    |     5  |   80 -  95  |  5  |   80 -  95  |  71 -  84  |
    |     6  |   96 - 111  |  6  |   96 - 111  |  85 -  98  |
    |     7  |  112 - 127  |  7  |  112 - 127  |  99 - 112  |
    |-------------------------------------------------------|
    °: index starts at 0
    ¹: numbering starts at 1

  # Centipedes

  Connected to the Arduino (Adafruit Feather M4 Express) are two Centipede
  boards from Macetech. Each Centipede board consists of 8x MCP23017 16-bit
  digital I/O port expander chips, adressable over I2C. Hence, each board
  provides 64 digital channels, here configured as output, for a total of 128
  channels.

  Both Centipedes are managed by a single instance of the `Centipede` class,
  called the `cp` object in `main.cpp`. The object uses `ports` and `values` to
  refer to individual channels. The `value` written to a `port` decodes a 16-bit
  bitmask, toggling the corresponding channels of that port on or off.

  # MOSFET boards

  The output channels of the Centipedes deliver 3.3 V. To drive the solenoid
  valves we need a voltage of 24 V. Hence, we use MOSFET boards in order to
  increase the electrical power of each digital channel. Each MOSFET board
  (from AliExpress, brand Sanwo?) provides 16-channels, so we have 8 MOSFET
  boards in total. All 128 Centipede channels are wired in a 1-to-1 incremental
  fashion to the MOSFET boards. This physical wiring SHOULD NOT CHANGE!

  # Solenoid valves

  The physical wiring from the output channels of the MOSFET boards to each
  individual valve happens in groups of 14, where only the first 14 of the 16
  channels of each MOSFET board are used. The last two channels are not
  connected to a valve, and can serve as a backup when one of the first 14
  channels becomes faulty somehow. Hence, here is where the physical wiring
  is user-configurable and diverts from a 1-to-1 incremental relationship with
  respect to the MOSFET and Centipede boards.

  NOTE: In contrast to the port and channel numbers of the Centipede and MOSFET
  boards which start at an index of 0, the valves start at a number of 1. A
  valve with number 0 is a special case denoting that no valve is connected at
  that location.

  Arrays `VALVE2CP_PORT` and `VALVE2CP_BIT` must reflect this physical wiring.
  Change these arrays whenever modifications had to be made to the wiring inside
  the electronics cabinet.

------------------------------------------------------------------------------*/

// clang-format off

// Translation array: Valve number to Centipede port.
// This array must reflect the physical wiring inside the electronics cabinet.
//   [dim 1]: The valve number - 1, so from 0 to 111
//   Returns: The Centipede port index
const uint8_t VALVE2CP_PORT[N_VALVES] = {
  //  1    2    3    4    5    6    7    8    9   10   11   12   13   14
      0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
  // 15   16   17   18   19   20   21   22   23   24   25   26   27   28
      1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
  // 29   30   31   32   33   34   35   36   37   38   39   40   41   42
      2,   2,   2,   2,   2,   2,   2,   2,   2,   2,   2,   2,   2,   2,
  // 43   44   45   46   47   48   49   50   51   52   53   54   55   56
      3,   3,   3,   3,   3,   3,   3,   3,   3,   3,   3,   3,   3,   3,
  // 57   58   59   60   61   62   63   64   65   66   67   68   69   70
      4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,   4,
  // 71   72   73   74   75   76   77   78   79   80   81   82   83   84
      5,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,
  // 85   86   87   88   89   90   91   92   93   94   95   96   97   98
      6,   6,   6,   6,   6,   6,   6,   6,   6,   6,   6,   6,   6,   6,
  // 99  100  101  102  103  104  105  106  107  108  109  110  111  112
      7,   7,   7,   7,   7,   7,   7,   7,   7,   7,   7,   7,   7,   7
};

// Translation array: Valve number to Centipede bitmask bit.
// This array must reflect the physical wiring inside the electronics cabinet.
//   [dim 1]: The valve number - 1, so from 0 to 111
//   Returns: The Centipede bitmask bit index
const uint8_t VALVE2CP_BIT[N_VALVES] = {
  //  1    2    3    4    5    6    7    8    9   10   11   12   13   14
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 15   16   17   18   19   20   21   22   23   24   25   26   27   28
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 29   30   31   32   33   34   35   36   37   38   39   40   41   42
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 43   44   45   46   47   48   49   50   51   52   53   54   55   56
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 57   58   59   60   61   62   63   64   65   66   67   68   69   70
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 71   72   73   74   75   76   77   78   79   80   81   82   83   84
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 85   86   87   88   89   90   91   92   93   94   95   96   97   98
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
  // 99  100  101  102  103  104  105  106  107  108  109  110  111  112
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,
};

// clang-format on

/*------------------------------------------------------------------------------
  LED matrix, 16x16 WS2812 RGB NeoPixel (Adafruit #2547)
------------------------------------------------------------------------------*/

const uint16_t N_LEDS = NUMEL_LED_AXIS * NUMEL_LED_AXIS;
const uint8_t PIN_LED_MATRIX = 11;

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

// Single R click readings fluctuate a lot and so we will employ an exponential
// moving average by using oversampling and subsequent low-pass filtering as
// data-acquisition (DAQ) routine.
const uint32_t DAQ_DT = 10000; // Desired oversampling interval [µs]
const float DAQ_LP = 2.;       // Low-pass filter cut-off frequency [Hz]

/*------------------------------------------------------------------------------
  OMEGA pressure sensors, type PXM309-007GI
------------------------------------------------------------------------------*/

/**
 * @brief Structure to hold the Omega pressure sensor calibration parameters.
 *
 * The parameters can be found on the calibration sheet supplied with the
 * sensor.
 */
struct Omega_Calib {
  float balance_mA;
  float sensitivity_mA;
  float full_range_bar;
};

// Omega calibration parameters supplied with the pressure sensors
//   sensor #1 - Serial BG042821D030, Job WHS0059544, Date 30-03-22022
//   sensor #2 - Serial BG042821D032, Job WHS0059544, Date 30-03-22022
//   sensor #3 - Serial BG042821D034, Job WHS0059544, Date 30-03-22022
//   sensor #4 - Serial BG042821D041, Job WHS0059544, Date 30-03-22022
const Omega_Calib OMEGA_1_CALIB{4.035, 16.015, 7.0};
const Omega_Calib OMEGA_2_CALIB{4.024, 16.002, 7.0};
const Omega_Calib OMEGA_3_CALIB{4.004, 16.057, 7.0};
const Omega_Calib OMEGA_4_CALIB{3.995, 16.001, 7.0};

inline float mA2bar(float mA, const Omega_Calib calib) {
  return (mA - calib.balance_mA) / calib.sensitivity_mA * calib.full_range_bar;
}

/*------------------------------------------------------------------------------
  Safety pulses
------------------------------------------------------------------------------*/

/*
There are two microcontroller (MCU) boards used in the TWT jetting grid. The
main MCU (Adafruit M4 Feather Express) is responsible for driving the solenoid
valves and LED matrix and communicates via USB to the Python main program
running on a PC. The second MCU (Adafruit Feather M0 Basic Proto) acts as a
safety controller, governing the relay that allows turning the jetting pump on
and off via terminal X1 of its frequency inverter.

The main MCU should send a digital 'safety' pulse at least once every N ms over
to the safety MCU as indication that the main MCU is still operating all right.
As long as the safety MCU receives pulses within the set time period, the
'pump on' relay will be engaged.
*/

const uint8_t PIN_SAFETY_PULSE_OUT = 12;
const uint16_t PERIOD_SAFETY_PULSES = 60; // [ms]

/*------------------------------------------------------------------------------
  Watchdog
------------------------------------------------------------------------------*/

// The microcontroller will auto-reboot when it fails to get a
// `Watchdog.reset()` within this time period [ms]
const uint16_t WATCHDOG_TIMEOUT = 8000;

#endif