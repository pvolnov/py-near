class JsonProviderError(Exception):
    pass


class TransactionError(JsonProviderError):
    pass


class AccountError(JsonProviderError):
    pass


class BlockError(JsonProviderError):
    pass


class AccessKeyError(JsonProviderError):
    pass


class UnknownAccessKeyError(AccessKeyError):
    """
    The requested public_key has not been found while viewing since the
    public key has not been created or has been already deleted
    """

    pass


class UnknownBlockError(BlockError):
    """
    The requested block has not been produced yet or it has been
    garbage-collected (cleaned up to save space on the RPC node)
    """

    pass


class InternalError(TransactionError, AccountError, BlockError):
    """
    Something went wrong with the node itself or overloaded
    """

    pass


class NoSyncedYetError(BlockError):
    """
    The node is still syncing and the requested block is not in the database yet
    """

    pass


class InvalidAccount(AccountError):
    """
    The requested account_id is invalid
    """

    pass


class UnknownAccount(AccountError):
    """
    The requested account_id has not been found while viewing since the
    account has not been created or has been already deleted
    """

    pass


class NoContractCodeError(AccountError):
    """
    The account does not have any contract deployed on it
    """

    pass


class TooLargeContractStateError(AccountError):
    """
    The requested contract state is too large to be returned from this node
    (the default limit is 50kb of state size)
    """

    pass


class UnavailableShardError(AccountError):
    """
    The node was unable to find the requested data because it does not track the shard where data is present
    """

    pass


class NoSyncedBlocksError(AccountError):
    """
    The node is still syncing and the requested block is not in the database yet
    """

    pass


class InvalidTransactionError(TransactionError):
    """
    An error happened during transaction execution
    """

    pass


class RpcTimeoutError(TransactionError):
    """
    Transaction was routed, but has not been recorded on chain in 10 seconds.
    """

    pass
