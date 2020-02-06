from datetime import datetime
import json
import sys

import aergo.herapy as herapy

assert len(sys.argv) == 2, "Please provide password to encrypt key"
password = sys.argv[1]

print('Generating a new json keystore...')

hera = herapy.Aergo()
hera.new_account()
keystore = hera.export_account_to_keystore(password)
print(keystore)

hera.import_account_from_keystore(keystore, password, True)
print("Decryption test OK: ", hera.get_address())

time = str(datetime.utcnow().isoformat('T', 'seconds'))
ks_file_name = "{addr}__{time}__keystore.json".format(
    addr=keystore['aergo_address'], time=time)

print("Storing file in: ", ks_file_name)
with open(ks_file_name, 'w') as f:
    json.dump(keystore, f, indent=4)
