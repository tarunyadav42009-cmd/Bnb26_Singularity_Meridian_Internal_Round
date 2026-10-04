from signer import (
    generate_key_pair,
    sign_data,
    verify_signature
)


def main():

    private_key, public_key = generate_key_pair()

    message = b"QUORUM BUILDER A TEST"

    signature = sign_data(
        private_key,
        message
    )

    print("=" * 60)
    print("       QUORUM - ED25519 SIGNATURE TEST")
    print("=" * 60)

    print()
    print("Message:")
    print(message.decode())

    print()
    print("Signature:")
    print(signature)

    print()
    print("Verification:")

    valid = verify_signature(
        public_key,
        message,
        signature
    )

    print(valid)

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()