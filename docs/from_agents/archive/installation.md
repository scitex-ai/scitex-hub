<!-- ---
!-- Timestamp: 2025-07-01 09:02:07
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/installation.md
!-- --- -->

./externals/install_externals.sh
python -m venv .env
source .env/bin/activate
pip install -m pip -U
pip install -r ./docs/requirements.txt

<!-- EOF -->