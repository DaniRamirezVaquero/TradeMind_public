from pathlib import Path

# Marcas soportadas
SUPPORTED_BRANDS = {
    "apple": "modelo_apple.json",
    "samsung": "modelo_samsung.json",
    "xiaomi": "modelo_xiaomi.json",
    "google": "modelo_google.json",
    "honor": "modelo_honor.json",
    "huawei": "modelo_huawei.json",
    "motorola": "modelo_motorola.json",
    "oneplus": "modelo_oneplus.json",
    "oppo": "modelo_oppo.json"
}

# Mapeo de grados
GRADE_MAPPING = {
    'B': 4,
    'C': 3,
    'D': 2,
    'E': 1
}

# Paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"