Installation
============

Requirements
------------

- Python 3.11 or higher
- Docker (for deployment management)

Install from PyPI
-----------------

.. code-block:: bash

   pip install scitex-cloud

Install with all optional dependencies:

.. code-block:: bash

   pip install scitex-cloud[all]

Install from Source
-------------------

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-cloud.git
   cd scitex-cloud
   pip install -e .[all]

Verify Installation
-------------------

After installation, verify it works:

.. code-block:: bash

   scitex-cloud --version
   scitex-cloud --help
