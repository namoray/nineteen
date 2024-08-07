# client.py

import os
import json
import time
import uuid
import base64
import requests
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Assume we have the server's public key
SERVER_PUBLIC_KEY = ...  # Load this from a file or environment variable

# Generate client's key pair
client_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
client_public_key = client_private_key.public_key()

# Generate a symmetric key
symmetric_key = os.urandom(32)  # 256-bit key
symmetric_key_uuid = str(uuid.uuid4())

def encrypt_symmetric_key(public_key, symmetric_key):
    return public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def sign_message(private_key, message):
    return private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

def encrypt_payload(symmetric_key, payload):
    iv = os.urandom(12)
    encryptor = Cipher(algorithms.AES(symmetric_key), modes.GCM(iv), backend=default_backend()).encryptor()
    ciphertext = encryptor.update(json.dumps(payload).encode()) + encryptor.finalize()
    return iv + encryptor.tag + ciphertext

def decrypt_response(symmetric_key, encrypted_response):
    iv, tag, ciphertext = encrypted_response[:12], encrypted_response[12:28], encrypted_response[28:]
    decryptor = Cipher(algorithms.AES(symmetric_key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

# Initialize communication with server
timestamp = int(time.time())
client_uuid = str(uuid.uuid4())
message_to_sign = f"{timestamp}{client_uuid}".encode()
signature = sign_message(client_private_key, message_to_sign)

initial_payload = {
    "timestamp": timestamp,
    "uuid": client_uuid,
    "signature": base64.b64encode(signature).decode(),
    "public_key": client_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode(),
    "encrypted_symmetric_key": base64.b64encode(encrypt_symmetric_key(SERVER_PUBLIC_KEY, symmetric_key)).decode()
}

response = requests.post("http://localhost:8000/initialize", json=initial_payload)
if response.status_code != 200:
    print("Initialization failed")
    exit(1)

# Send encrypted payload
payload = {
    "message": "Hello, server!",
    "nonce": os.urandom(16).hex()  # 16 bytes nonce
}
encrypted_payload = encrypt_payload(symmetric_key, payload)

headers = {
    "X-Hotkey": client_uuid,
    "X-Symmetric-Key-UUID": symmetric_key_uuid
}

response = requests.post(
    "http://localhost:8000/process_payload",
    headers=headers,
    json={"encrypted_payload": base64.b64encode(encrypted_payload).decode()}
)

if response.status_code == 200:
    encrypted_response = base64.b64decode(response.json()["encrypted_response"])
    decrypted_response = decrypt_response(symmetric_key, encrypted_response)
    print("Server response:", json.loads(decrypted_response))
else:
    print("Request failed:", response.text)
