Protocols
=========

Contains the Python scripts to generate protocols for the jetting grid of the
Twente Water Tunnel facility.

Installation
------------
    
In Anaconda prompt::

    conda create -n simplex python=3.10
    conda activate simplex
    pip install -r requirements.txt

Usage
-----

* Edit ``config_proto_opensimplex.py`` to your needs.
* Set global flags in ``make_proto_opensimplex.py`` to your needs.

In Anaconda prompt::
        
    conda activate simplex
    ipython make_proto_opensimplex.py

See the `protocols subfolder </protocols/protocols>`_ for an example of the generated output.
