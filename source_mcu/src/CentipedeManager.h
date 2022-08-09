/**
 * @file    CentipedeManager.h
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    09-08-2022
 *
 * @brief   Manage the output channels of a Centipede object by storing and
 * keeping track of the bitmasks per port.
 *
 * @copyright MIT License. See the LICENSE file for details.
 */

#ifndef CENTIPEDE_MANAGER_H_
#define CENTIPEDE_MANAGER_H_

// Ignore warning on `snprintf(buf, BUF_LEN, "%s%d\t", buf, masks_[port]);`
// It's safe here.
#pragma GCC diagnostic ignored "-Wformat-truncation"

#include <array>
using namespace std;

#include "Centipede.h"
#include "halt.h"

// Common character buffer for string formatting, see `main.cpp`
extern const uint8_t BUF_LEN;
extern char buf[];

/**
 * @brief Total number of Centipede ports in use.
 *
 * A single Centipede board has 4 ports for controlling a total of 64 channels.
 * A second Centipede board on another I2C address will add 4 more additional
 * ports, allowing a total of 128 channels to be controlled.
 */
const uint8_t N_CP_PORTS = 8;

// TODO: descr
using CP_Masks = std::array<uint16_t, N_CP_PORTS>;

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

    for (uint8_t port = 0; port < N_CP_PORTS; port++) {
      cp_.portMode(port, 0);  // Set all channels to output
      cp_.portWrite(port, 0); // Set all channels LOW
    }
  }

  /**
   * @brief Set all the stored bitmasks to 0, i.e. set all outputs LOW.
   */
  void clear_masks() { masks_.fill(0); }

  /**
   * @brief Add a single Centipede address to the stored bitmasks, turning that
   * output HIGH.
   *
   * @param cp_addr The Centipede address to set HIGH
   */
  void add_to_masks(CP_Address cp_addr) {
    if (cp_addr.port >= N_CP_PORTS) {
      snprintf(buf, BUF_LEN,
               "CRITICAL: Out-of-bounds port number %d in "
               "`CentipedeManager::add_to_masks()`",
               cp_addr.port);
      halt(7, buf);
    }
    masks_[cp_addr.port] |= (1U << cp_addr.bit);
  }

  /**
   * @brief Set all the stored bitmasks to new values.
   *
   * @param in The new bitmask values
   */
  void set_masks(CP_Masks in) { masks_ = in; }

  /**
   * @brief Get all the stored bitmasks.
   *
   * @return The stored bitmask values
   */
  CP_Masks get_masks() { return masks_; }

  /**
   * @brief Print the stored bitmasks to the serial stream.
   *
   * @param mySerial The serial stream to report over.
   */
  void report_masks(Stream &mySerial) {
    buf[0] = '\0';
    for (uint8_t port = 0; port < N_CP_PORTS - 1; port++) {
      snprintf(buf, BUF_LEN, "%s%d\t", buf, masks_[port]);
    }
    snprintf(buf, BUF_LEN, "%s%d\n", buf, masks_[N_CP_PORTS - 1]);
    mySerial.print(buf);
  }

  /**
   * @brief Send out the stored bitmasks to the Centipede, setting each output
   * channel HIGH or LOW as per the bitmasks.
   */
  void send_masks() {
    for (uint8_t port = 0; port < N_CP_PORTS; port++) {
      cp_.portWrite(port, masks_[port]);
    }
  }

private:
  Centipede cp_; // The Centipede object controlling up to two Centipede boards
  CP_Masks masks_; // Bitmask values for each of the ports in use
};

#endif
