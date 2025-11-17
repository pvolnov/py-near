from typing import Optional

from pydantic import BaseModel


class NftMetadata(BaseModel):
    """NFT token metadata model (NEP-177 standard)."""

    title: Optional[str] = None  # ex. "Arch Nemesis: Mail Carrier" or "Parcel #5055"
    description: Optional[str] = None  # free-form description
    media: Optional[str] = None  # URL to associated media, preferably to decentralized, content-addressed storage
    media_hash: Optional[str] = None  # Base64-encoded sha256 hash of content referenced by the `media` field. Required if `media` is included.
    copies: Optional[int] = None  # number of copies of this set of metadata in existence when token was minted.
    issued_at: Optional[str] = None  # ISO 8601 datetime when token was issued or minted
    expires_at: Optional[str] = None  # ISO 8601 datetime when token expires
    starts_at: Optional[str] = None  # ISO 8601 datetime when token starts being valid
    updated_at: Optional[str] = None  # ISO 8601 datetime when token was last updated
    extra: Optional[str] = None  # anything extra the NFT wants to store on-chain. Can be stringified JSON.
    reference: Optional[str] = None  # URL to an off-chain JSON file with more info.
    reference_hash: Optional[str] = None  # Base64-encoded sha256 hash of JSON from reference field. Required if `reference` is included.
