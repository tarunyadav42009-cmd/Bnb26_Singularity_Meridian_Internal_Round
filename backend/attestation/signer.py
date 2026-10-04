import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_key_pair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    return private_key, public_key


def sign_data(private_key, data: bytes) -> str:
    signature = private_key.sign(data)

    return base64.b64encode(signature).decode("utf-8")


def verify_signature(
    public_key: Ed25519PublicKey,
    data: bytes,
    signature_b64: str
) -> bool:

    try:
        signature = base64.b64decode(signature_b64)

        public_key.verify(
            signature,
            data
        )

        return True

    except (InvalidSignature, ValueError):
        return False