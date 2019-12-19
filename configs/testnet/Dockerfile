FROM python:3

RUN git clone https://github.com/aergoio/eth-merkle-bridge.git home/eth-merkle-bridge

WORKDIR /home/eth-merkle-bridge

RUN pip install -r requirements.txt 

ENTRYPOINT ["python3", "-m"]
