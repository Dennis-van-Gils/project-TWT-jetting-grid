Protocols
=========

Contains the Python scripts to generate protocols for the jetting grid of the
Twente Water Tunnel facility.

Installation
------------

1) Download the contents of this GitHub folder `here <https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/Dennis-van-Gils/project-TWT-jetting-grid/tree/main/protocols>`_ and unzip.
2) Open Anaconda prompt and navigate into the unzipped folder.
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


Example output
--------------

See the `protocols subfolder </protocols/protocols>`_.

.. image:: /protocols/protocols/proto_example.gif
.. image:: /protocols/protocols/proto_example_alpha.png
.. image:: /protocols/protocols/proto_example_pdfs.png
