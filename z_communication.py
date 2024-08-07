import os
import json
import time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# Key generation functions (unchanged)
def generate_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    return private_key


V_PRIVATE_KEY = generate_key_pair()
V_PUBLIC_KEY = V_PRIVATE_KEY.public_key()

M_PRIVATE_KEY = generate_key_pair()
M_PUBLIC_KEY = M_PRIVATE_KEY.public_key()

print("Keys generated for validator and miner")


# Helper functions
def public_key_to_pem(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def generate_session_key():
    return os.urandom(32)  # 256-bit key for AES


def encrypt_session_key(public_key, session_key):
    return public_key.encrypt(
        session_key, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )


def decrypt_session_key(private_key, encrypted_session_key):
    return private_key.decrypt(
        encrypted_session_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )


def encrypt_message(session_key, message):
    iv = os.urandom(12)  # 96-bit IV for GCM
    encryptor = Cipher(algorithms.AES(session_key), modes.GCM(iv), backend=default_backend()).encryptor()
    ciphertext = encryptor.update(message.encode()) + encryptor.finalize()
    return iv + encryptor.tag + ciphertext


def decrypt_message(session_key, encrypted_message):
    iv = encrypted_message[:12]
    tag = encrypted_message[12:28]
    ciphertext = encrypted_message[28:]
    decryptor = Cipher(algorithms.AES(session_key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


# Simplified signing function
def sign(message):
    return ""


# Main process
vali_hotkey = "your_validator_hotkey_here"
timestamp = int(time.time())
message_to_sign = f"{timestamp}{vali_hotkey}"

payload = {
    "public_key": public_key_to_pem(V_PUBLIC_KEY),
    "vali_hotkey": vali_hotkey,
    "timestamp": timestamp,
    "signature": sign(message_to_sign),
    "large_data": "A" * 100000000,  # Simulate 1MB of data
}

# Validator: Create and encrypt payload
session_key = generate_session_key()
encrypted_session_key = encrypt_session_key(M_PUBLIC_KEY, session_key)
encrypted_payload = encrypt_message(session_key, json.dumps(payload))

print("\nValidator: Payload created and encrypted")
print(f"Encrypted session key length: {len(encrypted_session_key)}")
print(f"Encrypted payload length: {len(encrypted_payload)}")
print(f"Encyrpted payload size in mb: {len(encrypted_payload) / 1024 / 1024}")

# Miner: Decrypt and process payload
miner_session_key = decrypt_session_key(M_PRIVATE_KEY, encrypted_session_key)
decrypted_payload = decrypt_message(miner_session_key, encrypted_payload)
payload_json = json.loads(decrypted_payload)

print("\nMiner: Payload decrypted")
print(f"Decrypted payload length: {len(decrypted_payload)}")

# Assume signature is always valid
signature_valid = True
print(f"\nMiner: Signature assumed valid: {signature_valid}")

# Miner: Send response
response = {"success": signature_valid}
encrypted_response = encrypt_message(miner_session_key, json.dumps(response))

print("\nMiner: Response encrypted and sent")
print(f"Encrypted response length: {len(encrypted_response)}")

# Validator: Decrypt response
decrypted_response = decrypt_message(session_key, encrypted_response)
response_json = json.loads(decrypted_response)

print("\nValidator: Response decrypted")
print(f"Decrypted response: {json.dumps(response_json, indent=2)}")

# TODO: ADD A NONCE / UUID to prevent replay attacks
