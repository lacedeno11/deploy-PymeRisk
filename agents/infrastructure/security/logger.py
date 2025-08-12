# security/logger.py

import logging
import json
import hashlib
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    Formateador personalizado para convertir los registros en una cadena JSON.
    """
    def format(self, record):
        # Creamos un diccionario base con la información estándar del log
        log_object = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # --- Mecanismo de Integridad (Hashing) ---
        # Convertimos el objeto de log a una cadena de texto ordenada para asegurar un hash consistente
        log_string = json.dumps(log_object, sort_keys=True)
        # Calculamos el hash SHA-256 del registro
        log_hash = hashlib.sha256(log_string.encode()).hexdigest()
        
        # Añadimos el hash al objeto de log final
        log_object["integrity_hash"] = log_hash

        return json.dumps(log_object)

def setup_logger():
    """
    Configura y devuelve una instancia de nuestro logger de auditoría.
    """
    # Creamos un logger con un nombre específico
    logger = logging.getLogger("AuditLogger")
    logger.setLevel(logging.INFO) # Nivel mínimo para registrar: INFO, WARNING, ERROR, CRITICAL

    # Evitamos que se añadan múltiples manejadores si la función se llama varias veces
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Creamos un "manejador" que sabe cómo escribir a un archivo
    file_handler = logging.FileHandler("audit.log", mode='a', encoding='utf-8')

    # 2. Creamos una instancia de nuestro formateador JSON y se la asignamos al manejador
    formatter = JsonFormatter()
    file_handler.setFormatter(formatter)

    # 3. Añadimos el manejador configurado a nuestro logger
    logger.addHandler(file_handler)

    return logger