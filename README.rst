Jetting Grid
============

This repository involves the Jetting Grid of the Twente Water Tunnel (TWT) facility of the Physics of Fluids research group at the University of Twente.

..
  More details can be found in the Review of Scientific Instruments article found here.

Here, you can find:

- The full electronic design schematics
- The electronics cabinet in 3D-CAD Solidworks
- The microcontroller source code and firmware
- The user control program
- The Jetting Grid protocol generator based on 4D-OpenSimplex noise


Introduction
------------

Upstream of the TWT measurement section is the jetting grid consisting of 112 individual nozzles laid out in a square grid perpendicular to the mean flow. All nozzles are powered by a single water pump providing the driving pressure for the jets. Each nozzle is controlled by an individual solenoid valve that can be programmatically opened or closed. The nozzles will open and close following predefined 'protocols' tailored to different turbulent statistics inside the measurement section.

The valves of the grid come in through the 4 side walls of the tunnel section, with 28 valves through each side: 4 x 28 = 112 valves. Each set of these 28 valves shares a common pressure distribution manifold of which we will monitor the pressure.

An Arduino controls the 112 solenoid valves, reads out the 4 pressure sensors and drives a 16x16 LED matrix to visualize the status of each valve.

Protocol coordinate system (PCS)
--------------------------------

The solenoid valves are ultimately opening and closing jetting nozzles that are laid out in a square grid, aka the protocol coordinate system (PCS): ::

      ●: Indicates a valve & nozzle
      -: Indicates no nozzle & valve exists

         -7 -6 -5 -4 -3 -2 -1  0  1  2  3  4  5  6  7
        ┌─────────────────────────────────────────────┐
      7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
      6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
      5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
      4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
      3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
      2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
      1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
      0 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
     -1 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     -2 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
     -3 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     -4 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
     -5 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
     -6 │ ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ● │
     -7 │ -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  -  ●  - │
        └─────────────────────────────────────────────┘

The PCS spans ``(-7, -7)`` to ``(7, 7)`` where ``(0, 0)`` is the center of the grid. Physical valves are numbered 1 to 112, see `/docs/jetting_grid_indices.pdf </docs/jetting_grid_indices.pdf>`_.