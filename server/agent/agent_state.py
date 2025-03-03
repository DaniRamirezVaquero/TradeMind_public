from typing import Optional
from langgraph.graph import MessagesState
from langchain.schema import AIMessage

from .prompts import BASE_PROMPT
from .models import BuyingInfo, DeviceInfo

class State(MessagesState):
    stage: str = "greeting"  
    intent: Optional[str] = None
    device_info: DeviceInfo = DeviceInfo()
    buying_info: Optional[BuyingInfo] = None
    system_prompt_content: str = ""

    
def initialize_state():
    """Initialize a new conversation state."""
    welcome_message = """## ¡Bienvenido a TradeMind! 🤖📱

Soy tu asistente especializado en la compra-venta de smartphones reacondicionados.

*Si quiere saber más sobre como te puedo ayudar, pulsa el botón de TradeMind.*

¿En qué te puedo ayudar hoy?
"""
    return {
        "messages": [
            AIMessage(content=welcome_message)
        ],
        "stage": "greeting",
        "intent": None,
        "device_info": DeviceInfo(),
        "buying_info": BuyingInfo(),
        "system_prompt_content": BASE_PROMPT,
    }