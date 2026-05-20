"""Generate a Fernet key for the SECRET_KEY environment variable."""

from cryptography.fernet import Fernet


def generate_key() -> str:
    """Generate a new Fernet encryption key.

    Returns:
        A base64-encoded Fernet key string.
    """
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    key = generate_key()
    print(f"Generated SECRET_KEY:\n\n{key}\n\nAdd this to your .env file as:\nSECRET_KEY={key}")
