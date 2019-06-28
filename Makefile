.PHONY: install docker-aergo docker-eth deploy_test_bridge proposer validator tests clean compile_bridge compile_token protoc 

install:
	pip install git+ssh://git@github.com/aergoio/herapy.git@4aabc7d2cb45cdbf263a972f6f11857c13118a87
	pip install pytest
	pip install git+ssh://git@github.com/aergoio/merkle-bridge.git@0393a251c56858d87e8968c9bdce157417d0af5e
	pip install git+ssh://git@github.com/ethereum/web3.py.git@11ef9df28dfbe4b83683a84fec184406165f18d5
	pip install trie
	pip install inquirer
	pip install pyfiglet

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

deploy_test_bridge:
	python3 -m ethaergo_wallet.eth_utils.aergo_erc20_deployer
	python3 -m bridge_operator.bridge_deployer

proposer:
	python3 -m bridge_operator.proposer_client

validator:
	python3 -m bridge_operator.validator_server

tests:
	python3 -m pytest -s tests/

clean:
	rm -fr docker_test_nodes/aergo/*/data
	rm -fr docker_test_nodes/ethereum/geth
	docker-compose -f ./docker_test_nodes/aergo/docker-compose.yml down

compile_bridge:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/eth_merkle_bridge.lua > contracts/lua/bridge_bytecode.txt

compile_token:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/standard_token.lua > contracts/lua/std_token_bytecode.txt

protoc:
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=. \
		--grpc_python_out=. \
		./proto/bridge_operator/*.proto