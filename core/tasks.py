from enum import Enum


class Task(Enum):
    chat_llama_3_1_8b = "chat-llama-3-1-8b"
    chat_llama_3_1_70b = "chat-llama-3-1-70b"
    proteus_text_to_image = "proteus-text-to-image"
    dreamshaper_text_to_image = "dreamshaper-text-to-image"
    flux_schnell_text_to_image = "flux-schnell-text-to-image"
    
