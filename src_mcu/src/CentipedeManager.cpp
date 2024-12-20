/**
 * @file    CentipedeManager.cpp
 * @author  Dennis van Gils (vangils.dennis@gmail.com)
 * @version https://github.com/Dennis-van-Gils/project-TWT-jetting-grid
 * @date    28-11-2022
 * @copyright MIT License. See the LICENSE file for details.
 */

// Ignore warning on `snprintf(buf, BUF_LEN, "%s%d\t", buf, _masks[port]);`
// It's safe here.
#pragma GCC diagnostic ignored "-Wformat-truncation"

#include "CentipedeManager.h"
#include "halt.h"

/*******************************************************************************
  CentipedeManager
*******************************************************************************/

CentipedeManager::CentipedeManager() { clear_masks(); }

void CentipedeManager::begin() {
  _cp.initialize();

  for (uint8_t port = 0; port < N_CP_PORTS; port++) {
    _cp.portMode(port, 0);  // Set all channels to output
    _cp.portWrite(port, 0); // Set all channels LOW
  }
}

void CentipedeManager::add_to_masks(CP_Address cp_addr) {
  if (cp_addr.port >= N_CP_PORTS) {
    snprintf(buf, BUF_LEN,
             "CRITICAL: Out-of-bounds port number %d in "
             "`CentipedeManager::add_to_masks()`",
             cp_addr.port);
    halt(7, buf);
  }
  _masks[cp_addr.port] |= (1U << cp_addr.bit);
}

bool CentipedeManager::all_masks_are_zero() {
  bool all_zero = true;
  for (uint8_t port = 0; port < N_CP_PORTS; port++) {
    all_zero &= (_masks[port] == 0);
  }
  return all_zero;
}

void CentipedeManager::report_masks(Stream &mySerial) {
  buf[0] = '\0';
  for (uint8_t port = 0; port < N_CP_PORTS - 1; port++) {
    snprintf(buf, BUF_LEN, "%s%d\t", buf, _masks[port]);
  }
  snprintf(buf, BUF_LEN, "%s%d\n", buf, _masks[N_CP_PORTS - 1]);
  mySerial.print(buf);
}

void CentipedeManager::send_masks() {
  for (uint8_t port = 0; port < N_CP_PORTS; port++) {
    _cp.portWrite(port, _masks[port]);
  }
}
