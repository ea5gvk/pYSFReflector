#! /bin/bash
apt-get update
apt-get upgrade -y
apt-get install net-tools -y
apt-get install python-pip -y
apt-get install python3-pip -y
pip3 install -r requirements.txt
pip3 install aprslib -y
pip install aprslib -y
pip3 install uvicorn -y
pip install uvicorn -y
pip install starlette -y
pip3 install starlette -y
chmod +x *.py
mkdir /var/log/mmdvm
exit 0
