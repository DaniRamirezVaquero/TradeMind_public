from pathlib import Path

# Marcas soportadas
SUPPORTED_BRANDS = {
    "apple": "modelo_apple.bin",
    "samsung": "modelo_samsung.bin",
    "xiaomi": "modelo_xiaomi.bin",
    "google": "modelo_google.bin",
    "honor": "modelo_honor.bin",
    "huawei": "modelo_huawei.bin",
    "motorola": "modelo_motorola.bin",
    "oneplus": "modelo_oneplus.bin",
    "oppo": "modelo_oppo.bin"
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