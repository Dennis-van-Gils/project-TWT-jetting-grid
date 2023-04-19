*This repository involves the Jetting Grid of the Twente Water Tunnel (TWT) facility of the University of Twente, Physics of Fluids group.*

Introduction
============

The Jetting Grid is essentially a turbulence generator. It consists of a rectangular array of 112 individually computer-controlled water jets that are aligned streamwise to the measurement section of our 8 meter tall vertically recirculating water tunnel. Individual jets will turn on and off following predefined 'protocols' tailored to different turbulent statistics inside the measurement section. The protocols are based on 4-dimensional OpenSimplex
noise: a type of gradient noise that features temporal and spatial coherence.

..
  More details can be found in the Review of Scientific Instruments article found here.

In this repository you can find:

- The electronic design schematics
- The electronics cabinet in 3D-CAD Solidworks
- The microcontroller C++ source code and firmware
- The Python user control program
- The Jetting Grid protocol generator based on 4D-OpenSimplex noise

.. figure:: /docs/photos/grid_outside_tunnel.jpg

  *Figure 1: The jetting grid before installation in the tunnel.*

.. figure:: /docs/photos/grid_head_on_inside_tunnel.jpg

  *Figure 2: The jetting grid inside of the tunnel viewed head-on through the measurement section of cross-section 0.45 m by 0.45 m.*


Extended introduction
=====================

All jetting nozzles are powered by a single water pump providing the driving pressure for the jets. Each nozzle is controlled by an individual solenoid valve that can be programmatically opened or closed. The valves of the grid come in through the 4 side walls of the tunnel section with 28 valves through each side: 4 x 28 = 112 valves. Each set of these 28 valves shares a common pressure distribution manifold of which we will monitor the pressure.

An Arduino controls the 112 solenoid valves, reads out the 4 pressure sensors and drives a 16x16 LED matrix to visualize the status of each valve.

Protocol coordinate system (PCS)
================================

The jetting nozzles are laid out in a square grid, aka the protocol coordinate system (PCS): ::

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