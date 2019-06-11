.PHONY: install compile_bridge compile_token deploy_bridge proposer validator broadcaster protoc tests wallet deploy_token docker clean

install:
	pip install git+ssh://git@github.com/aergoio/herapy.git@4aabc7d2cb45cdbf263a972f6f11857c13118a87
	pip install pytest
	pip install git+ssh://git@github.com/aergoio/merkle-bridge.git@f9b6b367c4a6a0b002f2d3a319cbda47d031707a
	pip install git+ssh://git@github.com/ethereum/web3.py.git@11ef9df28dfbe4b83683a84fec184406165f18d5
	pip install trie

compile_bridge:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/eth_merkle_bridge.lua > contracts/lua/bridge_bytecode.txt

compile_token:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/standard_token.lua > contracts/lua/std_token_bytecode.txt

deploy_bridge:
	python3 -m bridge_operator.bridge_deployer

proposer:
	python3 -m bridge_operator.proposer_client

validator:
	python3 -m bridge_operator.validator_server

protoc:
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=. \
		--grpc_python_out=. \
		./proto/bridge_operator/*.proto

tests:
	python3 -m pytest -s tests/

deploy_token:
	python3 -m ethaergo_wallet.eth_utils.contract_deployer

docker-aergo:
	docker-compose -f ./docker_test_nodes/aergo/docker-compose.yml up

docker-eth:
	docker run --rm --name ethereum-node \
		-v $(PWD)/docker_test_nodes/ethereum:/root \
		-v $(PWD)/docker_test_nodes/ethereum/local-eth-poa.json:/root/local-eth-poa.json \
		ethereum/client-go \
		--datadir ./root init ./root/local-eth-poa.json

	docker run --rm --name ethereum-node -v $(PWD)/docker_test_nodes/ethereum:/root \
		-v $(PWD)/docker_test_nodes/ethereum/bp_pwd.txt:/root/bp_pwd.txt \
		-p 8545:8545 \
		ethereum/client-go \
	 	--nodiscover --datadir ./root \
		--unlock "0x035d4303f9508ddcab6d074cbc5ed82cd0b436ad" --password ./root/bp_pwd.txt \
		--mine --rpcapi web3,eth,net --rpcaddr 0.0.0.0 --rpcport 8545 --rpc --allow-insecure-unlock\
	    --verbosity 5 --rpccorsdomain="*"

clean:
	rm -fr docker_test_nodes/aergo/*/data
	rm -fr docker_test_nodes/ethereum/geth
	docker-compose -f ./docker_test_nodes/aergo/docker-compose.yml down
