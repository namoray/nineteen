import base64
import httpx


async def fetch_image_b64(url: str, httpx_client: httpx.AsyncClient) -> str:

    response = await httpx_client.get(url)
    image_data = response.content
    return base64.b64encode(image_data).decode("utf-8")

def image_b64_is_valid(image_b64: str) -> bool:
    try:
        decoded_data = base64.b64decode(image_b64)
        # Check if the decoded data starts with known image file signatures
        image_signatures = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A',  # PNG
            b'GIF87a', b'GIF89a',  # GIF
            b'\x42\x4D',  # BMP
            b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A',  # TIFF
        ]
        return any(decoded_data.startswith(sig) for sig in image_signatures)
    except base64.binascii.Error:
        return False