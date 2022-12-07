NEAR = 1_000_000_000_000_000_000_000_000


class DappClient:
    def __init__(
        self,
        account: "Account",
    ):
        self._account = account
