/*
DvG_IIR_LP_DAQ

Manages data-acquisition (DAQ) at a fixed rate (non-blocking) and applies an
one-pole infinite response (IIR) low-pass (LP) filter to the acquired data. Such
a filter is very memory efficient.

Class `IIR_LP_DAQ()` takes in the following arguments:
  DAQ_interval_ms:
    Data-acquisition time interval [ms]

  f_LP_Hz:
    Low-pass filter cut-off frequency [Hz]

  read_fun:
    Pointer to the 'read a new sample' function to invoke each polling update,
    e.g. `analogRead()`. It should return a value castable to type `uint32_t`.

`IIR_LP_DAQ::poll_update()` should be called continuously inside the main loop.
This function will check the timer if another reading should be performed and
added to the IIR filter.

Dennis van Gils, 15-07-2022
*/

#ifndef DvG_IIR_LP_DAQ_h
#define DvG_IIR_LP_DAQ_h

#include <Arduino.h>

class IIR_LP_DAQ {
private:
  uint32_t _DAQ_interval_ms; // Data acquisition time interval [ms]
  float _f_LP_Hz;            // Low-pass filter cut-off frequency [Hz]
  uint32_t (*_read_fun)();   // Pointer to `read a new sample` function
  float _IIR_LP_value;       // Current filter output value
  bool _at_startup;          // Are we at startup?
  float _alpha;              // Derived smoothing factor
  uint32_t _tick;            // Time of last reading in [us]

public:
  IIR_LP_DAQ(uint32_t DAQ_interval_ms, float f_LP_Hz, uint32_t (*read_fun)()) {
    _DAQ_interval_ms = DAQ_interval_ms;
    _f_LP_Hz = f_LP_Hz;
    _read_fun = read_fun;
    _IIR_LP_value = 0.0;
    _at_startup = true;
    _alpha = 1.0;
    _tick = micros();
  }

  /* Check if enough time has passed to acquire a new reading. If yes, acquire a
  new reading and append it to the IIR filter. Returns true when a reading was
  actually performed.
  */
  bool poll_update() {
    uint32_t now = micros();

    if ((now - _tick) > _DAQ_interval_ms * 1e3) {
      // Enough time has passed -> Acquire a new reading.
      // Calculate the smoothing factor every time because an exact DAQ interval
      // time is not garantueed.
      // (Operation takes ~ 180 usec on M0 Pro)
      _alpha = 1.0f - exp(-float(now - _tick) * 1e-6f * _f_LP_Hz);

      if (_at_startup) {
        _IIR_LP_value = _read_fun();
        _at_startup = false;
      } else {
        // (Operation not including `_read_fun()` takes ~ 20 usec on M0 Pro)
        _IIR_LP_value += _alpha * (_read_fun() - _IIR_LP_value);
        //_IIR_LP_value = _read_fun();  // DEBUG SPEED TEST
        //_IIR_LP_value = 0;            // DEBUG SPEED TEST
      }
      _tick = now;
      return true;

    } else {
      return false;
    }
  }

  // Return the current filter output value
  float get_value() { return _IIR_LP_value; }

  // Return the last derived smoothing factor
  float get_alpha() { return _alpha; }
};

#endif
