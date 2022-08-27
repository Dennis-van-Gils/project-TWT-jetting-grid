/**
 * @file    DvG_SerialCommand.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/DvG_SerialCommand
 * @version 3.0.0
 * @date    27-08-2022
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
    : _stream(stream) // Initialize reference before body
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
  if (_stream.available()) {
    _fTerminated = false;
    while (_stream.available()) {
      c = _stream.peek();

      if (c == 13) {
        // Ignore ASCII 13 (carriage return)
        _stream.read(); // Remove char from serial buffer

      } else if (c == 10) {
        // Found ASCII 10 (line feed) --> Terminate string
        _stream.read(); // Remove char from serial buffer
        _buffer[_cur_len] = '\0';
        _fTerminated = true;
        break;

      } else if (_cur_len < _max_len - 1) {
        // Append char to string
        _stream.read(); // Remove char from serial buffer
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
  DvG_BinarySerialCommand
*******************************************************************************/

DvG_BinarySerialCommand::DvG_BinarySerialCommand(Stream &stream,
                                                 uint8_t *buffer,
                                                 uint16_t max_len,
                                                 const uint8_t *EOL,
                                                 uint8_t EOL_len)
    : _stream(stream) // Initialize reference before body
{
  _buffer = buffer;
  _buffer[0] = 0;
  _max_len = max_len;
  _cur_len = 0;
  _EOL = EOL;
  _EOL_len = EOL_len;
  _found_EOL = false;
}

int8_t DvG_BinarySerialCommand::available(bool debug_info) {
  uint8_t c;

  while (_stream.available()) {
    c = _stream.read();
    if (debug_info) {
      _stream.print(c, HEX);
      _stream.write('\t');
    }

    if (_cur_len < _max_len) {
      _buffer[_cur_len] = c;
      _cur_len++;
    } else {
      // Maximum buffer length is reached. Discard the byte and return the
      // special value of -1.
      return -1;
    }

    // Check for EOL at the end
    if (_cur_len >= _EOL_len) {
      _found_EOL = true;
      for (uint8_t i = 0; i < _EOL_len; ++i) {
        if (_buffer[_cur_len - i - 1] != _EOL[_EOL_len - i - 1]) {
          _found_EOL = false;
          break; // Any mismatch will exit early
        }
      }
      if (_found_EOL) {
        // Wait with reading in more bytes from the serial buffer to let the
        // user act upon the currently received command
        if (debug_info) {
          _stream.print("EOL\t");
        }
        break;
      }
    }
  }

  return _found_EOL;
}

uint16_t DvG_BinarySerialCommand::getCommandLength() {
  uint16_t len;

  if (_found_EOL) {
    len = _cur_len - _EOL_len;

    // Reset serial command buffer
    _found_EOL = false;
    _cur_len = 0;
  } else {
    len = 0;
  }

  return len;
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