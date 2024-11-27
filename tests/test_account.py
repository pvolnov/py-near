import pytest

from py_near.account import Account


@pytest.mark.asyncio
async def test_account_get_balance():
    acc = Account(
        account_id="bob.testnet",
        rpc_addr="https://rpc.testnet.near.org",
    )

    assert await acc.get_balance(account_id=acc.account_id) > 0
