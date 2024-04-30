async def test_account_get_balance(account):
    assert await account.get_balance() > 0
