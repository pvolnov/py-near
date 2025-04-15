import json

import base58
from nacl import signing

from py_near.mpc.auth.base import AuthContract


class DefaultAuthContract(AuthContract):
    root_pk: signing.SigningKey
    contract_id: str = "default.auth.hot.tg"

    def __init__(self, root_pk: signing.SigningKey):
        self.root_pk = root_pk
        super().__init__()

    def generate_user_payload(self, msg_hash: bytes):
        auth_signature = base58.b58encode(self.root_pk.sign(msg_hash).signature).decode(
            "utf-8"
        )
        return json.dumps(
            dict(
                signature=auth_signature,
                public_key=base58.b58encode(
                    bytes(self.root_pk.verify_key.encode())
                ).decode(),
            )
        )

