from pydantic import BaseModel


class FtTokenMetadata(BaseModel):
    spec: str
    name: str
    symbol: str
    icon: str
    reference: str
    reference_hash: str
    decimals: int
