import hashlib

from async_near.serializer import BinarySerializer


class Signature:
    pass


class SignedTransaction:
    pass


class Transaction:
    pass


class PublicKey:
    pass


class AccessKey:
    pass


class AccessKeyPermission:
    pass


class FunctionCallPermission:
    pass


class FullAccessPermission:
    pass


class Action:
    pass


class CreateAccount:
    pass


class DeployContract:
    pass


class FunctionCall:
    pass


class Transfer:
    pass


class Stake:
    pass


class AddKey:
    pass


class DeleteKey:
    pass


class DeleteAccount:
    pass


tx_schema = dict(
    [
        [Signature, {"kind": "struct", "fields": [["keyType", "u8"], ["data", [64]]]}],
        [
            SignedTransaction,
            {
                "kind": "struct",
                "fields": [["transaction", Transaction], ["signature", Signature]],
            },
        ],
        [
            Transaction,
            {
                "kind": "struct",
                "fields": [
                    ["signerId", "string"],
                    ["publicKey", PublicKey],
                    ["nonce", "u64"],
                    ["receiverId", "string"],
                    ["blockHash", [32]],
                    ["actions", [Action]],
                ],
            },
        ],
        [PublicKey, {"kind": "struct", "fields": [["keyType", "u8"], ["data", [32]]]}],
        [
            AccessKey,
            {
                "kind": "struct",
                "fields": [
                    ["nonce", "u64"],
                    ["permission", AccessKeyPermission],
                ],
            },
        ],
        [
            AccessKeyPermission,
            {
                "kind": "enum",
                "field": "enum",
                "values": [
                    ["functionCall", FunctionCallPermission],
                    ["fullAccess", FullAccessPermission],
                ],
            },
        ],
        [
            FunctionCallPermission,
            {
                "kind": "struct",
                "fields": [
                    ["allowance", {"kind": "option", type: "u128"}],
                    ["receiverId", "string"],
                    ["methodNames", ["string"]],
                ],
            },
        ],
        [FullAccessPermission, {"kind": "struct", "fields": []}],
        [
            Action,
            {
                "kind": "enum",
                "field": "enum",
                "values": [
                    ["createAccount", CreateAccount],
                    ["deployContract", DeployContract],
                    ["functionCall", FunctionCall],
                    ["transfer", Transfer],
                    ["stake", Stake],
                    ["addKey", AddKey],
                    ["deleteKey", DeleteKey],
                    ["deleteAccount", DeleteAccount],
                ],
            },
        ],
        [CreateAccount, {"kind": "struct", "fields": []}],
        [DeployContract, {"kind": "struct", "fields": [["code", ["u8"]]]}],
        [
            FunctionCall,
            {
                "kind": "struct",
                "fields": [
                    ["methodName", "string"],
                    ["args", ["u8"]],
                    ["gas", "u64"],
                    ["deposit", "u128"],
                ],
            },
        ],
        [Transfer, {"kind": "struct", "fields": [["deposit", "u128"]]}],
        [
            Stake,
            {"kind": "struct", "fields": [["stake", "u128"], ["publicKey", PublicKey]]},
        ],
        [
            AddKey,
            {
                "kind": "struct",
                "fields": [["publicKey", PublicKey], ["accessKey", AccessKey]],
            },
        ],
        [DeleteKey, {"kind": "struct", "fields": [["publicKey", PublicKey]]}],
        [DeleteAccount, {"kind": "struct", "fields": [["beneficiaryId", "string"]]}],
    ]
)


def sign_and_serialize_transaction(receiverId, nonce, actions, blockHash, signer):
    assert signer.public_key != None
    assert blockHash != None
    tx = Transaction()
    tx.signerId = signer.account_id
    tx.publicKey = PublicKey()
    tx.publicKey.keyType = 0
    tx.publicKey.data = signer.public_key
    tx.nonce = nonce
    tx.receiverId = receiverId
    tx.actions = actions
    tx.blockHash = blockHash

    msg = BinarySerializer(tx_schema).serialize(tx)
    hash_ = hashlib.sha256(msg).digest()

    signature = Signature()
    signature.keyType = 0
    signature.data = signer.sign(hash_)

    signedTx = SignedTransaction()
    signedTx.transaction = tx
    signedTx.signature = signature

    return BinarySerializer(tx_schema).serialize(signedTx)


def create_create_account_action():
    createAccount = CreateAccount()
    action = Action()
    action.enum = "createAccount"
    action.createAccount = createAccount
    return action


def create_full_access_key_action(pk):
    permission = AccessKeyPermission()
    permission.enum = "fullAccess"
    permission.fullAccess = FullAccessPermission()
    accessKey = AccessKey()
    accessKey.nonce = 0
    accessKey.permission = permission
    publicKey = PublicKey()
    publicKey.keyType = 0
    publicKey.data = pk
    addKey = AddKey()
    addKey.accessKey = accessKey
    addKey.publicKey = publicKey
    action = Action()
    action.enum = "addKey"
    action.addKey = addKey
    return action


def create_delete_access_key_action(pk):
    publicKey = PublicKey()
    publicKey.keyType = 0
    publicKey.data = pk
    deleteKey = DeleteKey()
    deleteKey.publicKey = publicKey
    action = Action()
    action.enum = "deleteKey"
    action.deleteKey = deleteKey
    return action


def create_transfer_action(amount):
    transfer = Transfer()
    transfer.deposit = amount
    action = Action()
    action.enum = "transfer"
    action.transfer = transfer
    return action


create_payment_action = create_transfer_action


def create_staking_action(amount, pk):
    stake = Stake()
    stake.stake = amount
    stake.publicKey = PublicKey()
    stake.publicKey.keyType = 0
    stake.publicKey.data = pk
    action = Action()
    action.enum = "stake"
    action.stake = stake
    return action


def create_deploy_contract_action(code):
    deployContract = DeployContract()
    deployContract.code = code
    action = Action()
    action.enum = "deployContract"
    action.deployContract = deployContract
    return action


def create_function_call_action(methodName, args, gas, deposit):
    functionCall = FunctionCall()
    functionCall.methodName = methodName
    functionCall.args = args
    functionCall.gas = gas
    functionCall.deposit = deposit
    action = Action()
    action.enum = "functionCall"
    action.functionCall = functionCall
    return action
