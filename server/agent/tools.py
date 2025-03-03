from datetime import date
import random
from typing import List, Optional, Union, Dict, Any
import numpy as np

from .models import DeviceInfo
from .utils import load_brand_model_reference, load_model_reference, load_xgboost_model, parse_date
from .constants import SUPPORTED_BRANDS, GRADE_MAPPING, MODELS_DIR, DATA_DIR

# Variable global para el mapeo de modelos
MODEL_REFERENCE = {}
# Variable global para el mapeo de marcas y modelos
BRAND_MODEL_MAP = {}

# Inicializar la referencia de modelos y el mapeo de marcas y modelos
try:
    MODEL_REFERENCE = load_model_reference()
    print(f"Loaded {len(MODEL_REFERENCE)} model references")
except Exception as e:
    print(f"Could not initialize model reference: {e}")

try:
    BRAND_MODEL_MAP = load_brand_model_reference()
    print(f"Loaded models for {len(BRAND_MODEL_MAP)} brands")
except Exception as e:
    print(f"Could not initialize brand-model reference: {e}")


def predict_price(
    brand: str,
    model: str,
    storage: str,
    has_5g: bool,
    release_date: Union[str, date],
    grade: str = 'C',
    sale_date: Union[str, date] = date.today()
) -> Union[float, Dict[str, Any]]:
    """Predicts the selling price of a device based on its characteristics."""

    print(
        f"Predicting price for {brand} {model} ({storage}, 5G: {has_5g}, grade: {grade})")
    print(f"Release date: {release_date}, sale date: {sale_date}")

    # Convertir fechas
    release_date = parse_date(release_date)
    sale_date = parse_date(sale_date)

    # Calcular días entre fechas
    fecha_lanzamiento = (sale_date - release_date).days
    if fecha_lanzamiento < 0:
        print(
            f"Warning: Release date {release_date} is in the future relative to sale date {sale_date}")
        fecha_lanzamiento = 0

    # Comprobar si la marca está soportada
    brand_lower = brand.lower()
    if brand_lower not in SUPPORTED_BRANDS:
        print(
            f"Brand {brand} not in supported brands: {list(SUPPORTED_BRANDS.keys())}")
        return {
            "error": "unsupported_brand",
            "message": f"Lo siento, actualmente no podemos ofrecer predicciones para dispositivos de la marca {brand}. Las marcas soportadas son: {', '.join(SUPPORTED_BRANDS.keys())}.",
            "supported_brands": list(SUPPORTED_BRANDS.keys())
        }

    # Intentar encontrar el ID del modelo en el mapping
    model_with_5g = f"{model} 5G" if has_5g and "5G" not in model else model
    model_without_5g = model.replace(" 5G", "") if "5G" in model else model

    Modelo = None
    model_used = None

    # Buscar primero con 5G si tiene 5G
    if has_5g and model_with_5g in MODEL_REFERENCE:
        Modelo = MODEL_REFERENCE[model_with_5g]
        model_used = model_with_5g
    # Si no se encuentra, buscar sin 5G
    elif model_without_5g in MODEL_REFERENCE:
        Modelo = MODEL_REFERENCE[model_without_5g]
        model_used = model_without_5g

    # Si no se encuentra el modelo, devolver un error informativo
    if Modelo is None:
        print(f"Model {model} not found in reference data")
        return {
            "error": "model_not_found",
            "message": f"No encontramos el modelo '{model}' en nuestra base de datos. Podemos hacer una estimación general pero no será tan precisa.",
            "fallback_price": fallback_predict_price(fecha_lanzamiento, grade)
        }

    # Cargar el modelo para la marca
    xgb_model = load_xgboost_model(brand_lower)
    if xgb_model is None:
        return {
            "error": "model_loading_failed",
            "message": f"Hubo un problema al cargar el modelo de predicción para {brand}. Utilizaremos una estimación general.",
            "fallback_price": fallback_predict_price(fecha_lanzamiento, grade)
        }

    try:
        print(f"Predicting price for model ID {Modelo} ({model_used})")

        # Preparar datos para el modelo
        Almacenamiento = int(storage.replace(
            "GB", "").replace("TB", "000").strip())
        print("Storage GB:", Almacenamiento)

        # Obtener día de la semana (0=lunes, 6=domingo)
        dia_semana = sale_date.weekday()
        print("Day of week:", dia_semana)

        # Obtener mes (1-12)
        mes = sale_date.month
        print("mes:", mes)

        # Obtener día del año (1-366)
        Dia_año = sale_date.timetuple().tm_yday
        print("Day of year:", Dia_año)

        # Mapear grado a número
        Grado = GRADE_MAPPING.get(grade, 3)  # Por defecto C=3
        print("Grade:", Grado)

        features = np.array([[
            Modelo, Almacenamiento, fecha_lanzamiento, dia_semana, mes, Dia_año, Grado
        ]])

        # Predicción
        prediction = xgb_model.predict(np.array(features, dtype=np.float32))[0]

        # Redondear a 2 decimales
        final_price = round(float(prediction), 2)

        print(f"XGBoost prediction for {brand} {model_used}: {final_price}")
        return final_price

    except Exception as e:
        print(f"Error during price prediction: {e}")
        return {
            "error": "prediction_error",
            "message": f"Hubo un error al calcular la predicción: {str(e)}. Utilizaremos una estimación general.",
            "fallback_price": fallback_predict_price(fecha_lanzamiento, grade)
        }


def fallback_predict_price(fecha_lanzamiento: int, grade: str) -> float:
    """Método de fallback para predecir precio cuando el modelo falla."""
    print("Using fallback price prediction")

    base_price = random.uniform(800, 1200)
    # Depreciation del 20% por año, mínimo 40% del valor
    age_factor = max(0.4, 1 - (fecha_lanzamiento / 365 * 0.2))
    grade_factors = {'B': 0.8, 'C': 0.6, 'D': 0.4, 'E': 0.2}
    grade_factor = grade_factors.get(grade, 0.5)

    final_price = base_price * age_factor * grade_factor

    return round(final_price, 2)


def recommend_device(
    budget: float, 
    brand_preference: Optional[str] = None, 
    min_storage: Optional[int] = None, 
    grade_preference: Optional[str] = 'B'
) -> Union[List[DeviceInfo], Dict[str, Any]]:
    """Recommends devices based on budget and optional preferences."""
    print(f"Recommending devices within {budget}€ budget")
    print(f"Preferences: Brand={brand_preference}, Min Storage={min_storage}GB, Grade={grade_preference}")
    
    recommended_devices = []
    
    try:
        # Si se especificó una marca, verificar que esté soportada
        if brand_preference:
            brand_lower = brand_preference.lower()
            if brand_lower not in SUPPORTED_BRANDS:
                return {
                    "error": "unsupported_brand",
                    "message": f"Lo siento, actualmente no podemos ofrecer recomendaciones para la marca {brand_preference}. Las marcas soportadas son: {', '.join(SUPPORTED_BRANDS.keys())}.",
                    "supported_brands": list(SUPPORTED_BRANDS.keys())
                }
            
            # Verificar si tenemos modelos para esta marca
            if brand_lower not in BRAND_MODEL_MAP or not BRAND_MODEL_MAP[brand_lower]:
                return {
                    "error": "no_models_for_brand",
                    "message": f"No encontramos modelos disponibles para la marca {brand_preference}.",
                    "fallback_recommendation": get_fallback_recommendation(budget, min_storage, grade_preference)
                }
        
        # Preparar lista de modelos a evaluar
        models_to_evaluate = []
        
        if brand_preference:
            # Usar solo modelos de la marca preferida
            brand_lower = brand_preference.lower()
            if brand_lower in BRAND_MODEL_MAP:
                for model_name in BRAND_MODEL_MAP[brand_lower]:
                    models_to_evaluate.append((brand_preference, model_name))
        else:
            # Usar modelos de todas las marcas soportadas
            for brand, models in BRAND_MODEL_MAP.items():
                if brand.lower() in SUPPORTED_BRANDS:
                    for model_name in models:
                        # Extraer solo el modelo sin la marca
                        if brand in model_name:
                            model_only = model_name.split(brand)[1].strip()
                        else:
                            model_only = model_name
                        
                        models_to_evaluate.append((brand.capitalize(), model_only))
        
        if not models_to_evaluate:
            return {
                "error": "no_matching_models",
                "message": "No encontramos modelos disponibles que coincidan con tus criterios.",
                "fallback_recommendation": get_fallback_recommendation(budget, min_storage, grade_preference)
            }
            
        # Definir opciones de almacenamiento según la preferencia
        if min_storage:
            # Si se especificó un almacenamiento mínimo, usar ese valor exacto
            storage_value = min_storage
            storage_options = [f"{storage_value}GB"]
        else:
            # Si no se especificó almacenamiento, evaluar varias opciones comunes
            storage_options = ["64GB", "128GB", "256GB", "512GB", "1TB"]
        
        # Definir opciones de grado según la preferencia
        if grade_preference:
            # Si se especificó un grado, usar ese valor exacto
            grade_options = [grade_preference]
        else:
            # Si no se especificó grado, evaluar varios grados
            grade_options = ["B", "C", "D", "E"]
        
        # Fecha actual para calcular el precio
        today = date.today()
        
        # Generar todas las combinaciones y calcular precios
        candidates = []
        
        # Definir márgenes de precio por marca y grado
        markup_by_brand = {
            "apple": {"B": 0.60, "C": 0.55, "D": 0.50, "E": 0.45},  # Apple tiene márgenes más altos
            "samsung": {"B": 0.55, "C": 0.50, "D": 0.45, "E": 0.40},
            "xiaomi": {"B": 0.45, "C": 0.40, "D": 0.35, "E": 0.30},
            "default": {"B": 0.50, "C": 0.45, "D": 0.40, "E": 0.35}  # Para otras marcas
        }
        
        for brand, model in models_to_evaluate:
            has_5g = "5G" in model
            
            # Usar fecha de lanzamiento aproximada
            release_date = get_release_date(brand, model) or date(2021, 1, 1)
            
            # Para cada combinación de almacenamiento y grado
            for storage in storage_options:
                for grade in grade_options:
                    # Calcular precio estimado (precio de trade-out)
                    price_result = predict_price(brand, model, storage, has_5g, release_date, grade, today)
                    
                    # Manejar el caso de error en la predicción
                    if isinstance(price_result, dict):
                        if "fallback_price" in price_result:
                            trade_in_price = price_result["fallback_price"]
                        else:
                            continue
                    else:
                        trade_in_price = price_result
                    
                    # Aplicar margen según marca y grado
                    brand_key = brand.lower()
                    if brand_key not in markup_by_brand:
                        brand_key = "default"
                        
                    # Asegurar que usamos un grado válido para el lookup
                    grade_key = grade if grade in markup_by_brand[brand_key] else "C"
                    
                    # Obtener el margen de markup y calcular el precio final
                    markup_factor = markup_by_brand[brand_key][grade_key]
                    final_price = trade_in_price * (1 + markup_factor)
                    
                    # Si está dentro del presupuesto, añadir a candidatos
                    if final_price <= budget:
                        candidates.append({
                            "brand": brand,
                            "model": model,
                            "storage": storage,
                            "has_5g": has_5g,
                            "release_date": release_date,
                            "grade": grade,
                            "trade_in_price": trade_in_price,
                            "markup_factor": markup_factor,
                            "estimated_price": round(final_price, 2)  # Precio de venta estimado
                        })
        
        # Ordenar los candidatos por precio descendente (maximizar el presupuesto)
        candidates.sort(key=lambda x: x["estimated_price"], reverse=True)
        
        # Limitar a los 5 mejores resultados
        top_candidates = candidates[:5]
        
        # Convertir a DeviceInfo
        for candidate in top_candidates:
            device = DeviceInfo(
                brand=candidate["brand"],
                model=candidate["model"],
                storage=candidate["storage"],
                has_5g=candidate["has_5g"],
                release_date=candidate["release_date"],
                grade=candidate["grade"],
                estimated_price=candidate["estimated_price"]
            )
            recommended_devices.append(device)
        
        # Si no hay recomendaciones, proporcionar un fallback
        if not recommended_devices:
            return {
                "error": "no_recommendations_within_budget",
                "message": f"No encontramos dispositivos que cumplan con tus criterios dentro del presupuesto de {budget}€.",
                "fallback_recommendation": get_fallback_recommendation(budget, min_storage, grade_preference)
            }
            
        return recommended_devices
        
    except Exception as e:
        print(f"Error recommending devices: {e}")
        return {
            "error": "recommendation_error",
            "message": f"Hubo un error al buscar recomendaciones: {str(e)}.",
            "fallback_recommendation": get_fallback_recommendation(budget, min_storage, grade_preference)
        }

def get_fallback_recommendation(budget: float, min_storage: Optional[int] = None, grade_preference: Optional[str] = None) -> List[DeviceInfo]:
    """Genera recomendaciones genéricas cuando el algoritmo principal falla."""
    print("Using fallback recommendations")
    
    recommendations = []
    
    # Definir segmentos de presupuesto
    budget_segments = [
        (0, 200, ["Xiaomi Redmi 10C", "Galaxy A12", "Xiaomi Redmi Note 9"]),
        (200, 400, ["Galaxy A22 5G", "Xiaomi Redmi Note 11", "Galaxy A13 5G"]),
        (400, 700, ["iPhone 11", "Galaxy S20 FE 5G", "Xiaomi 11T"]),
        (700, 1000, ["iPhone 13", "Galaxy S21 5G", "Xiaomi 11T Pro"]),
        (1000, float('inf'), ["iPhone 14 Pro", "Galaxy S23 Ultra", "Xiaomi 13 Pro 5G"])
    ]
    
    # Encontrar segmento adecuado
    for low, high, models in budget_segments:
        if low <= budget < high:
            for model_name in models:
                parts = model_name.split(" ", 1)
                if len(parts) < 2:
                    continue
                    
                brand = parts[0]
                model = parts[1]
                has_5g = "5G" in model_name
                
                # Elegir almacenamiento según presupuesto
                storage_options = ["64GB", "128GB", "256GB"]
                if min_storage:
                    storage_options = [s for s in storage_options if int(s.replace("GB", "")) >= min_storage]
                
                if not storage_options:
                    storage_options = ["64GB"]
                    
                storage = random.choice(storage_options)
                
                # Usar grado preferido o C por defecto
                grade = grade_preference or "C"
                
                # Generar un precio razonable dentro del presupuesto
                price = random.uniform(low + (high - low) * 0.2, min(budget, high - 10))
                
                recommendations.append(DeviceInfo(
                    brand=brand,
                    model=model,
                    storage=storage,
                    has_5g=has_5g,
                    release_date=date(2022, 1, 1),  # Fecha aproximada
                    grade=grade,
                    estimated_price=round(price, 2)
                ))
            
            break
    
    return recommendations

def get_today_date() -> date:
    """Obtiene la fecha actual."""
    return date.today()

def get_release_date(brand: str, model: str, has_5g: bool = False) -> Optional[date]:
    """Gets the release date for a device model.
    
    Args:
        brand: The device brand
        model: The device model name
        has_5g: Whether the device has 5G capability if not specified in model
    
    Returns:
        The release date if found in CSV or hardcoded data, or a default date
    """
    import pandas as pd
    import os
    from datetime import datetime
    
    print(f"Getting release date for {brand} {model} (5G: {has_5g})")
    
    # Intentar cargar las fechas desde el CSV primero
    try:
        csv_path = os.path.join(DATA_DIR, "Fecha_Lanzamiento.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, sep=";")
            
            # Preparar el modelo para búsqueda
            if has_5g and "5G" not in model:
                model_with_5g = f"{model} 5G"
            else:
                model_with_5g = None
            
            # En el CSV, el formato es: "Marca Modelo"
            full_name = f"{brand} {model}"
            
            # Intentar encontrar coincidencias directas
            for search_term in [full_name, model_with_5g, f"{brand} {model_with_5g}"]:
                if not search_term:
                    continue
                
                matches = df[df['Modelo'].str.lower() == search_term.lower()]
                if not matches.empty:
                    date_str = matches.iloc[0]['Fecha de Lanzamiento']
                    return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
            
            # Búsqueda parcial si no hay coincidencias exactas
            for idx, row in df.iterrows():
                db_model = row['Modelo'].lower()
                if (model.lower() in db_model) or (full_name.lower() in db_model):
                    date_str = row['Fecha de Lanzamiento']
                    return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
                
                # Intentar con versión 5G si aplica
                if model_with_5g and model_with_5g.lower() in db_model:
                    date_str = row['Fecha de Lanzamiento']
                    return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
    
    except Exception as e:
        print(f"Error loading release dates from CSV: {e}")
    
    # Si no se encuentra en CSV o hay error, usar el método anterior con datos hardcodeados
    release_dates = {
        # Apple
        ("Apple", "iPhone 15"): date(2023, 9, 22),
        ("Apple", "iPhone 14"): date(2022, 9, 16),
        ("Apple", "iPhone 13"): date(2021, 9, 24),
        ("Apple", "iPhone 12"): date(2020, 10, 23),
        ("Apple", "iPhone 11"): date(2019, 9, 20),
        ("Apple", "iPhone XS"): date(2018, 9, 21),
        ("Apple", "iPhone X"): date(2017, 11, 3),
        ("Apple", "iPhone 8"): date(2017, 9, 22),
        ("Apple", "iPhone 7"): date(2016, 9, 16),
        
        # Samsung
        ("Samsung", "Galaxy S24"): date(2024, 1, 31),
        ("Samsung", "Galaxy S23"): date(2023, 2, 17),
        ("Samsung", "Galaxy S22"): date(2022, 2, 25),
        ("Samsung", "Galaxy S21"): date(2021, 1, 29),
        ("Samsung", "Galaxy S20"): date(2020, 3, 6),
        ("Samsung", "Galaxy A53"): date(2022, 3, 25),
        ("Samsung", "Galaxy A13"): date(2022, 3, 23),
        ("Samsung", "Galaxy A12"): date(2021, 1, 7),
        
        # Xiaomi
        ("Xiaomi", "13 Pro"): date(2023, 2, 26),
        ("Xiaomi", "12 Pro"): date(2022, 3, 15),
        ("Xiaomi", "11T Pro"): date(2021, 9, 23),
        ("Xiaomi", "Redmi Note 12"): date(2022, 10, 27),
        ("Xiaomi", "Redmi Note 11"): date(2022, 1, 26),
        ("Xiaomi", "Redmi Note 10"): date(2021, 3, 16),
        ("Xiaomi", "Redmi 10C"): date(2022, 3, 29),
    }
    
    # Intentar encontrar coincidencia exacta en datos hardcodeados
    key = (brand, model)
    if key in release_dates:
        return release_dates[key]
    
    # Intentar buscar coincidencia parcial
    for (b, m), date_value in release_dates.items():
        if b.lower() == brand.lower() and m in model:
            return date_value
    
    # Fecha por defecto para modelos desconocidos: 2 años atrás
    today = date.today()
    default_date = date(today.year - 2, today.month, today.day)
    return default_date


def generate_graphic_dict(
        brand: str,
        model: str,
        storage: str,
        has_5g: bool,
        release_date: Union[str, date],
        grade: str,
        date_range: list) -> dict:
    """Generates a dictionary of date-price pairs for a graphic based on device info and grade."""
    print(
        f"Generating graphic for {brand} {model} ({storage}, 5G: {has_5g}, grade: {grade})")

    graphic_data = {}
    for date in date_range:
        price = predict_price(brand, model, storage,
                              has_5g, release_date, grade, date)
        graphic_data[date] = price

    tool_result = {
        "graph_data": graphic_data,
    }

    return tool_result
