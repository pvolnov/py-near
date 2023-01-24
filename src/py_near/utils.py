import json
from datetime import datetime
from re import sub
from typing import List, Tuple

import base58
from pyonear.transaction import Action


def utcnow():
    return datetime.utcnow()


def timestamp():
    return utcnow().timestamp()


def _camel_case(s):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def actions_to_link(receiver_id, actions: List[Action], network="mainnet"):
    actions_args = []
    for a in actions:
        params = {}
        for p, v in json.loads(a.to_json()).items():
            if p == "access_key":
                if "FunctionCall" in v["permission"]:
                    for par, val in v["permission"]["FunctionCall"].items():
                        v["permission"][_camel_case(par)] = val
                    del v["permission"]["FunctionCall"]
                else:
                    v["permission"] = "FullAccess"
            params[_camel_case(p)] = v
        actions_args.append(
            {
                "type": type(a).__name__.replace("Action", ""),
                "params": params,
            }
        )
    request = base58.b58encode(
        json.dumps(
            {
                "transactions": [
                    {
                        "actions": actions_args,
                        "receiverId": receiver_id,
                    }
                ],
                "network": network,
            }
        ).encode("utf8")
    ).decode("utf8")
    return f"https://my.herewallet.app/{request}"
