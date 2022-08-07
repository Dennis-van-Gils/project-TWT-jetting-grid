/**
 * @file    CentipedeManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @brief   Manage the output channels of a Centipede object by storing and
 * keeping track of the bitmasks per port.
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef CENTIPEDE_MANAGER_H_
#define CENTIPEDE_MANAGER_H_

#include <array>
using namespace std;

#include "Centipede.h"
#include "halt.h"

// Common character buffer for string formatting
extern const uint8_t BUF_LEN;
extern char buf[];

/**
 * @brief Total number of Centipede ports in use.
 */
const uint8_t NUMEL_CP_PORTS = 8;

/*******************************************************************************
  CP_Address
*******************************************************************************/

/**
 * @brief Structure to hold a Centipede port and bit address.
 */
struct CP_Address {
  uint8_t port;
  uint8_t bit;
};

/*******************************************************************************
  CentipedeManager
*******************************************************************************/

/**
 * @brief Class to manage the output channels of a Centipede object by storing
 * and keeping track of the bitmasks per port.
 *
 * The state of the output channels as decoded by the stored bitmasks will only
 * become effective after @ref send_masks() has been called.
 */
class CentipedeManager {
public:
  /**
   * @brief Construct a new Centipede Manager object.
   */
  CentipedeManager() { clear_masks(); }

  /**
   * @brief Initialize the Centipede, set all channels to output and turn the
   * outputs LOW.
   */
  void begin() {
    cp_.initialize();

    for (uint8_t port = 0; port < NUMEL_CP_PORTS; port++) {
      cp_.portMode(port, 0);  // Set all channels to output
      cp_.portWrite(port, 0); // Set all channels LOW
    }
  }

  /**
   * @brief Set all the stored bitmasks to 0, i.e. set all outputs LOW.
   */
  void clear_masks() { bitmasks_.fill(0); }

  /**
   * @brief Add a single Centipede address to the stored bitmasks, turning that
   * output HIGH.
   *
   * @param cp_addr The Centipede address to set HIGH
   */
  void add_to_masks(CP_Address cp_addr) {
    if (cp_addr.port >= NUMEL_CP_PORTS) {
      snprintf(buf, BUF_LEN,
               "CRITICAL: Out-of-bounds port number %d in "
               "`CentipedeManager::add_to_masks()`",
               cp_addr.port);
      halt(7, buf);
    }
    bitmasks_[cp_addr.port] |= (1U << cp_addr.bit);
  }

  /**
   * @brief Set all the stored bitmasks.
   *
   * @param in The new bitmask values
   */
  void set_masks(std::array<uint16_t, NUMEL_CP_PORTS> in) { bitmasks_ = in; }

  /**
   * @brief Get all the stored bitmasks.
   *
   * @return The stored bitmask values
   */
  std::array<uint16_t, NUMEL_CP_PORTS> get_masks() { return bitmasks_; }

  /**
   * @brief Print the stored bitmasks to the serial stream.
   *
   * @param mySerial The serial stream to report over.
   */
  void report_masks(Stream &mySerial) {
    snprintf(buf, BUF_LEN, "%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n", //
             bitmasks_[0], bitmasks_[1], bitmasks_[2], bitmasks_[3],
             bitmasks_[4], bitmasks_[5], bitmasks_[6], bitmasks_[7]);
    mySerial.print(buf);
  }

  /**
   * @brief Send out the stored bitmasks to the Centipede, setting each output
   * channel HIGH or LOW as per the bitmasks.
   */
  void send_masks() {
    for (uint8_t port = 0; port < NUMEL_CP_PORTS; port++) {
      cp_.portWrite(port, bitmasks_[port]);
    }
  }

private:
  Centipede cp_; // The Centipede object that manages all 128 channels
  std::array<uint16_t, NUMEL_CP_PORTS>
      bitmasks_; // Bitmask values for each of the 8 ports
};

#endif
