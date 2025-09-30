import hmac
import hashlib
from binascii import hexlify


def sign_by_hmac_sha256(payload: str, key: str) -> bytes:
    """Signs payload using HMAC-SHA256 with the given key.
    
    Args:
        payload: The message to sign
        key: The secret key
        
    Returns:
        The HMAC-SHA256 signature as bytes
    """
    h = hmac.new(key.encode(), payload.encode(), hashlib.sha256)
    return h.digest()


def sign_by_hmac_sha256_to_hex(payload: str, key: str) -> str:
    """Signs payload using HMAC-SHA256 and returns hex encoded signature.
    
    Args:
        payload: The message to sign
        key: The secret key
        
    Returns:
        The HMAC-SHA256 signature as a hex string
    """
    signature = sign_by_hmac_sha256(payload, key)
    return hexlify(signature).decode()
