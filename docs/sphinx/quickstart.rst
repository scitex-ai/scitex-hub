Quick Start
===========

This guide helps you get started with SciTeX Cloud CLI.

Basic Usage
-----------

Check the status of your SciTeX deployment:

.. code-block:: bash

   scitex-cloud status

Start services in development mode:

.. code-block:: bash

   scitex-cloud start --env dev

Stop all services:

.. code-block:: bash

   scitex-cloud stop

Environments
------------

SciTeX Cloud supports multiple deployment environments:

- ``dev``: Local development (127.0.0.1:8000)
- ``nas``: Production deployment (home NAS)

Switch between environments using the ``--env`` flag:

.. code-block:: bash

   scitex-cloud start --env dev   # Development
   scitex-cloud start --env nas   # Production

Configuration
-------------

Environment-specific configuration files are located in:

- ``SECRET/.env.dev`` - Development environment variables
- ``SECRET/.env.nas`` - Production environment variables

Docker Management
-----------------

Manage Docker containers:

.. code-block:: bash

   # View running containers
   scitex-cloud docker ps

   # View logs
   scitex-cloud docker logs

   # Restart services
   scitex-cloud docker restart
