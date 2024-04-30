import pytest

from py_near.account import Account
from py_near.dapps.fts import FtModel


@pytest.fixture(scope="session")
async def rpc_url() -> Account:
    return "https://rpc.testnet.near.org"


@pytest.fixture(scope="session")
async def account(rpc_url) -> Account:
    acc = Account(
        account_id="py-near.testnet",
        rpc_addr=rpc_url,
    )

    await acc.startup()

    # quick check that the account started up correctly
    assert acc.chain_id == "testnet"

    return acc
