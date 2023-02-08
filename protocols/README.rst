Protocols
=========

Contains the Python scripts to generate protocols for the jetting grid of the
Twente Water Tunnel facility.

Installation
------------
    
1) Download the contents of this GitHub folder and unzip.
2) Open Anaconda prompt and navigate to the unzipped folder.
3) Now, we will create a separate Python environment called 'twt' to install the necessary packages and run the scripts in.

    In Anaconda prompt::

        conda create -n twt python=3.10
        conda activate twt
        pip install -r requirements.txt

Usage
-----

* Edit ``config_proto_opensimplex.py`` to your needs.
* Set global flags in ``make_proto_opensimplex.py`` to your needs.

In Anaconda prompt::
        
    conda activate twt
    ipython make_proto_opensimplex.py

See the `protocols subfolder </protocols/protocols>`_ for an example of the generated output.
