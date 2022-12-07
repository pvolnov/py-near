from pydantic import BaseModel


class NearTrustTransaction(BaseModel):
    from_account_id: str
    amount: str


class FtTrustTransaction(BaseModel):
    from_account_id: str
    ft_contract_id: str
    ft_amount: str


class NftTrustTransaction(BaseModel):
    from_account_id: str
    nft_contract_id: str
    nft_token_id: str
