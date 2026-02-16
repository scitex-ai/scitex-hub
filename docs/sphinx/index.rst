SciTeX Cloud Documentation
==========================

SciTeX Cloud is a deployment and management CLI for the SciTeX scientific writing platform.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   setup
   quickstart
   api/index

Installation
------------

Install SciTeX Cloud using pip:

.. code-block:: bash

   pip install scitex-cloud

Quick Start
-----------

After installation, use the CLI to manage your SciTeX deployment:

.. code-block:: bash

   # Check status
   scitex-cloud status

   # Start services
   scitex-cloud start --env dev

   # Stop services
   scitex-cloud stop

API Reference
-------------

For detailed API documentation, see the :doc:`api/index` section.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
