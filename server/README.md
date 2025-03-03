# TradeMind Backend 📈🤖

## Descripción del Proyecto 📚
TradeMind es una red multiagente especializada en la predicción y estudio de precios de trade-in de smartphones. El backend está construido con FastAPI y utiliza un sistema de agentes inteligentes basado en LangGraph para procesar consultas relacionadas con la compra-venta de dispositivos móviles.

## Características Principales 🌟

### Sistema de Agentes 🤖
- **Procesamiento de Intenciones**: Detecta automáticamente si el usuario quiere comprar, vender o ver gráficos de precios
- **Extracción de Información**: Analiza y extrae datos relevantes sobre dispositivos móviles
- **Evaluación de Estado**: Sistema de clasificación de dispositivos por grado (B, C, D, E)
- **Predicción de Precios**: Estimación de precios basada en múltiples factores
- **Recomendación de Dispositivos**: Sugiere dispositivos basados en presupuesto y preferencias

### API REST 🔌
- Endpoints para:
  - Inicialización de sesiones
  - Procesamiento de mensajes
  - Consulta de historial de conversaciones
- Sistema de sesiones persistentes
- Soporte para CORS

## Estructura del Proyecto 📁

```
server/
├── agent/                 # Lógica de agentes
│   ├── main.py           # Configuración principal del agente
│   ├── tools.py          # Herramientas del agente
│   ├── prompts.py        # Prompts para el LLM
│   ├── models.py         # Modelos de datos
│   ├── agent_state.py    # Gestión de estado
│   └── utils.py          # Utilidades
├── main.py               # Servidor FastAPI
├── requirements.txt      # Dependencias
└── .env                  # Variables de entorno
```

## Requisitos Previos 📋
- Python 3.8+
- API key de OpenAI
- API key de LangChain (opcional, para trazabilidad)
- API key de Tavily (opcional, para búsquedas)

## Configuración del Entorno 🔧

1. Clona el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd TradeMind/server
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python -m venv env
   source env/bin/activate  # En Windows: env\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura las variables de entorno:
   - Copia `.env_example` a `.env`
   - Añade tus claves de API

## Ejecución del Servidor 🚀

```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints 🛣️

### POST /chat
Procesa mensajes del usuario y devuelve respuestas del agente.

```json
{
    "content": "string",
    "type": "string",
    "sessionId": "string (opcional)"
}
```

### POST /init-session
Inicia una nueva sesión de chat.

### GET /messages/{session_id}
Recupera el historial de mensajes de una sesión.

## Documentación de la API 📖
Accede a la documentación interactiva en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Variables de Entorno 🔐
```plaintext
OPENAI_API_KEY=           # API key de OpenAI
LANGCHAIN_API_KEY=        # API key de LangChain
LANGCHAIN_TRACING_V2=     # Activar/desactivar trazabilidad
```

## Estado del Desarrollo 🚧
- [x] Sistema básico de agentes
- [x] Detección de intenciones
- [x] Evaluación de dispositivos
- [x] Predicción de precios
- [x] Recomendación de dispositivos en base a presupuesto
- [x] Generación de gráficos de precios
- [x] API REST funcional
- [ ] Integración con bases de datos reales
- [ ] Mejora del sistema de recomendación