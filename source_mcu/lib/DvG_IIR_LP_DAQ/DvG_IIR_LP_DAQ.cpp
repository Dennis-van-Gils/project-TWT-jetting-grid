/*******************************************************************************
  DvG_IIR_LP_DAQ

  Dennis van Gils
  14-07-2022
*******************************************************************************/

#include "DvG_IIR_LP_DAQ.h"

/*******************************************************************************
  IIR_LP_DAQ
  Performs data acquisition (DAQ) at a fixed rate (non-blocking) and applies an
  one-pole infinite-input response (IIR) low-pass (LP) filter to the acquired
  data.
  IIR_LP_DAQ::pollUpdate() should be called continuously inside the main loop.
  This function will check the timer if another reading should be performed and
  added to the IIR filter.
*******************************************************************************/

IIR_LP_DAQ::IIR_LP_DAQ(uint32_t DAQ_interval_ms, float f_LP_Hz,
                       uint32_t (*readFunction)()) {
  _DAQ_interval_ms = DAQ_interval_ms; // [millisec]
  _f_LP_Hz = f_LP_Hz;
  _readFunction = readFunction;
  _IIR_LP_value = 0.0;
  _prevMicros = 0;
  _fStartup = true;
  _alpha = 1.0;
}

// Checks if enough time has passed to acquire a new reading. If yes, acquire
// a new reading and append it to the IIR filter. Returns true when a reading
// was actually performed.
bool IIR_LP_DAQ::pollUpdate() {
  uint32_t curMicros = micros();

  if ((curMicros - _prevMicros) > _DAQ_interval_ms * 1e3) {
    // Enough time has passed: acquire new reading
    // Calculate the smoothing factor every time because an exact DAQ interval
    // time is not garantueed
    _alpha = 1.0 - exp(-float(curMicros - _prevMicros) * 1e-6 *
                       _f_LP_Hz); // (Operation takes ~ 180 usec on M0 Pro)

    if (_fStartup) {
      _IIR_LP_value = _readFunction();
      _fStartup = false;
    } else {
      _IIR_LP_value +=
          _alpha * (_readFunction() -
                    _IIR_LP_value); // (Operation not including _readFunction
                                    // takes ~ 20 usec on M0 Pro)
      //_IIR_LP_value = _readFunction();  // DEBUG SPEED TEST
      //_IIR_LP_value = 0;                // DEBUG SPEED TEST
    }
    _prevMicros = curMicros;
    return true;
  } else {
    return false;
  }
}

// Returns the current low-pass filtered value
float IIR_LP_DAQ::getValue() { return _IIR_LP_value; }

// Returns the last derived smoothing factor
float IIR_LP_DAQ::getAlpha() { return _alpha; }
