.PHONY: docker-aergo docker-eth deploy_test_bridge proposer validator tests clean compile_bridge compile_token protoc 

# Shortcuts for development and testing

docker-aergo:
	# docker build --build-arg GIT_TAG=5a16373a3c535f77304709f725e10284dccfbea1 -t aergo/node ./docker_test_nodes/aergo
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
	 	--nodiscover --datadir ./root --networkid 52306\
		--unlock "0x035d4303f9508ddcab6d074cbc5ed82cd0b436ad" --password ./root/bp_pwd.txt \
		--mine --rpcapi web3,eth,net --rpcaddr 0.0.0.0 --rpcport 8545 --rpc --allow-insecure-unlock\
	    --verbosity 5 --rpccorsdomain="*"

deploy_test_bridge:
	python3 -m ethaergo_bridge_operator.test_setup.erc20_deployer -c './test_config.json' -n 'aergo_erc20' -e 'eth-poa-local' --local_test
	python3 -m ethaergo_bridge_operator.bridge_deployer -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --privkey_name "proposer" --local_test
	python3 -m ethaergo_bridge_operator.test_setup.freeze_aergo
	python3 -m ethaergo_bridge_operator.test_setup.erc20_deployer -c './test_config.json' -n 'test_erc20' -e 'eth-poa-local' --local_test
	python3 -m ethaergo_bridge_operator.test_setup.arc1_deployer

proposer:
	python3 -m ethaergo_bridge_operator.proposer.client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 1 --privkey_name "proposer" --auto_update --local_test

validator:
	python3 -m ethaergo_bridge_operator.validator.server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --auto_update --local_test

tests:
	python3 -m pytest -s tests/

clean:
	rm -fr docker_test_nodes/aergo/*/data
	rm -fr docker_test_nodes/ethereum/geth
	docker-compose -f ./docker_test_nodes/aergo/docker-compose.yml down

compile_bridge:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/eth_merkle_bridge.lua > contracts/lua/bridge_bytecode.txt

compile_oracle:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/oracle.lua > contracts/lua/oracle_bytecode.txt

compile_token:
	$(GOPATH)/src/github.com/aergoio/aergo/bin/aergoluac --payload contracts/lua/standard_token.lua > contracts/lua/std_token_bytecode.txt

protoc:
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=. \
		--grpc_python_out=. \
		./proto/ethaergo_bridge_operator/*.proto