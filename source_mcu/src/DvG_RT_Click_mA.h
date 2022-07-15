/*
DvG_RT_click_mA

A library for the 4-20 mA current controllers of MIKROE
- 4-20 mA R click (receiver)
- 4-20 mA T click (transmitter)
Both operate over the SPI bus

Maximal SPI clock frequency for MCP3204 (R click) and MCP3201 (T click)
running at 3.3V is 1 MHz.

Dennis van Gils, 15-07-2022
*/

/*
Additional notes from John Cabrer, wildseyed@gmail.com

According to other code examples for PIC, the 4-20 mA T click takes values from
~ 800 to ~ 4095 for the current control. The four most significant bits are for
control, and should be 0011 where:

bit 15
  1 = Ignore this command
  0 = Write to DAC register
bit 14 BUF: VREF Input Buffer Control bit
  1 = Buffered
  0 = Unbuffered
bit 13 GA: Output Gain Selection bit
  1 = 1x (VOUT = VREF * D/4096)
  0 = 2x (VOUT = 2 * VREF * D/4096)
bit 12 SHDN: Output Shutdown Control bit
  1 = Active mode operation. VOUT is available.
  0 = Shutdown the device. Analog output is not available. VOUT pin is
      connected to 500 kOhm (typical)
bit 11-0 D11:D0: DAC Input Data bits. Bit x is ignored
*/

#ifndef DvG_RT_click_mA_h
#define DvG_RT_click_mA_h

#include <Arduino.h>
#include <SPI.h>

// Maximal SPI clock frequency for MCP3204 (R click) and MCP3201 (T click)
// running at 3.3V is 1 MHz.
const SPISettings RT_CLICK_SPI(1000000, MSBFIRST, SPI_MODE0);

const byte JUNK = 0xFF;

/*******************************************************************************
  T_Click
*******************************************************************************/

class T_Click {
private:
  uint8_t _CS_pin;      // Cable Select pin
  float _p1_mA;         // Point 1 for linear interpolation [mA]
  float _p2_mA;         // Point 2 for linear interpolation [mA]
  uint16_t _p1_bitval;  // Point 1 for linear interpolation [bit value]
  uint16_t _p2_bitval;  // Point 2 for linear interpolation [bit value]
  uint16_t _set_bitval; // Last set bit value

public:
  // Constructor
  // CS_pin          : Cable Select pin corresponding to the T click board
  // p1_mA, p1_bitval: Point 1 for the linear interpolation
  // p2_mA, p2_bitval: Point 2 for the linear interpolation
  // Points 1 and 2 should be determined per T click board by calibration
  // against a digital multimeter, e.g.
  // p1_mA =  4.00 (read from multimeter), p1_bitval =  798 (set by Arduino)
  // p2_mA = 20.51 (read from multimeter), p2_bitval = 4095 (set by Arduino)
  T_Click(uint8_t CS_pin, float p1_mA, uint16_t p1_bitval, float p2_mA,
          uint16_t p2_bitval) {
    _CS_pin = CS_pin;
    _p1_mA = p1_mA;
    _p2_mA = p2_mA;
    _p1_bitval = p1_bitval;
    _p2_bitval = p2_bitval;
  }

  // Start SPI and set up GPIO
  void begin() {
    SPI.begin();                 // Start SPI
    digitalWrite(_CS_pin, HIGH); // Disable the slave SPI device for now
    pinMode(_CS_pin, OUTPUT);

    // Force output to 4 mA at the start
    set_mA(4.0);
  }

  // Set the output current [mA]
  void set_mA(float mA_value) {
    uint16_t bitval;
    byte bitval_HI;
    byte bitval_LO;

    // Transform current [mA] to bit value
    bitval = (int)round((mA_value - _p1_mA) / (_p2_mA - _p1_mA) *
                            (_p2_bitval - _p1_bitval) +
                        _p1_bitval);
    _set_bitval = bitval;

    // The standard Arduino SPI library handles data of 8 bits long
    // The MIKROE T Click shield is 12 bits, hence transfer in two steps
    bitval_HI = (bitval >> 8) & 0x0F; // 0x0F = 15
    bitval_HI |= 0x30;                // 0x30 = 48
    bitval_LO = bitval;

    SPI.beginTransaction(RT_CLICK_SPI);
    digitalWrite(_CS_pin, LOW);  // Enable slave device
    SPI.transfer(bitval_HI);     // Transfer highbyte
    SPI.transfer(bitval_LO);     // Transfer lowbyte
    digitalWrite(_CS_pin, HIGH); // Disable slave device
    SPI.endTransaction();
  }

  // Returns the bit value belonging to the last set current
  uint16_t get_last_set_bitval() { return _set_bitval; }
};

/*******************************************************************************
  R_Click
*******************************************************************************/

class R_Click {
private:
  uint8_t _CS_pin;     // Cable Select pin
  float _p1_mA;        // Point 1 for linear interpolation [mA]
  float _p2_mA;        // Point 2 for linear interpolation [mA]
  uint16_t _p1_bitval; // Point 1 for linear interpolation [bit value]
  uint16_t _p2_bitval; // Point 2 for linear interpolation [bit value]

public:
  // Constructor
  // CS_pin          : Cable Select pin corresponding to the R click board
  // p1_mA, p1_bitval: Point 1 for the linear interpolation
  // p2_mA, p2_bitval: Point 2 for the linear interpolation
  // Points 1 and 2 should be determined per R click board by calibration
  // against a digital multimeter, e.g.
  // p1_mA =  4.0 (read from multimeter), p1_bitval =  781 (read by Arduino)
  // p2_mA = 20.0 (read from multimeter), p2_bitval = 3963 (read by Arduino)
  R_Click(uint8_t CS_pin, float p1_mA, uint16_t p1_bitval, float p2_mA,
          uint16_t p2_bitval) {
    _CS_pin = CS_pin;
    _p1_mA = p1_mA;
    _p2_mA = p2_mA;
    _p1_bitval = p1_bitval;
    _p2_bitval = p2_bitval;
  }

  // Start SPI and set up GPIO
  void begin() {
    SPI.begin();                 // Start SPI
    digitalWrite(_CS_pin, HIGH); // Disable the slave SPI device for now
    pinMode(_CS_pin, OUTPUT);
  }

  // Transform the bit value into a current [mA] given the calibration params
  float bitval2mA(float bitval) {
    // NB: Keep input argument of type 'float' to accomodate for a running
    // average that could have been applied to the bit value, hence making it
    // fractional.
    return (_p1_mA + (bitval - _p1_bitval) / float(_p2_bitval - _p1_bitval) *
                         (_p2_mA - _p1_mA));
  }

  // Read out the R click and return the bit value
  uint32_t read_bitval() {
    byte data_HI;
    byte data_LO;

    // The standard Arduino SPI library handles data of 8 bits long
    // The MIKROE R Click shield is 12 bits, hence transfer in two steps
    SPI.beginTransaction(RT_CLICK_SPI);
    digitalWrite(_CS_pin, LOW); // Enable slave device
    data_HI = SPI.transfer(JUNK) & 0x1F;
    data_LO = SPI.transfer(JUNK);
    digitalWrite(_CS_pin, HIGH); // Disable slave device
    SPI.endTransaction();

    // Reconstruct bit value
    return (uint32_t)((data_HI << 8) | data_LO) >> 1;
  }

  // Read out the R click and return the current in [mA]
  float read_mA() { return bitval2mA(R_Click::read_bitval()); }
};

#endif
