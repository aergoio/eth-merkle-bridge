docker_image:
	docker build -t ethaergo_operator .
	# docker tag d5ee88e88ea4 paouvrard/ethaergo_operator:0.3.2
	# docker push paouvrard/ethaergo_operator:0.3.2

# Folder structure for each operator:
# proposer_root /
#	validator0.json
#	keystore/UTC--2019-09-03...

validator0:
	docker run -it --name ethaergo_validator \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/validator0.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		-p 9845:9845 \
		paouvrard/ethaergo_operator:latest \
		ethaergo_bridge_operator.validator.server \
		-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--validator_index 0 --privkey_name "validator0" --anchoring_on

validator1:
	docker run -it --name ethaergo_validator \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/validator1.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		-p 9845:9845 \
		paouvrard/ethaergo_operator:latest \
		ethaergo_bridge_operator.validator.server \
		-c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--validator_index 1 --privkey_name "validator1" --anchoring_on

# ...

proposer:
	docker run -it --rm --name ethaergo_proposer \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/proposer.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		paouvrard/ethaergo_operator:latest \
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
		paouvrard/ethaergo_operator:latest \
		unfreeze_service.server \
		-ip '0.0.0.0:7891' -c './config.json' -a 'aergo-testnet' -e 'ropsten' \
		--privkey_name "broadcaster"

unfreeze_proxy:
	# unfreeze_service and unfreeze_proxy containers run on the same machine
	docker run --rm --name=proxy \
		-p 8080:8080 \
		-v $(PWD)/envoy.yaml:/etc/envoy/envoy.yaml \
		envoyproxy/envoy:latest


cli:
	docker run -it --rm --name ethaergo_cli \
		-v $(PWD)/keystore:/home/eth-merkle-bridge/keystore \
		-v $(PWD)/proposer.json:/home/eth-merkle-bridge/config.json \
		-v $(PWD)/logs:/home/eth-merkle-bridge/logs \
		paouvrard/ethaergo_operator:latest \
		ethaergo_cli.main