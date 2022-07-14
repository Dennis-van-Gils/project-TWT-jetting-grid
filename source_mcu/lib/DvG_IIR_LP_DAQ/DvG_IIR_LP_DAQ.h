/*******************************************************************************
  DvG_IIR_LP_DAQ

  Dennis van Gils
  14-07-2022
*******************************************************************************/

#ifndef DvG_IIR_LP_DAQ_h
#define DvG_IIR_LP_DAQ_h

#include <Arduino.h>

/*******************************************************************************
  IIR_LP_DAQ
  Performs data acquisition (DAQ) at a fixed rate (non-blocking) and applies an
  one-pole infinite-input response (IIR) low-pass (LP) filter to the acquired
  data.
  IIR_LP_DAQ::pollUpdate() should be called continuously inside the main loop.
  This function will check the timer if another reading should be performed and
  added to the IIR filter.
*******************************************************************************/

class IIR_LP_DAQ {
public:
  // Constructor
  //  DAQ_interval_ms: data acquisition time interval [microsec]
  //  f_LP_Hz        : low-pass cut-off frequency [Hz]
  //  readFunction   : pointer to 'read' function, e.g. analogRead()
  IIR_LP_DAQ(uint32_t DAQ_interval_ms, float f_LP_Hz,
             uint32_t (*readFunction)());

  // Checks if enough time has passed to acquire a new reading. If yes, acquire
  // a new reading and append it to the IIR filter. Returns true when a reading
  // was actually performed.
  bool pollUpdate();

  // Returns the current low-pass filtered value
  float getValue();

  // Returns the last derived smoothing factor
  float getAlpha();

private:
  uint32_t _DAQ_interval_ms;
  float _f_LP_Hz;
  uint32_t (*_readFunction)(); // Pointer to read function
  float _IIR_LP_value;
  uint32_t _prevMicros; // Time of last reading
  bool _fStartup;
  float _alpha; // Derived smoothing factor
};

#endif
