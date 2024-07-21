from pydantic import BaseModel


class CheckImageRequest(BaseModel):
    image_b64: str
