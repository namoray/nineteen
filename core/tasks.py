from enum import Enum


class Task(Enum):
    chat_llama_3_1_8b = "chat-llama-3-1-8b"
    chat_llama_3_1_70b = "chat-llama-3-1-70b"
    chat_reflection_70b = "chat-reflection-70b"
    proteus_text_to_image = "proteus-text-to-image"
    proteus_image_to_image = "proteus-image-to-image"
    dreamshaper_text_to_image = "dreamshaper-text-to-image"
    dreamshaper_image_to_image = "dreamshaper-image-to-image"
    flux_schnell_text_to_image = "flux-schnell-text-to-image"
    flux_schnell_image_to_image = "flux-schnell-image-to-image"
    inpaint = "inpaint"
    avatar = "avatar"
    
unique_tasks = set(i.value for i in Task)