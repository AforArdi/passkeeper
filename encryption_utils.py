from cryptography.fernet import Fernet
import os
import base64

def get_master_key() -> bytes:
    """
    Retrieves the master key from environment variables.
    The key is expected to be a URL-safe base64 encoded string.
    """
    master_key_str = os.getenv("BOT_MASTER_KEY")
    if not master_key_str:
        raise ValueError("BOT_MASTER_KEY environment variable not set.")
    # The key must be a URL-safe base64-encoded 32-byte key.
    # Fernet keys are base64-encoded, so we can use it directly.
    return master_key_str.encode('utf-8')

def encrypt_data(data: str) -> bytes:
    """
    Encrypts a string using the master key.
    """
    master_key = get_master_key()
    f = Fernet(master_key)
    return f.encrypt(data.encode('utf-8'))

def decrypt_data(encrypted_data: bytes) -> str:
    """
    Decrypts bytes using the master key.
    """
    master_key = get_master_key()
    f = Fernet(master_key)
    return f.decrypt(encrypted_data).decode('utf-8')

if __name__ == '__main__':
    # To test this module --> BOT_MASTER_KEY environment variable.

    print("--- Encryption Utility Test ---")
    if not os.getenv("BOT_MASTER_KEY"):
        print("BOT_MASTER_KEY not set. Generating a temporary key for testing.")
        os.environ["BOT_MASTER_KEY"] = Fernet.generate_key().decode()

    # Encrypt data
    original_password_data = "MySecretWebsitePassword123!"
    encrypted_password = encrypt_data(original_password_data)
    print(f"Original Data: {original_password_data}")
    print(f"Encrypted Data (base64): {base64.b64encode(encrypted_password).decode()}")

    # Decrypt data
    decrypted_password = decrypt_data(encrypted_password)
    print(f"Decrypted Data: {decrypted_password}")

    assert original_password_data == decrypted_password
    print("Encryption/Decryption successful!")