from near_jsonrpc_models import RpcTransactionResponse

from py_near.models import TransactionResult


def map_rpc_transaction_to_result(
    rpc_transaction_response: RpcTransactionResponse,
) -> TransactionResult:

    final = rpc_transaction_response

    def dump(model):
        return model.model_dump(
            by_alias=False,
            exclude_none=True,
        )

    receipts_outcome = [
        dump(ro) for ro in final.receipts_outcome
    ]

    transaction_outcome = dump(final.transaction_outcome)

    transaction = dump(final.transaction)

    status = dump(final.status)

    kwargs = {}
    if hasattr(final, "receipts"):
        kwargs["receipts"] = [dump(r) for r in final.receipts]

    return TransactionResult(
        receipts_outcome=receipts_outcome,
        transaction_outcome=transaction_outcome,
        transaction=transaction,
        status=status,
        **kwargs,
    )
