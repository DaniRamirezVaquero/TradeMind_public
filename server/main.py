from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import uuid4
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage

from models.database import UserSession, Chat, get_db, Base, engine
from models.schemas import Message, ChatRequest, ChatResponse, ChatCreateRequest, ChatUpdateRequest, MessageRequest
from agent.main import react_graph
from agent.agent_state import initialize_state
from langchain.schema import HumanMessage, AIMessage
from utils.serializer import serialize_state, deserialize_state, get_frontend_messages, serialize_message_frontend

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200",
                   "https://trade-mind-tawny.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_session(db: Session, session_id: Optional[str] = None) -> tuple[str, dict]:
    if session_id:
        session = db.query(UserSession).filter(
            UserSession.user_id == session_id).first()
        if session:
            return session_id, deserialize_state(session.session_data)

    new_session_id = session_id or str(uuid4())
    session_data = initialize_state()
    new_session = UserSession(
        user_id=new_session_id,
        session_data=serialize_state(session_data)
    )
    db.add(new_session)
    db.commit()
    return new_session_id, session_data


def get_chat_preview(messages):
    """Extract a preview from chat messages"""
    if not messages or len(messages) == 0:
        return ""

    # Try to find the last meaningful message
    for msg in reversed(messages):
        if isinstance(msg, dict) and "content" in msg and msg.get("type") in ["Human", "AI"]:
            return msg["content"][:100]

    return ""

# Añadir este endpoint al final del archivo
@app.get("/health-check")
async def health_check():
    """Verificar si el servidor está activo y listo para recibir peticiones."""
    return {"status": "up", "timestamp": datetime.now().isoformat()}

@app.post("/init-session")
async def init_session(db: Session = Depends(get_db)):
    # Create session with default chat
    session_id = str(uuid4())
    session = UserSession(user_id=session_id)
    db.add(session)
    db.commit()  # Commit the session first to ensure it exists before creating chat

    # Create welcome chat with proper initial state
    chat_id = str(uuid4())
    initial_state = initialize_state()
    initial_message = serialize_message_frontend(initial_state["messages"][0])

    chat = Chat(
        id=chat_id,
        user_id=session_id,
        title="Nueva conversación",
        messages=[initial_message]
    )
    db.add(chat)
    db.commit()

    return {
        "sessionId": session_id,
        "chats": [{
            "id": chat_id,
            "title": chat.title,
            "createdAt": chat.created_at.isoformat(),
            "previewText": initial_message["content"][:100]
        }]
    }


@app.get("/sessions/{session_id}/chats")
async def get_session_chats(session_id: str, db: Session = Depends(get_db)):
    # Check if session exists
    session = db.query(UserSession).filter(
        UserSession.user_id == session_id).first()
    if not session:
        # Create new session if not found
        return await init_session(db)

    # Get existing chats
    chats = db.query(Chat).filter(Chat.user_id == session_id).all()

    return {
        "sessionId": session_id,
        "chats": [{
            "id": chat.id,
            "title": chat.title,
            "createdAt": chat.created_at.isoformat(),
            "previewText": get_chat_preview(chat.messages),
            "tokenLimitReached": chat.token_limit_reached  
        } for chat in chats]
    }


@app.post("/chats")
async def create_chat(request: ChatCreateRequest, db: Session = Depends(get_db)):
    # Verify session exists
    session = db.query(UserSession).filter(
        UserSession.user_id == request.sessionId).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create a new chat with initial AI greeting message
    chat_id = str(uuid4())
    initial_state = initialize_state()
    initial_message = serialize_message_frontend(initial_state["messages"][0])

    chat = Chat(
        id=chat_id,
        user_id=request.sessionId,
        title=request.title,
        messages=[initial_message]
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at.isoformat(),
        "previewText": initial_message["content"][:100]
    }


@app.get("/chats/{chat_id}")
async def get_chat(chat_id: str, db: Session = Depends(get_db)):
    # Find the chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Log the messages being returned
    print(
        f"Retrieving chat {chat_id} with {len(chat.messages) if chat.messages else 0} messages")

    # Return chat with messages
    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at.isoformat(),
        "userId": chat.user_id,
        "messages": chat.messages,
        "tokenLimitReached": chat.token_limit_reached  # Añadir esta propiedad
    }
    
# Añadir en main.py
@app.get("/chats/{chat_id}/state")
async def get_chat_state(chat_id: str, db: Session = Depends(get_db)):
    # Encontrar el chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Devolver solo la información de estado que necesitamos
    return {
        "id": chat.id,
        "tokenLimitReached": chat.token_limit_reached
    }

@app.put("/chats/{chat_id}")
async def update_chat(chat_id: str, request: ChatUpdateRequest, db: Session = Depends(get_db)):
    # Find the chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Update title
    chat.title = request.title
    db.commit()
    db.refresh(chat)

    return {
        "id": chat.id,
        "title": chat.title,
        "createdAt": chat.created_at.isoformat()
    }


@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    # Find the chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Delete the chat
    db.delete(chat)
    db.commit()

    return {"success": True, "message": "Chat deleted successfully"}


@app.post("/chats/{chat_id}/message")
async def chat_message(chat_id: str, request: MessageRequest, db: Session = Depends(get_db)):
    # Find the chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Check if the chat is already marked as token limited
    if chat.token_limit_reached:
        raise HTTPException(
            status_code=400, detail="Token limit reached for this conversation")

    # Check if this is the first human message and chat has default title
    is_first_message = not chat.messages or not any(
        msg.get("type") == "Human" for msg in chat.messages)
    has_default_title = chat.title == "Nueva conversación"

    # Log the initial state
    print(
        f"Chat {chat_id} before adding message: {len(chat.messages) if chat.messages else 0} messages")

    try:
        # Initialize agent state from existing messages
        session_state = initialize_state()

        # Add existing messages to session state
        if chat.messages:
            session_state["messages"] = []
            for msg in chat.messages:
                if msg["type"] == "AI":
                    session_state["messages"].append(
                        AIMessage(content=msg["content"]))
                elif msg["type"] == "Human":
                    session_state["messages"].append(
                        HumanMessage(content=msg["content"]))

        # Record the current message count to identify new messages later
        last_message_index = len(session_state["messages"])

        # Add the new message
        human_message = HumanMessage(content=request.content)
        session_state["messages"].append(human_message)

        # Create a new messages list instead of modifying in place
        new_messages_list = list(chat.messages) if chat.messages else []

        # Add human message
        new_messages_list.append({
            "type": "Human",
            "content": request.content
        })

        # Process with agent
        result = react_graph.invoke(session_state, {"recursion_limit": 100})

        # Get new messages from the result
        agent_new_messages = result["messages"][last_message_index + 1:]
        response_messages = [serialize_message_frontend(
            msg) for msg in agent_new_messages]

        # Add AI responses to the new messages list
        for msg in response_messages:
            new_messages_list.append(msg)

        # Generate title if this is the first human message and chat has default title
        updated_title = None
        if is_first_message and has_default_title:
            try:
                # Reuse the LLM from react_graph if possible
                llm = getattr(react_graph, "llm", None) or ChatOpenAI(
                    model="gpt-4", temperature=0.7)
                updated_title = generate_title_for_chat(request.content, llm)
                chat.title = updated_title
                print(
                    f"Generated new title for chat {chat_id}: '{updated_title}'")
            except Exception as e:
                print(f"Error generating title: {str(e)}")

        # Explicitly set the messages column to the new list
        # This ensures SQLAlchemy knows the column has changed
        chat.messages = new_messages_list

        # Update chat in the database
        db.commit()
        chat = db.query(Chat).filter(Chat.id == chat_id).first()

        # Convert to Message format for response
        formatted_response = [
            Message(content=msg["content"], type=msg["type"])
            for msg in response_messages
        ]

        # Include the new title in the response if it was updated
        response = {
            "messages": formatted_response,
            "chatId": chat_id
        }

        if updated_title:
            response["title"] = updated_title

        return response

    except Exception as e:
        error_message = str(e)
        print(f"Error in chat processing: {error_message}")

        # Detección mejorada para los errores de límite de tokens de OpenAI
        is_token_limit_error = any([
            "maximum context length" in error_message,
            "token limit" in error_message,
            "too many tokens" in error_message,
            "context_length_exceeded" in error_message,
            "This model's maximum context length" in error_message,
            "resulted in" in error_message and "tokens" in error_message
        ])

        if is_token_limit_error:
            # Marcar el chat como limitado por tokens
            chat.token_limit_reached = True

            # Agregar mensaje de error como mensaje AI
            token_limit_message = {
                "type": "AI",
                "content": "⚠️ Esta conversación ha alcanzado el límite de tokens. No se pueden procesar más mensajes en este chat. Por favor, crea una nueva conversación para continuar."
            }

            # Añadir el mensaje a la lista de mensajes
            new_messages_list = list(chat.messages) if chat.messages else []

            # Asegurar que el mensaje del usuario también se guarda
            if not any(msg.get("content") == request.content and msg.get("type") == "Human"
                    for msg in new_messages_list):
                new_messages_list.append({
                    "type": "Human",
                    "content": request.content
                })

            new_messages_list.append(token_limit_message)
            chat.messages = new_messages_list

            db.commit()

            # Devolver respuesta con flag de límite alcanzado
            return {
                "messages": [Message(content=token_limit_message["content"], type=token_limit_message["type"])],
                "chatId": chat_id,
                "tokenLimitReached": True
            }

        # Si es otro tipo de error, intentar extraer información más detallada
        try:
            if hasattr(e, 'response') and e.response:
                error_details = e.response.json()
                error_message = error_details.get(
                    'error', {}).get('message', str(e))

            if 'BadRequestError' in str(type(e)) and 'context_length_exceeded' in error_message:
                # Es una OpenAI BadRequestError por límite de contexto
                chat.token_limit_reached = True

                token_limit_message = {
                    "type": "AI",
                    "content": "⚠️ Esta conversación ha alcanzado el límite de tokens. No se pueden procesar más mensajes en este chat. Por favor, crea una nueva conversación para continuar."
                }

                new_messages_list = list(chat.messages) if chat.messages else []
                if not any(msg.get("content") == request.content and msg.get("type") == "Human"
                        for msg in new_messages_list):
                    new_messages_list.append({
                        "type": "Human",
                        "content": request.content
                    })

                new_messages_list.append(token_limit_message)
                chat.messages = new_messages_list

                db.commit()

                return {
                    "messages": [Message(content=token_limit_message["content"], type=token_limit_message["type"])],
                    "chatId": chat_id,
                    "tokenLimitReached": True
                }
        except:
            pass  # Si falla este intento de extraer más detalles, continuar con la respuesta de error estándar

        # Si es otro tipo de error, reenviar
        raise HTTPException(
            status_code=500, detail=f"Error processing message: {error_message}")


@app.get("/messages/{session_id}", response_model=ChatResponse)
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(
        UserSession.user_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Obtenemos mensajes en formato frontend
    frontend_messages = get_frontend_messages(session.session_data)

    # Convertimos al formato Message para la respuesta
    response_messages = [
        Message(content=msg["content"], type=msg["type"])
        for msg in frontend_messages
    ]

    return ChatResponse(
        messages=response_messages,
        sessionId=session_id
    )


def generate_title_for_chat(user_message: str, llm=None) -> str:
    """Generate a concise, descriptive title based on user's first message"""
    if not llm:
        # Use the same model as the agent but with different parameters
        llm = ChatOpenAI(model="gpt-4", temperature=0.7)

    system_prompt = """Genera un título corto y descriptivo (máximo 6 palabras) para una conversación 
    basado en el primer mensaje del usuario. El título debe capturar la esencia de lo que el usuario 
    quiere consultar. No uses comillas ni puntos finales."""

    title_response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])

    # Clean up and limit length
    title = title_response.content.strip()
    if len(title) > 50:
        title = title[:47] + "..."

    return title
