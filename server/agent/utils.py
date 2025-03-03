import json
from typing import Union
from langchain.schema import SystemMessage, BaseMessage
from datetime import date, datetime
import xgboost as xgb
import pandas as pd
import unicodedata

from .constants import DATA_DIR, MODELS_DIR, SUPPORTED_BRANDS
from .agent_state import State
from .models import BuyingInfo, DeviceInfo
from .prompts import BASE_PROMPT, BUYING_INFO_EXTRACT_PROMPT, BUYING_PROMPT, GRADING_BASE_PROMPT, GRAPHIC_INTENT_PROMPT, SELL_INTENT_PROMPT, SELLING_PROMPT, BASIC_INFO_EXTRACTION_PROMPT, DETECT_INTENT_PROMPT


def extract_selling_info(state, llm) -> DeviceInfo:
    # Obtener la información existente del state
    current_info = state.device_info if hasattr(
        state, 'device_info') else DeviceInfo()

    # Extraer solo el contenido de los mensajes del usuario
    conversation_text = "\n".join([
        f"Usuario: {msg.content}" if msg.type == "human" else f"Asistente: {msg.content}"
        for msg in state["messages"]
    ])

    result = llm.invoke([
        SystemMessage(content=BASIC_INFO_EXTRACTION_PROMPT.format(
            conversation=conversation_text))
    ])

    try:
        cleaned_content = result.content.strip()
        # Añadir comprobación del tipo de resultado
        try:
            result_dict = json.loads(cleaned_content)
            if isinstance(result_dict, list):
                print("Warning: LLM returned a list instead of a dictionary")
                # Si es una lista, devolver la información actual o un DeviceInfo vacío
                return current_info or DeviceInfo()
            if not isinstance(result_dict, dict):
                print(
                    f"Warning: LLM returned unexpected type: {type(result_dict)}")
                return current_info or DeviceInfo()
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            print("Contenido del resultado:", cleaned_content)
            return current_info or DeviceInfo()

        # Preservar datos existentes que no sean vacíos
        if current_info:
            # Preservar brand si existe
            if current_info.brand:
                result_dict['brand'] = current_info.brand

            # Preservar model si existe
            if current_info.model:
                result_dict['model'] = current_info.model

            # Preservar storage si existe
            if current_info.storage:
                result_dict['storage'] = current_info.storage

            # Preservar has_5g si existe
            if current_info.has_5g is not None:
                result_dict['has_5g'] = current_info.has_5g

            # Preservar release_date si existe
            if current_info.release_date:
                result_dict['release_date'] = current_info.release_date

        # Asegurar que los campos string no sean None
        result_dict['brand'] = result_dict.get('brand') or ""
        result_dict['model'] = result_dict.get('model') or ""
        result_dict['storage'] = result_dict.get('storage') or ""

        # Procesar fecha si existe y no había una fecha válida previamente
        if result_dict.get('release_date') and not current_info.release_date:
            try:
                date_str = result_dict['release_date']
                if isinstance(date_str, str):
                    if len(date_str.split('/')) == 2:  # Formato MM/YYYY
                        month, year = date_str.split('/')
                        result_dict['release_date'] = f"{year}-{month.zfill(2)}-01"
                    elif len(date_str.split('-')) == 2:  # Formato YYYY-MM
                        result_dict['release_date'] = f"{date_str}-01"
                    elif len(date_str.split('-')) == 3:  # Ya está en formato YYYY-MM-DD
                        # Validar que la fecha sea correcta
                        datetime.strptime(date_str, "%Y-%m-%d")
                        result_dict['release_date'] = date_str
                    else:
                        result_dict['release_date'] = None
            except (ValueError, IndexError):
                result_dict['release_date'] = None

        return DeviceInfo(**result_dict)

    except Exception as e:
        print(f"Error inesperado: {e}")
        print("Contenido del resultado:", cleaned_content)
        # En caso de error, devolver la información existente
        return current_info or DeviceInfo()


def extract_buying_info(state, llm) -> BuyingInfo:
    current_info = state.buying_info if hasattr(
        state, 'buying_info') else BuyingInfo()

    conversation_text = "\n".join([
        f"Usuario: {msg.content}" if msg.type == "human" else f"Asistente: {msg.content}"
        for msg in state["messages"]
    ])

    result = llm.invoke([
        SystemMessage(content=BUYING_INFO_EXTRACT_PROMPT.format(
            conversation=conversation_text))
    ])

    try:
        cleaned_content = result.content.strip()
        result_dict = json.loads(cleaned_content)

        # Preservar datos existentes que no sean vacíos
        if current_info:
            # Preservar budget si existe
            if current_info.budget:
                result_dict['budget'] = current_info.budget

            # Preservar brand_preference si existe
            if current_info.brand_preference:
                result_dict['brand_preference'] = current_info.brand_preference

            # Preservar min_storage si existe
            if current_info.min_storage:
                result_dict['min_storage'] = current_info.min_storage

            # Preservar grade_preference si existe
            if current_info.grade_preference:
                result_dict['grade_preference'] = current_info.grade_preference

        # Asegurar que los campos string no sean None
        result_dict['brand_preference'] = result_dict.get(
            'brand_preference') or ""
        result_dict['grade_preference'] = result_dict.get(
            'grade_preference') or ""

        return BuyingInfo(**result_dict)

    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        print("Contenido del resultado:", cleaned_content)
        # En caso de error, devolver la información existente
        return BuyingInfo()


def build_prompt(state: State) -> SystemMessage:
    """Build system prompt based on conversation stage."""

    base_prompt = BASE_PROMPT

    if state["intent"] == "sell" or state["intent"] == "graphic":
        # Detectar la etapa actual basándonos en el último mensaje
        state["stage"] = "info_gathering"  # default

        # Buscar palabras clave en los últimos mensajes para determinar la etapa
        last_messages = state["messages"][-3:] if len(
            state["messages"]) > 3 else state["messages"]
        for msg in reversed(last_messages):
            if isinstance(msg, BaseMessage):
                content = msg.content.lower()
                if "lanzamiento" in content or "fecha" in content or got_basic_info(state):
                    state["stage"] = "grade_assessment"
                    break
                elif any(word in content for word in ["5g", "almacenamiento", "modelo"]):
                    state["stage"] = "info_gathering"
                elif any(word in content for word in ["estado", "condición", "pantalla"]):
                    state["stage"] = "grade_assessment"
                    break

        # Construir el prompt base
        device_info = state["device_info"]
        inferred_info = f"""
        INFORMACIÓN INFERIDA:
        - Marca: {device_info.brand}
        - Modelo: {device_info.model}
        - Almacenamiento: {device_info.storage}
        - Conectividad 5G: {device_info.has_5g}
        - Fecha de lanzamiento: {device_info.release_date}
        """

        base_prompt = SELLING_PROMPT.format(
            conversation_state="Current stage: " + state["stage"]) + inferred_info

        # Añadir el GRADING_PROMPT si estamos en la fase de evaluación
        if state["stage"] == "grade_assessment":
            # Primero añadimos el prompt base de evaluación
            base_prompt = base_prompt + "\n\n" + GRADING_BASE_PROMPT

            # Luego añadimos el prompt específico según la intención
            if state["intent"] == "sell":
                base_prompt = base_prompt + "\n\n" + SELL_INTENT_PROMPT
            elif state["intent"] == "graphic":
                base_prompt = base_prompt + "\n\n" + GRAPHIC_INTENT_PROMPT

    elif state["intent"] == "buy":
        base_prompt = BUYING_PROMPT

    return SystemMessage(content=base_prompt)


def got_basic_info(state: State) -> bool:
    current_device_info = state["device_info"]

    device_info_dict = current_device_info.model_dump()
    # Remove estimated_price from validation
    device_info_dict.pop('estimated_price', None)

    for field in device_info_dict.values():
        if field is None or field == "":
            return False

    return True


def got_basic_buying_info(state: State) -> bool:
    current_buying_info = state["buying_info"]

    if current_buying_info.budget is None or current_buying_info.budget == 0:
        return False

    return True


def parse_date(date_str: Union[str, date]) -> date:
    """Convierte una string de fecha en objeto date."""
    if isinstance(date_str, date):
        return date_str
    try:
        # Intenta parsear primero como MM/YYYY
        if '/' in date_str and len(date_str.split('/')) == 2:
            month, year = date_str.split('/')
            return date(int(year), int(month), 1)
        # Intenta diferentes formatos comunes
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"No se pudo convertir '{date_str}' a fecha")
    except ValueError as e:
        raise ValueError(f"Error al procesar la fecha: {e}")


def detect_intent(state: State, llm) -> json:
    """Analiza el último mensaje del usuario para conocer si quiere vender o comprar un dispositivo."""
    last_message = state["messages"][-1].content.lower()

    result = llm.invoke([
        SystemMessage(content=DETECT_INTENT_PROMPT.format(
            message=last_message, intent=state["intent"]))
    ])

    print("DETECT INTENT RESULT:", result.content)

    return result.content


def detect_intent_with_context(state: State, llm, context: str) -> str:
    """Detecta intención considerando el contexto de la conversación."""
    last_message = state["messages"][-1].content
    current_intent = state.get("intent", "none")

    result = llm.invoke([
        SystemMessage(content=DETECT_INTENT_PROMPT.format(
            message=last_message,
            context=context,
            intent=current_intent))
    ])

    detected_intent = result.content.strip().lower()

    # Validación básica de la respuesta
    valid_intents = ["buy", "sell", "graphic", "none"]
    if detected_intent not in valid_intents:
        print(
            f"Invalid intent detected: '{detected_intent}', defaulting to current: '{current_intent}'")
        return current_intent if current_intent != "none" else "none"

    return detected_intent


def verify_intent_change(state: State, new_intent: str, llm) -> float:
    """Verifica la confianza en un cambio de intención detectado."""
    last_message = state["messages"][-1].content
    current_intent = state.get("intent", "none")

    # Prompt específico para verificar cambio de intención
    verification_prompt = f"""
    Evalúa la confianza (de 0.0 a 1.0) de que el siguiente mensaje del usuario indica un cambio de intención de "{current_intent}" a "{new_intent}".
    
    Mensaje: "{last_message}"
    
    Responde ÚNICAMENTE con un número entre 0.0 (sin confianza) y 1.0 (máxima confianza).
    """

    result = llm.invoke([SystemMessage(content=verification_prompt)])

    try:
        # Extraer el valor numérico de la respuesta
        confidence = float(result.content.strip())
        return max(0.0, min(1.0, confidence))  # Limitar entre 0.0 y 1.0
    except ValueError:
        print(f"Could not parse confidence value from: '{result.content}'")
        return 0.5  # Valor medio por defecto en caso de error

# Cargar el dataframe de referencia de modelos


def load_model_reference():
    try:
        df = pd.read_csv(DATA_DIR / "Modelo_REF.csv", sep=';')
        # Crear un diccionario para mapear nombre de modelo a ID
        model_mapping = dict(zip(df['Modelo'], df['Modelo_NUM']))
        return model_mapping
    except Exception as e:
        print(f"Error loading model reference data: {e}")
        return {}

# Cargar el mapeo de marcas y modelos


def load_brand_model_reference():
    try:
        df = pd.read_csv(DATA_DIR / "Marca_Modelo_REF.csv", sep=';')
        # Agrupar modelos por marca
        brand_models = {}
        for _, row in df.iterrows():
            brand = row['Marca'].lower()
            model = row['Modelo']
            if brand not in brand_models:
                brand_models[brand] = []
            brand_models[brand].append(model)
        return brand_models
    except Exception as e:
        print(f"Error loading brand-model reference data: {e}")
        return {}


# Cargar el modelo XGBoost para una marca específica
def load_xgboost_model(brand: str):
    try:
        brand = brand.lower()
        if brand not in SUPPORTED_BRANDS:
            print(f"Brand {brand} not supported")
            return None

        model_filename = SUPPORTED_BRANDS[brand]
        model_path = MODELS_DIR / model_filename

        if not model_path.exists():
            print(f"Model file {model_path} not found")
            return None

        # Cargar el modelo
        model = xgb.XGBRegressor()
        model.load_model(str(model_path))

        return model
    except Exception as e:
        print(f"Error loading XGBoost model for {brand}: {e}")
        return None


def normalize_text(text):
    """Elimina acentos y caracteres especiales de un texto."""
    # Descompone caracteres acentuados en su base + acento
    text_normalized = unicodedata.normalize('NFD', text)
    # Elimina los caracteres de acento (categoría "Mark, Nonspacing")
    text_without_accents = ''.join(
        [c for c in text_normalized if not unicodedata.category(c).startswith('Mn')])
    return text_without_accents.lower()


def intent_change_potential(state: State) -> bool:
    """Determina si el último mensaje del usuario sugiere un cambio de intención."""
    # Si no hay mensajes suficientes o no hay intención establecida, siempre retornar True
    if len(state["messages"]) < 2 or not state.get("intent"):
        return True

    last_message = state["messages"][-1].content.lower()
    # Normalizar el mensaje (quitar acentos)
    normalized_message = normalize_text(last_message)

    # Categorías de palabras clave por intención
    intent_keywords = {
        "buy": ["comprar", "compro", "adquirir", "recomendar", "busco", "quiero comprar",
                "presupuesto", "cuanto cuesta", "opciones", "modelos", "recomendacion"],
        "sell": ["vender", "vendo", "cuanto me dan", "tasar", "precio de mi", "valor de mi"],
        "graphic": ["grafica", "evolucion", "depreciacion", "cambio de precio",
                    "historico", "tendencia"]
    }

    # Normalizar todas las palabras clave (quitar acentos)
    normalized_intent_keywords = {}
    for intent, keywords in intent_keywords.items():
        normalized_intent_keywords[intent] = [
            normalize_text(keyword) for keyword in keywords]

    # Frases indicadoras de cambio explícito
    change_phrases = [
        "mejor quiero", "en realidad", "he cambiado de", "prefiero",
        "ahora quiero", "pensandolo mejor", "al final", "en vez de eso",
        "mejor dicho", "olvidalo", "dejando eso de lado", "cambiando de tema"
    ]

    # Normalizar frases de cambio (quitar acentos)
    normalized_change_phrases = [normalize_text(
        phrase) for phrase in change_phrases]

    # Verificar cambio explícito
    if any(phrase in normalized_message for phrase in normalized_change_phrases):
        return True

    # Verificar si hay palabras clave de una intención diferente a la actual
    current_intent = state.get("intent", "none")
    for intent, keywords in normalized_intent_keywords.items():
        # Si detectamos palabras clave de otra intención
        if intent != current_intent and any(word in normalized_message for word in keywords):
            return True

    # Análisis sintáctico básico para detectar preguntas nuevas (también normalizado)
    question_starters = ["puedo", "puedes",
                         "podrias", "como", "cuanto", "que", "cual"]
    if any(normalized_message.startswith(starter) for starter in question_starters):
        # Verificar si la pregunta indica una nueva intención
        return True

    return False
