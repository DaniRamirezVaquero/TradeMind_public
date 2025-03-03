from typing import Any, Dict, List, Optional
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage, BaseMessage
from agent.models import DeviceInfo, BuyingInfo
from datetime import date
import json
import uuid

def serialize_model(model: Any) -> Dict:
    """Serializa modelos Pydantic"""
    if isinstance(model, (DeviceInfo, BuyingInfo)):
        data = model.dict()
        # Convertir fecha a string si existe
        if isinstance(data.get('release_date'), date):
            data['release_date'] = data['release_date'].isoformat()
        return data
    if isinstance(model, date):
        return model.isoformat()
    return str(model)

def serialize_message_full(message: Any) -> Dict:
    """Serializa completamente un mensaje para preservar su estructura interna"""
    # Guardar el tipo de mensaje
    message_type = type(message).__name__
    
    data = {
        "_message_type": message_type,
    }
    
    # Guardar contenido
    if hasattr(message, "content"):
        data["content"] = message.content
    
    # Guardar additional_kwargs para AIMessage
    if isinstance(message, AIMessage) and hasattr(message, "additional_kwargs"):
        data["additional_kwargs"] = message.additional_kwargs
    
    # Guardar tool_call_id para ToolMessage
    if isinstance(message, ToolMessage) and hasattr(message, "tool_call_id"):
        data["tool_call_id"] = message.tool_call_id
    
    # Para otros atributos específicos de cada tipo de mensaje
    if hasattr(message, "__dict__"):
        for key, value in message.__dict__.items():
            if key not in ["content", "additional_kwargs", "tool_call_id"] and not key.startswith("_"):
                try:
                    # Intentar serializar, si falla usar str()
                    json.dumps(value)
                    data[key] = value
                except (TypeError, OverflowError):
                    data[key] = str(value)
    
    return data

def serialize_message_frontend(message: Any) -> Dict:
    """Convierte un mensaje de Langchain en un diccionario serializable para el frontend."""
    if isinstance(message, AIMessage):
        return {
            "type": "AI",
            "content": message.content
        }
    elif isinstance(message, HumanMessage):
        return {
            "type": "Human",
            "content": message.content
        }
    elif isinstance(message, ToolMessage):
        return {
            "type": "tool_result",
            "content": message.content,
            "tool_call_id": message.tool_call_id
        }
    
    # Para mensajes que son resultados de herramientas (diccionarios)
    if isinstance(message, dict) and "type" in message and message["type"] == "tool":
        return {
            "type": "tool_result",
            "content": message["content"],
            "tool_call_id": message.get("tool_call_id", "default_tool_call_id")
        }
        
    # Caso de fallback para otros tipos de mensajes
    content = str(message)
    if "content=" in content:
        content_start = content.find("content='") + 9
        content_end = content.find("'", content_start)
        content = content[content_start:content_end]
    
    return {
        "type": "tool_result",
        "content": content,
        "tool_call_id": "default_tool_call_id"
    }

def serialize_state(state: Dict) -> Dict:
    """Serializa el estado completo del agente."""
    serialized_state = state.copy()
    
    if "messages" in serialized_state:
        # Serializar cada mensaje con estructura completa para preservar su estado interno
        serialized_state["messages"] = [
            serialize_message_full(msg) for msg in serialized_state["messages"]
        ]
        
        # También guardar una versión simplificada para el frontend
        serialized_state["frontend_messages"] = [
            serialize_message_frontend(msg) for msg in state["messages"]
        ]
    
    if "device_info" in serialized_state:
        serialized_state["device_info"] = serialize_model(serialized_state["device_info"])
        
    if "buying_info" in serialized_state:
        serialized_state["buying_info"] = serialize_model(serialized_state["buying_info"])
    
    return serialized_state

def deserialize_message(message_dict: Dict) -> BaseMessage:
    """Reconstruye un mensaje de Langchain desde su representación serializada."""
    # Si es una serialización completa (tiene _message_type)
    if "_message_type" in message_dict:
        message_type = message_dict["_message_type"]
        
        if message_type == "AIMessage":
            # Reconstruir AIMessage con additional_kwargs si existe
            additional_kwargs = message_dict.get("additional_kwargs", {})
            return AIMessage(content=message_dict.get("content", ""), additional_kwargs=additional_kwargs)
        
        elif message_type == "HumanMessage":
            return HumanMessage(content=message_dict.get("content", ""))
        
        elif message_type == "ToolMessage":
            # Reconstruir ToolMessage con tool_call_id
            tool_call_id = message_dict.get("tool_call_id", "default_tool_call_id")
            return ToolMessage(content=message_dict.get("content", ""), tool_call_id=tool_call_id)
        
        elif message_type == "SystemMessage":
            return SystemMessage(content=message_dict.get("content", ""))
    
    # Fallback para formatos antiguos
    if "type" in message_dict:
        if message_dict["type"] == "AI":
            return AIMessage(content=message_dict["content"])
        elif message_dict["type"] == "Human":
            return HumanMessage(content=message_dict["content"])
        elif message_dict["type"] in ["tool_result", "tool"]:
            tool_call_id = message_dict.get("tool_call_id", "default_tool_call_id")
            return ToolMessage(content=message_dict["content"], tool_call_id=tool_call_id)
    
    # Caso excepcional, devolver como AIMessage
    return AIMessage(content=str(message_dict))

def deserialize_state(state: Dict) -> Dict:
    """Deserializa el estado completo del agente."""
    deserialized_state = state.copy()
    
    # Eliminar la versión para frontend, ya que no la necesitamos en el backend
    if "frontend_messages" in deserialized_state:
        del deserialized_state["frontend_messages"]
    
    if "messages" in deserialized_state:
        deserialized_state["messages"] = [
            deserialize_message(msg) for msg in deserialized_state["messages"]
        ]
    
    if "device_info" in deserialized_state:
        device_data = deserialized_state["device_info"]
        # Convertir string de fecha a objeto date si existe
        if "release_date" in device_data and device_data["release_date"]:
            device_data["release_date"] = date.fromisoformat(device_data["release_date"])
        deserialized_state["device_info"] = DeviceInfo(**device_data)
        
    if "buying_info" in deserialized_state:
        deserialized_state["buying_info"] = BuyingInfo(**deserialized_state["buying_info"])
    
    return deserialized_state

def get_frontend_messages(state: Dict) -> List[Dict]:
    """Extrae los mensajes en formato frontend desde el estado."""
    if "frontend_messages" in state:
        return state["frontend_messages"]
    
    # Si no hay frontend_messages, convertir los mensajes normales
    if "messages" in state:
        return [serialize_message_frontend(msg) for msg in state["messages"]]
    
    return []