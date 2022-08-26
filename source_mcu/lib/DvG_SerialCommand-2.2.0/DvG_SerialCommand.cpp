/**
 * @file    DvG_SerialCommand.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/DvG_SerialCommand
 * @version 3.0.0
 * @date    26-08-2022
 *
 * @mainpage An Arduino library to listen to a serial port for incoming commands
 * and act upon them.
 *
 * @section Introduction
 * To keep the memory usage low, it uses a C-string (null-terminated character
 * array) to store incoming characters received over the serial port, instead of
 * using a memory hungry C++ string.
 *
 * TODO: mention ASCII and byte (raw) classes
 *
 * @section Usage
 * 'available()' should be called periodically to poll for incoming characters.
 * It will return true when a new command is ready to be processed.
 * Subsequently, the command string can be retrieved by calling 'getCmd()'.
 *
 * @code{.cpp}
 * @endcode
 *
 * @section author Author
 * Dennis van Gils (vangils.dennis@gmail.com)
 *
 * @section version Version
 * - https://github.com/Dennis-van-Gils/DvG_SerialCommand
 * - v3.0.0
 *
 * @section Changelog
 * - v3.0.0 - ...
 *
 * @section license License
 * MIT License. See the LICENSE file for details.
 */

#include "DvG_SerialCommand.h"

/*******************************************************************************
  DvG_SerialCommand
*******************************************************************************/

DvG_SerialCommand::DvG_SerialCommand(Stream &stream, char *buffer,
                                     uint16_t max_len)
    : _port(stream) // Initialize reference before body
{
  _buffer = buffer;
  _buffer[0] = '\0';
  _max_len = max_len;
  _cur_len = 0;
  _fTerminated = false;
}

bool DvG_SerialCommand::available() {
  char c;

  // Poll serial buffer
  if (_port.available()) {
    _fTerminated = false;
    while (_port.available()) {
      c = _port.peek();

      if (c == 13) {
        // Ignore ASCII 13 (carriage return)
        _port.read(); // Remove char from serial buffer

      } else if (c == 10) {
        // Found ASCII 10 (line feed) --> Terminate string
        _port.read(); // Remove char from serial buffer
        _buffer[_cur_len] = '\0';
        _fTerminated = true;
        break;

      } else if (_cur_len < _max_len - 1) {
        // Append char to string
        _port.read(); // Remove char from serial buffer
        _buffer[_cur_len] = c;
        _cur_len++;

      } else {
        // Maximum length of incoming serial command is reached. Forcefully
        // terminate string now. Leave the char in the serial buffer.
        _buffer[_cur_len] = '\0';
        _fTerminated = true;
        break;
      }
    }
  }

  return _fTerminated;
}

char *DvG_SerialCommand::getCommand() {
  if (_fTerminated) {
    // Reset serial command buffer
    _fTerminated = false;
    _cur_len = 0;
    return _buffer;
  } else {
    return (char *)_empty;
  }
}

/*******************************************************************************
  Parse functions
*******************************************************************************/

float parseFloatInString(const char *str_in, uint16_t pos) {
  if (strlen(str_in) > pos) {
    return (float)atof(&str_in[pos]);
  } else {
    return 0.0f;
  }
}

bool parseBoolInString(const char *str_in, uint16_t pos) {
  if (strlen(str_in) > pos) {
    return (atoi(&str_in[pos]) == 1 ||               //
            strncmp(&str_in[pos], "true", 4) == 0 || //
            strncmp(&str_in[pos], "True", 4) == 0 || //
            strncmp(&str_in[pos], "TRUE", 4) == 0);
  } else {
    return false;
  }
}

int parseIntInString(const char *str_in, uint16_t pos) {
  if (strlen(str_in) > pos) {
    return atoi(&str_in[pos]);
  } else {
    return 0;
  }
}