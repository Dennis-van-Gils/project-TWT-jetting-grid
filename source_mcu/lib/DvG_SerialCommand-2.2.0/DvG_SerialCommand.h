/**
 * @file DvG_SerialCommand.h
 * @author Dennis van Gils (vangils.dennis@gmail.com)
 * @brief An Arduino library to listen to a serial port for incoming commands
 * and act upon them.
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef H_DvG_SerialCommand
#define H_DvG_SerialCommand

#include <Arduino.h>

/*******************************************************************************
  DvG_SerialCommand
*******************************************************************************/

/**
 * @brief Class to manage listening to a serial port for ASCII commands and act
 * upon them.
 *
 * Once a linefeed ('\\n', ASCII 10) character is received, or else when the
 * number of incoming characters has exceeded the command buffer size, we speak
 * of a completely received 'command'. Carriage return ('\\r', ASCII 13)
 * characters are ignored from the stream.
 */
class DvG_SerialCommand {
public:
  /**
   * @brief Construct a new DvG_SerialCommand object.
   *
   * @param stream Reference to a serial port stream to listen to
   * @param buffer Reference to a character array which will be managed by this
   * class to hold a single incoming serial command. This command buffer should
   * be one character larger than the longest incoming serial command to allow
   * for the C-string termination character '\0' to become appended.
   * @param max_len Array size of @p buffer including '\0'. Do not exceed the
   * maximum of 2^^16 = 65536 characters.
   */
  DvG_SerialCommand(Stream &stream, char *buffer, uint16_t max_len);

  /**
   * @brief Poll the serial port refered to by @p stream for incoming characters
   * and append them one-by-one to the command buffer @p buffer.
   *
   * @return True when a complete command has been received and is ready to be
   * returned by @ref getCommand(), false otherwise.
   */
  bool available();

  /**
   * @brief Return the reference to the serial command buffer only when a
   * complete serial command has been received. Otherwise, an empty C-string is
   * returned.
   *
   * @return char*
   */
  char *getCommand();

private:
  Stream &_port;           // Reference to the serial port stream to listen to
  char *_buffer;           // Reference to the command buffer
  uint16_t _max_len;       // Array size of the command buffer
  uint16_t _cur_len;       // Number of currently received command characters
  bool _fTerminated;       // Has a complete serial command been received?
  const char *_empty = ""; // Empty reply, which is just the '\0' character
};

/*******************************************************************************
  DvG_BinarySerialCommand
*******************************************************************************/

/**
 * @brief Class to manage listening to a serial port for binary commands and act
 * upon them.
 *
 * Once a sequence of bytes is received that matches the end-of-line (EOL)
 * sentinel, or else when the number of incoming bytes has exceeded the command
 * buffer size, we speak of a completely received 'command'.
 */
class DvG_BinarySerialCommand {
public:
  /**
   * @brief Construct a new DvG_BinarySerialCommand object.
   *
   * @param stream Reference to a serial port stream to listen to
   * @param buffer Reference to an uint8_t array which will be managed by this
   * class to hold a single incoming serial command in binary form.
   * @param max_len Array size of @p buffer. Do not exceed the maximum size of
   * 2^^16 = 65536 bytes.
   * @param EOL
   * @param EOL_len Do not exceed maximum size of 2^^8 = 256 bytes
   * TODO: update descr
   */
  DvG_BinarySerialCommand(Stream &stream, uint8_t *buffer, uint16_t max_len,
                          const uint8_t *EOL, uint8_t EOL_len);

  /**
   * @brief Poll the serial port refered to by @p stream for incoming bytes
   * and append them one-by-one to the command buffer @p buffer.
   *
   * @return True when a complete command has been received and is ready to be
   * returned by @ref getCommand(), false otherwise.
   */
  bool available(bool debug_info = false);

  /**
   * @brief Returns the size of the command minus the EOL sentinel
   * TODO: descr
   *
   * @return uint16_t
   */
  uint16_t getCommandLength();

private:
  Stream &_port;           // Reference to the serial port stream to listen to
  uint8_t *_buffer;        // Reference to the command buffer
  uint16_t _max_len;       // Array size of the command buffer
  uint16_t _cur_len;       // Number of currently received command bytes
  bool _found_EOL;         // Has a complete serial command been received?
  const char *_empty = ""; // Empty reply, which is just the '\0' character

  const uint8_t *_EOL;
  uint16_t _EOL_len;
};

/*******************************************************************************
  Parse functions
*******************************************************************************/

/**
 * @brief Safely parse a float value in C-string @p str_in from of position
 * @p pos.
 *
 * @return The parsed float value when successful, 0.0 otherwise.
 */
float parseFloatInString(const char *str_in, uint16_t pos);

/**
 * @brief Safely parse a boolean value in C-string @p str_in from of position
 * @p pos.
 *
 * @return 1 when the string starts with '1' after any leading spaces, zeros or
 * '+' sign has been removed. 1 when the string perfectly matches 'true', 'True'
 * or 'TRUE'. 0 otherwise.
 */
bool parseBoolInString(const char *str_in, uint16_t pos);

/**
 * @brief Safely parse an integer value in C-string @p str_in from of position
 * @p pos.
 *
 * @return The parsed integer value when successful, 0 otherwise.
 */
int parseIntInString(const char *str_in, uint16_t pos);

#endif
