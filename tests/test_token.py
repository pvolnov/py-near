import pytest

from py_near.dapps.fts import FtModel


@pytest.fixture
async def usdc():
    return FtModel("usdc.orderly-qa.testnet", 6)


async def test_ft_balance(account, usdc):
    assert await account.ft.get_ft_balance(usdc) == 0
