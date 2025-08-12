"""
Servicio de ingestión de PDFs financieros
- Extrae texto y tablas de PDFs de la Superintendencia de Compañías
- Devuelve un JSON normalizado y un helper para construir texto consolidado

Requisitos: pdfplumber (ya incluido en requirements.txt)
"""

from __future__ import annotations

import os
from typing import List, Dict, Any
import pdfplumber
import logging

# Configurar logger global
logger = logging.getLogger("pdf_ingestion_service")
logger.setLevel(logging.WARNING)


async def parse_financial_pdfs(pdf_paths: List[str]) -> Dict[str, Any]:
    """
    Extrae texto y tablas de una lista de PDFs y devuelve un JSON normalizado.

    Estructura de salida:
    {
        "sources": [{"file": str, "status": "parsed|no_text_layer|error_opening_pdf:...", "pages": int}],
        "statements": [
            {
                "filename": str,
                "text": str,
                "tables": [
                    {"page": int, "rows": List[List[str]]}
                ]
            }
        ],
        "needs_ocr": [str],
        "summary": {"detected_documents": int, "pending_ocr": int, "notes": str}
    }
    """
    result: Dict[str, Any] = {
        "sources": [],
        "statements": [],
        "needs_ocr": [],
        "summary": {},
    }

    for path in pdf_paths:
        doc = {"filename": os.path.basename(path), "text": "", "tables": []}
        has_text = False
        page_count = 0
        try:
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
                for idx, page in enumerate(pdf.pages, start=1):
                    try:
                        # Texto
                        txt = page.extract_text() or ""
                        if txt.strip():
                            has_text = True
                            # Normalizar líneas y agregar separadores de página
                            doc["text"] += f"\n\n==== PÁGINA {idx} ====\n" + txt.strip() + "\n"
                        # Tablas (intento múltiple)
                        tables = page.extract_tables() or []
                        for t in tables:
                            if t and isinstance(t, list) and len(t) > 0:
                                doc["tables"].append({"page": idx, "rows": t})
                    except Exception as page_error:
                        logger.warning(f"Error procesando página {idx} del PDF {path}: {page_error}")
        except Exception as e:
            result["sources"].append({"file": path, "status": f"error_opening_pdf: {e}", "pages": 0})
            continue

        result["sources"].append({"file": path, "status": "parsed" if has_text else "no_text_layer", "pages": page_count})
        if has_text:
            result["statements"].append(doc)
        else:
            result["needs_ocr"].append(path)

    result["summary"] = {
        "detected_documents": len(result["statements"]),
        "pending_ocr": len(result["needs_ocr"]),
        "notes": "Parser básico. Para PDFs escaneados o tablas complejas, integrar Azure Document Intelligence.",
    }
    return result


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _table_to_markdown(rows: List[List[str]], max_rows: int = 15, max_cols: int = 8) -> str:
    """
    Convierte una tabla (lista de filas) a una representación tipo markdown simple.
    Limita filas/columnas para no exceder tokens.
    """
    if not rows:
        return ""
    # Limitar columnas por fila
    limited = [list(map(lambda c: (c or "").strip(), r[:max_cols])) for r in rows[:max_rows]]
    # Armar markdown simple
    lines = []
    for r in limited:
        lines.append(" | ".join(r))
    if len(rows) > max_rows:
        lines.append(f"... ({len(rows) - max_rows} filas adicionales)")
    return "\n".join(lines)


def build_financial_text_from_parsed(parsed: Dict[str, Any], max_rows_per_table: int = 12) -> str:
    """
    Construye un texto consolidado amigable para LLM a partir del JSON parseado.
    Incluye extractos de texto y un resumen de tablas.
    """
    parts: List[str] = []
    for st in parsed.get("statements", []):
        parts.append(f"\n\n===== DOCUMENTO: {st.get('filename','')} =====\n")
        # Agregar texto con límite para no explotar tokens
        parts.append(_truncate_text(st.get("text", "").strip(), 10000))
        # Resumen de tablas
        tables = st.get("tables", [])
        if tables:
            parts.append("\n-- Resumen de Tablas --\n")
            for i, t in enumerate(tables, start=1):
                parts.append(f"Tabla {i} (página {t.get('page', '?')}):\n")
                parts.append(_table_to_markdown(t.get("rows", []), max_rows=max_rows_per_table))
    # Notas de OCR
    needs_ocr = parsed.get("needs_ocr", [])
    if needs_ocr:
        parts.append(f"\n\n[Nota] {len(needs_ocr)} documento(s) requieren OCR y no se incluyeron.\n")
    return "\n".join(parts).strip()
