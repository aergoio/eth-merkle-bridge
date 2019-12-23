.PHONY: docker_image proposer validator unfreeze_service unfreeze_proxy

docker_image:
	docker build -t ethaergo_operator .

validator0:
	docker run --rm -it --name ethaergo_validator \
		-v $(PWD)/_testnet_operator/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/_testnet_operator/validator0.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/_testnet_operator/logs:/home/eth-merkle-bridge/logs \
		-p 9845:9845 \
		ethaergo_operator \
		ethaergo_bridge_operator.validator.server \
		-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--validator_index 0 --privkey_name "validator0" --anchoring_on

validator1:
	docker run --rm -it --name ethaergo_validator \
		-v $(PWD)/_testnet_operator/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/_testnet_operator/validator1.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/_testnet_operator/logs:/home/eth-merkle-bridge/logs \
		-p 9845:9845 \
		ethaergo_operator \
		ethaergo_bridge_operator.validator.server \
		-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--validator_index 1 --privkey_name "validator1" --anchoring_on

# ...

proposer:
	docker run -it --rm --name ethaergo_proposer \
		-v $(PWD)/_testnet_operator/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/_testnet_operator/proposer.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/_testnet_operator/logs:/home/eth-merkle-bridge/logs \
		ethaergo_operator \
		ethaergo_bridge_operator.proposer.client \
    	-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
    	--eth_block_time 10 --privkey_name "proposer" --anchoring_on

unfreeze_service:
	# unfreeze_service and unfreeze_proxy containers run on the same machine
	docker run -it --rm --name unfreeze_service \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/testnet_config.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		-p 7891:7891 \
		ethaergo_operator \
		unfreeze_service.server \
		-ip '0.0.0.0:7891' -c './config.json' -a 'aergo-local' -e 'eth-poa-local' \
		--privkey_name "broadcaster"

unfreeze_proxy:
	# unfreeze_service and unfreeze_proxy containers run on the same machine
	docker run --rm --name=proxy \
		-p 8080:8080 \
		--network="host" \
		-v $(PWD)/envoy.yaml:/etc/envoy/envoy.yaml \
		envoyproxy/envoy:latest