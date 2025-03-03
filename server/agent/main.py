from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from langchain.schema import SystemMessage

from .utils import build_prompt, detect_intent_with_context, extract_buying_info, extract_selling_info, intent_change_potential, verify_intent_change
from .tools import generate_graphic_dict, get_release_date, get_today_date, predict_price, recommend_device
from .agent_state import State

load_dotenv()

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Define tools como funciones en lugar de diccionarios
tools = [predict_price, recommend_device, get_today_date, generate_graphic_dict, get_release_date]
llm_with_tools = llm.bind_tools(tools)


def intent_checker(state: State) -> State:
    """Node that checks and updates the intent if needed."""
    
    # Parámetros configurables
    VERIFY_EVERY_N_MESSAGES = 3
    FORCE_CHECK_ON_NEW_TOPIC_KEYWORDS = ["ahora", "entonces", "por otro lado", "cambiando de tema"]
    
    # Determinar si debemos verificar la intención
    messages_count = len(state["messages"])
    last_message = state["messages"][-1].content.lower() if state["messages"] else ""
    
    should_check_intent = (
        not state.get("intent") or  # Sin intención previa
        intent_change_potential(state) or  # Posible cambio detectado por reglas
        messages_count % VERIFY_EVERY_N_MESSAGES == 0 or  # Verificación periódica
        any(keyword in last_message for keyword in FORCE_CHECK_ON_NEW_TOPIC_KEYWORDS)  # Palabras clave de cambio de tema
    )
    
    if should_check_intent:
        # Obtener contexto reciente para el prompt
        context_messages = state["messages"][-3:] if len(state["messages"]) >= 3 else state["messages"]
        context = "\n".join([f"{'Usuario' if msg.type == 'human' else 'Asistente'}: {msg.content}" 
                           for msg in context_messages[:-1]])
        
        # Detectar intención con contexto
        new_intent = detect_intent_with_context(state, llm, context)
        
        if not state.get("intent"):
            state["intent"] = new_intent
            print(f"Initial intent set to: {new_intent}")
        elif new_intent != state["intent"]:
            # Cambio de intención detectado, verificar si debemos actualizar
            confidence = verify_intent_change(state, new_intent, llm)
            if confidence > 0.7:  # Umbral configurable
                print(f"Intent changed from {state['intent']} to {new_intent} (confidence: {confidence})")
                state["intent"] = new_intent
            else:
                print(f"Potential intent change to {new_intent} rejected (confidence: {confidence})")
    
    return state


def info_extractor(state: State) -> State:
    """Node that extracts relevant information based on intent."""
    
    if state["intent"] == "sell" or state["intent"] == "graphic":
        state["device_info"] = extract_selling_info(state, llm)
    elif state["intent"] == "buy":
        state["buying_info"] = extract_buying_info(state, llm)
            
    return state


def prompt_builder(state: State) -> State:
    """Node that builds the appropriate prompt."""
    
    # Build prompt based on state
    system_msg = build_prompt(state)
    
    # Store system message in a safe way (as a string content)
    state["system_prompt_content"] = system_msg.content if system_msg else ""
    
    return state


def assistant(state: State) -> State:
    """Node that handles LLM invocation."""
    
    # Get system message content built in previous node
    system_content = state.get("system_prompt_content", "")
    
    # Create a proper SystemMessage
    system_msg = SystemMessage(content=system_content) if system_content else None
    
    # Invoke LLM with tools
    if system_msg:
        response = llm_with_tools.invoke([system_msg] + state["messages"])
    else:
        response = llm_with_tools.invoke(state["messages"])
    
    if response.content == '':
        response.content = "Lo siento, no he entendido tu consulta. ¿Podrías reformularla?"
    
    # Update state
    state["messages"] = state["messages"] + [response]
    
    return state


# Build graph
builder = StateGraph(State)

# Define nodes
builder.add_node("intent_checker", intent_checker)
builder.add_node("info_extractor", info_extractor)
builder.add_node("prompt_builder", prompt_builder)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges
builder.add_edge(START, "intent_checker")
builder.add_edge("intent_checker", "info_extractor")
builder.add_edge("info_extractor", "prompt_builder")
builder.add_edge("prompt_builder", "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,  # Esto determina si vamos a tools o END
)
builder.add_edge("tools", "intent_checker")  # Volver a verificar intención después de usar herramientas

# Compile graph
react_graph = builder.compile()