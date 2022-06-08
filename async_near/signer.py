import json

import base58
import ed25519


class KeyPair(object):
    def __init__(self, secret_key):
        secret_key = secret_key.split(":")[1] if ":" in secret_key else secret_key
        self._secret_key = ed25519.SigningKey(base58.b58decode(secret_key))
        self._public_key = self._secret_key.get_verifying_key()

    @property
    def public_key(self):
        return self._public_key.to_bytes()

    def encoded_public_key(self):
        return base58.b58encode(self._public_key.to_bytes()).decode("utf-8")

    def sign(self, message):
        return self._secret_key.sign(message)


class Signer(object):
    def __init__(self, account_id, key_pair):
        self._account_id = account_id
        self._key_pair = key_pair

    @property
    def account_id(self):
        return self._account_id

    @property
    def key_pair(self):
        return self._key_pair

    @property
    def public_key(self):
        return self._key_pair.public_key

    def sign(self, message):
        return self._key_pair.sign(message)

    @classmethod
    def from_json(self, j):
        return Signer(j["account_id"], KeyPair(j["secret_key"]))

    @classmethod
    def from_json_file(self, json_file):
        with open(json_file) as f:
            return Signer.from_json(json.loads(f.read()))
