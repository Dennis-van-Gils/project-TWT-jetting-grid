/**
 * @file    DvG_StreamCommand.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/DvG_StreamCommand
 * @version 1.0.0
 * @date    28-08-2022
 *
 * @mainpage A lightweight Arduino library to listen for commands over a stream.
 *
 * It provides two classes to allow listening to a stream, such as Serial or
 * Wire, for incoming commands (or data packets in general) and act upon them.
 * Class `DvG_StreamCommand` will listen for ASCII commands, while class
 * `DvG_BinaryStreamCommand` will listen for binary commands.
 *
 * @section Usage
 * Method `available()` should be called repeatedly to poll for incoming
 * characters or bytes to the stream. It will return true when a new command is
 * ready to be processed.
 *
 * @section example_1 Example: Serial ASCII
 * @code{.cpp}
 * #include <Arduino.h>
 * #include "DvG_StreamCommand.h"
 *
 * // Serial port listener for receiving ASCII commands
 * const uint8_t CMD_BUF_LEN = 64;  // Length of the ASCII command buffer
 * char cmd_buf[CMD_BUF_LEN]{'\0'}; // The ASCII command buffer
 * DvG_StreamCommand sc(Serial, cmd_buf, CMD_BUF_LEN);
 *
 * void loop() {
 *   char *str_cmd; // Will hold a completed ASCII command string
 *
 *   if (sc.available()) {
 *     str_cmd = sc.getCommand();
 *
 *     // Example command, put your own code here
 *     if (strcmp(str_cmd, "id?") == 0) {
 *       // Report identity
 *       Serial.println("Arduino");
 *     }
 *   }
 * }
 * @endcode
 *
 * @section example_2 Example: Serial binary
 * @code{.cpp}
 * #include <Arduino.h>
 * #include "DvG_StreamCommand.h"
 *
 * // Serial port listener for receiving binary commands
 * const uint8_t BIN_BUF_LEN = 64; // Length of the binary command buffer
 * uint8_t bin_buf[BIN_BUF_LEN];   // The binary command buffer
 * const uint8_t EOL[] = {0xff, 0xff, 0xff, 0xff}; // End-of-line sentinel
 * DvG_BinaryStreamCommand bsc(Serial, bin_buf, BIN_BUF_LEN, EOL, sizeof(EOL));
 *
 * void loop() {
 *   int8_t bsc_available = bsc.available();
 *
 *   if (bsc_available == -1) {
 *     Serial.println("Buffer has overrun and bytes got dropped.");
 *   }
 *
 *   if (bsc_available) {
 *     uint16_t data_len = bsc.getCommandLength();
 *
 *     // Example command parser, put your own code here
 *     for (uint16_t idx = 0; idx < data_len; ++idx) {
 *       // Simply print all received bytes as HEX to the serial port
 *       Serial.println(bin_buf[idx], HEX);
 *     }
 *   }
 * }
 * @endcode
 *
 * @section author Author
 * Dennis van Gils (vangils.dennis@gmail.com)
 *
 * @section version Version
 * - https://github.com/Dennis-van-Gils/DvG_StreamCommand
 * - v1.0.0
 *
 * @section Changelog
 * - v1.0.0 - Initial commit. This is the improved successor to
 * `DvG_SerialCommand`.
 *
 * @section license License
 * MIT License. See the LICENSE file for details.
 */

#include "DvG_SerialCommand.h"
//#include "DvG_StreamCommand.h" TODO: switch around

/*******************************************************************************
  DvG_StreamCommand
*******************************************************************************/

DvG_StreamCommand::DvG_StreamCommand(Stream &stream, char *buffer,
                                     uint16_t max_len)
    : _stream(stream) // Initialize reference before body
{
  _buffer = buffer;
  _buffer[0] = '\0';
  _max_len = max_len;
  _cur_len = 0;
  _fTerminated = false;
}

bool DvG_StreamCommand::available() {
  char c;

  // Poll the input buffer of the stream for data
  if (_stream.available()) {
    _fTerminated = false;
    while (_stream.available()) {
      c = _stream.peek();

      if (c == 13) {
        // Ignore ASCII 13 (carriage return)
        _stream.read(); // Remove char from the stream input buffer

      } else if (c == 10) {
        // Found ASCII 10 (line feed) --> Terminate string
        _stream.read(); // Remove char from the stream input buffer
        _buffer[_cur_len] = '\0';
        _fTerminated = true;
        break;

      } else if (_cur_len < _max_len - 1) {
        // Append char to string
        _stream.read(); // Remove char from the stream input buffer
        _buffer[_cur_len] = c;
        _cur_len++;

      } else {
        // Maximum buffer length is reached. Forcefully terminate the string
        // in the command buffer now. Leave the char in the stream input buffer.
        _buffer[_cur_len] = '\0';
        _fTerminated = true;
        break;
      }
    }
  }

  return _fTerminated;
}

char *DvG_StreamCommand::getCommand() {
  if (_fTerminated) {
    _fTerminated = false;
    _cur_len = 0;
    return _buffer;

  } else {
    return (char *)_empty;
  }
}

/*******************************************************************************
  DvG_BinaryStreamCommand
*******************************************************************************/

DvG_BinaryStreamCommand::DvG_BinaryStreamCommand(Stream &stream,
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

int8_t DvG_BinaryStreamCommand::available(bool debug_info) {
  uint8_t c;

  // Poll the input buffer of the stream for data
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
      // Maximum buffer length is reached. Drop the byte and return the special
      // value of -1 to signal the user.
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
        // Wait with reading in more bytes from the stream input buffer to let
        // the user act upon the currently received command
        if (debug_info) {
          _stream.print("EOL\t");
        }
        break;
      }
    }
  }

  return _found_EOL;
}

uint16_t DvG_BinaryStreamCommand::getCommandLength() {
  uint16_t len;

  if (_found_EOL) {
    len = _cur_len - _EOL_len;
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