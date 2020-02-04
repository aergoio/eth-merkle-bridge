.PHONY: docker-aergo docker-eth deploy_test_bridge proposer validator unfreeze_service tests clean compile_bridge compile_token protoc 

# Shortcuts for development and testing

docker-aergo:
	# docker build --build-arg GIT_TAG=3f24ea32ddeb27dd1b86671d1622ab2108a1f42e -t aergo/node ./docker_test_nodes/aergo
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
	python3 -m ethaergo_bridge_operator.oracle_deployer -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --privkey_name "proposer" --local_test
	python3 -m ethaergo_bridge_operator.test_setup.freeze_aergo
	python3 -m ethaergo_bridge_operator.test_setup.erc20_deployer -c './test_config.json' -n 'test_erc20' -e 'eth-poa-local' --local_test
	python3 -m ethaergo_bridge_operator.test_setup.arc1_deployer

proposer:
	python3 -m ethaergo_bridge_operator.proposer.client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 1 --privkey_name "proposer" --privkey_pwd "1234" --local_test

validator:
	python3 -m ethaergo_bridge_operator.validator.server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --local_test

unfreeze_service:
	python3 -m unfreeze_service.server -ip 'localhost:7891' -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --privkey_name "broadcaster" --local_test &
	docker run --rm --name=proxy -p 8080:8080 -v $(PWD)/unfreeze_service/envoy/envoy.yaml:/etc/envoy/envoy.yaml envoyproxy/envoy:latest

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
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=. \
		--grpc_python_out=. \
		./proto/unfreeze_service/*.proto

monitor_testnet_bridge:
	# python3 -m ethaergo_bridge_operator.proposer.client -c './configs/testnet/testnet_config.json' -a 'aergo-testnet' -e 'ropsten' --eth_block_time 10 --eco
	docker run -it --rm --name ethaergo_proposer \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/configs/testnet/testnet_config.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		paouvrard/ethaergo_operator:latest \
		ethaergo_bridge_operator.proposer.client \
		-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--eth_block_time 10 --eth_eco
