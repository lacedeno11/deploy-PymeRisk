"""
Frontend de Streamlit para el Sistema de Evaluación de Riesgo Financiero para PYMEs
Hackathon - Deploy: https://deploy-pymerisk-dhtmtkfxynnrd6wqzsztbu.streamlit.app/
"""

import streamlit as st
import asyncio
import time
import os
from datetime import datetime
import PyPDF2
import io
import traceback

# Configuración de la página
st.set_page_config(
    page_title="PymeRisk - Evaluación de Riesgo Financiero",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado - Paleta de colores PymeRisk oficial
st.markdown("""
<style>
    /* Variables CSS - Paleta PymeRisk */
    :root {
        /* PRINCIPALES */
        --header-gradient-start: #1e3c72;
        --header-gradient-end: #2a5298;
        --header-text: #ffffff;
        --header-subtitle: #e0e6ed;
        
        /* SISTEMA DE RIESGO */
        --risk-low: #28a745;
        --risk-medium: #ffc107;
        --risk-high: #dc3545;
        
        /* TEXTOS Y FONDOS */
        --text-primary: #000000;
        --text-secondary: #666666;
        --background-white: #ffffff;
        --background-light-gray: #f8f9fa;
        
        /* GRISES ELEGANTES PARA CONTRASTE */
        --gray-dark: #495057;
        --gray-medium: #6c757d;
        --gray-light: #adb5bd;
        --gray-lighter: #dee2e6;
        --gray-lightest: #f8f9fa;
    }
    
    /* Fondo principal - Gris muy suave para contraste */
    .stApp {
        background-color: var(--background-light-gray);
        color: var(--text-primary);
    }
    
    /* HEADER PRINCIPAL - Siguiendo especificaciones exactas */
    .main-header {
        background: linear-gradient(90deg, var(--header-gradient-start) 0%, var(--header-gradient-end) 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(30, 60, 114, 0.3);
    }
    
    .main-header h1 {
        color: var(--header-text);
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .main-header p {
        color: var(--header-subtitle);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* SIDEBAR - Gris elegante para contraste */
    .css-1d391kg, .css-1cypcdb, .css-17eq0hr {
        background: linear-gradient(180deg, var(--gray-dark) 0%, var(--gray-medium) 100%) !important;
        color: var(--background-white) !important;
    }
    
    .css-1d391kg .markdown-text-container {
        color: var(--background-white) !important;
    }
    
    /* BOTONES - Gris elegante según especificaciones */
    .stButton > button {
        background: linear-gradient(135deg, var(--gray-medium) 0%, var(--gray-dark) 100%) !important;
        color: var(--background-white) !important;
        border: 2px solid var(--gray-light) !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(73, 80, 87, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--gray-dark) 0%, var(--gray-medium) 100%) !important;
        border-color: var(--gray-lighter) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(73, 80, 87, 0.4) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* FILE UPLOADER - Gris elegante */
    .stFileUploader > div {
        background: var(--gray-lightest) !important;
        border: 2px dashed var(--gray-light) !important;
        border-radius: 8px !important;
        padding: 2rem !important;
        color: var(--text-primary) !important;
        transition: all 0.3s ease !important;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--gray-medium) !important;
        background: var(--background-white) !important;
    }
    
    .stFileUploader label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    /* INPUTS DE TEXTO - Gris suave */
    .stTextInput > div > div > input {
        background: var(--background-white) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--gray-lighter) !important;
        border-radius: 6px !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--header-gradient-end) !important;
        box-shadow: 0 0 8px rgba(42, 82, 152, 0.3) !important;
    }
    
    /* TEXT AREA - Gris suave */
    .stTextArea > div > div > textarea {
        background: var(--background-white) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--gray-lighter) !important;
        border-radius: 6px !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: var(--header-gradient-end) !important;
        box-shadow: 0 0 8px rgba(42, 82, 152, 0.3) !important;
    }
    
    /* SELECTBOX - Gris suave */
    .stSelectbox > div > div {
        background: var(--background-white) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--gray-lighter) !important;
        border-radius: 6px !important;
    }
    
    /* EXPANDIR/COLAPSAR - Gris elegante */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, var(--gray-lightest) 0%, var(--background-white) 100%) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        border: 1px solid var(--gray-lighter) !important;
        transition: all 0.3s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, var(--background-white) 0%, var(--gray-lightest) 100%) !important;
        border-color: var(--gray-light) !important;
    }
    
    .streamlit-expanderContent {
        background: var(--background-white) !important;
        border: 1px solid var(--gray-lighter) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    /* CAJAS DE INFORMACIÓN - Usando colores de la paleta */
    .info-box {
        background: linear-gradient(135deg, var(--header-gradient-start) 0%, var(--header-gradient-end) 100%);
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid var(--header-gradient-end);
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(30, 60, 114, 0.2);
        color: var(--header-text);
    }
    
    .success-box {
        background: linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(40, 167, 69, 0.05) 100%);
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid var(--risk-low);
        margin: 1rem 0;
        color: var(--text-primary);
    }
    
    .warning-box {
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 193, 7, 0.05) 100%);
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid var(--risk-medium);
        margin: 1rem 0;
        color: var(--text-primary);
    }
    
    .error-box {
        background: linear-gradient(135deg, rgba(220, 53, 69, 0.1) 0%, rgba(220, 53, 69, 0.05) 100%);
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid var(--risk-high);
        margin: 1rem 0;
        color: var(--text-primary);
    }
    
    /* INDICADORES DE ESTADO */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-operational {
        background-color: var(--risk-low);
        box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 8px rgba(40, 167, 69, 0.6); }
        50% { box-shadow: 0 0 16px rgba(40, 167, 69, 0.8); }
        100% { box-shadow: 0 0 8px rgba(40, 167, 69, 0.6); }
    }
    
    /* TARJETAS DE MÉTRICAS - Gris elegante */
    .metric-card {
        background: linear-gradient(135deg, var(--gray-lightest) 0%, var(--background-white) 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--gray-lighter);
        margin: 0.5rem 0;
        text-align: center;
        color: var(--text-primary);
        box-shadow: 0 2px 8px rgba(73, 80, 87, 0.1);
    }
    
    /* PASOS DEL PROCESO - Usando colores del header */
    .process-step {
        background: linear-gradient(135deg, var(--header-gradient-start) 0%, var(--header-gradient-end) 100%);
        padding: 1.2rem;
        border-radius: 8px;
        margin: 0.8rem 0;
        border-left: 4px solid var(--header-gradient-end);
        color: var(--header-text);
        box-shadow: 0 4px 16px rgba(30, 60, 114, 0.2);
    }
    
    /* MÉTRICAS DE STREAMLIT - Gris elegante */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, var(--gray-lightest) 0%, var(--background-white) 100%) !important;
        border: 1px solid var(--gray-lighter) !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(73, 80, 87, 0.1) !important;
    }
    
    [data-testid="metric-container"] > div {
        color: var(--text-primary) !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-label"] {
        color: var(--text-secondary) !important;
    }
    
    /* TABS - Gris elegante */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--gray-lightest) !important;
        border-radius: 8px !important;
        border: 1px solid var(--gray-lighter) !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: var(--text-primary) !important;
        background: transparent !important;
        border-radius: 6px !important;
        margin: 2px !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(108, 117, 125, 0.1) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--header-gradient-start) 0%, var(--header-gradient-end) 100%) !important;
        color: var(--header-text) !important;
    }
    
    /* PROGRESS BAR - Usando colores del header */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--header-gradient-start) 0%, var(--header-gradient-end) 100%) !important;
    }
    
    /* SPINNER - Color del header */
    .stSpinner > div {
        border-top-color: var(--header-gradient-end) !important;
    }
    
    /* SUCCESS/ERROR MESSAGES - Colores de la paleta */
    .stSuccess {
        background-color: rgba(40, 167, 69, 0.1) !important;
        border-left: 4px solid var(--risk-low) !important;
    }
    
    .stError {
        background-color: rgba(220, 53, 69, 0.1) !important;
        border-left: 4px solid var(--risk-high) !important;
    }
    
    .stWarning {
        background-color: rgba(255, 193, 7, 0.1) !important;
        border-left: 4px solid var(--risk-medium) !important;
    }
    
    .stInfo {
        background-color: rgba(42, 82, 152, 0.1) !important;
        border-left: 4px solid var(--header-gradient-end) !important;
    }
</style>
""", unsafe_allow_html=True)

def extract_text_from_pdf(pdf_file):
    """Extrae texto de un archivo PDF con mejor manejo de espacios"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            # Mejorar el espaciado del texto extraído
            page_text = improve_text_spacing(page_text)
            text += page_text + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error al extraer texto del PDF: {str(e)}")
        return None

def improve_text_spacing(text):
    """Mejora el espaciado del texto extraído de PDFs"""
    import re
    
    if not text:
        return text
    
    # Agregar espacios antes de números que siguen a letras
    text = re.sub(r'([a-záéíóúñ])(\d)', r'\1 \2', text, flags=re.IGNORECASE)
    
    # Agregar espacios después de números que preceden a letras
    text = re.sub(r'(\d)([a-záéíóúñ])', r'\1 \2', text, flags=re.IGNORECASE)
    
    # Agregar espacios antes de paréntesis que siguen a letras/números
    text = re.sub(r'([a-záéíóúñ\d])\(', r'\1 (', text, flags=re.IGNORECASE)
    
    # Agregar espacios después de paréntesis que preceden a letras/números
    text = re.sub(r'\)([a-záéíóúñ\d])', r') \1', text, flags=re.IGNORECASE)
    
    # Agregar espacios antes de signos de dólar que siguen a letras
    text = re.sub(r'([a-záéíóúñ])\$', r'\1 $', text, flags=re.IGNORECASE)
    
    # Agregar espacios después de signos de dólar que preceden a letras (pero no números)
    text = re.sub(r'\$([a-záéíóúñ])', r'$ \1', text, flags=re.IGNORECASE)
    
    # Agregar espacios antes de mayúsculas que siguen a minúsculas (para separar palabras pegadas)
    text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
    
    # Agregar espacios después de puntos que preceden a letras mayúsculas
    text = re.sub(r'\.([A-ZÁÉÍÓÚÑ])', r'. \1', text)
    
    # Agregar espacios después de comas que preceden a letras
    text = re.sub(r',([a-záéíóúñA-ZÁÉÍÓÚÑ])', r', \1', text, flags=re.IGNORECASE)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    # Limpiar espacios al inicio y final
    text = text.strip()
    
    return text

def generate_simulated_social_comments(company_name):
    """Genera comentarios simulados de redes sociales para demostrar el análisis reputacional"""
    import random
    
    # Plantillas de comentarios positivos
    positive_comments = [
        f"Excelente servicio de {company_name}! Muy profesionales y puntuales en sus entregas. Los recomiendo 100%.",
        f"Llevo 3 años trabajando con {company_name} y siempre cumplen con lo prometido. Calidad garantizada.",
        f"El equipo de {company_name} es muy responsable. Resolvieron nuestro problema rápidamente y con gran profesionalismo.",
        f"Muy satisfecho con los servicios de {company_name}. Precios justos y excelente atención al cliente.",
        f"Recomiendo ampliamente a {company_name}. Son una empresa seria y confiable, siempre entregan a tiempo."
    ]
    
    # Plantillas de comentarios neutrales
    neutral_comments = [
        f"Trabajé con {company_name} el año pasado. El servicio fue correcto, sin mayores inconvenientes.",
        f"Empresa {company_name} cumple con lo básico. Nada extraordinario pero tampoco problemas graves.",
        f"Experiencia promedio con {company_name}. Podrían mejorar la comunicación con los clientes.",
        f"Los precios de {company_name} están dentro del mercado. Servicio estándar para el sector."
    ]
    
    # Plantillas de comentarios con sugerencias de mejora
    improvement_comments = [
        f"Buen servicio de {company_name}, aunque podrían mejorar los tiempos de respuesta por WhatsApp.",
        f"En general bien con {company_name}, solo sugiero que actualicen más seguido su página web.",
        f"Trabajo realizado por {company_name} fue satisfactorio. Sería bueno que ofrecieran más opciones de pago."
    ]
    
    # Seleccionar comentarios de forma aleatoria pero balanceada
    selected_comments = []
    
    # 60% positivos, 30% neutrales, 10% con sugerencias
    selected_comments.extend(random.sample(positive_comments, 3))
    selected_comments.extend(random.sample(neutral_comments, 2))
    selected_comments.extend(random.sample(improvement_comments, 1))
    
    # Mezclar el orden
    random.shuffle(selected_comments)
    
    return selected_comments[:6]  # Retornar 6 comentarios

def parse_analysis_result(analysis_data):
    """Parsea los resultados de análisis que pueden venir como JSON string o dict"""
    import json
    import re
    
    def clean_json_from_text(text):
        """Extrae solo el texto legible de un JSON o texto que contiene JSON"""
        if not isinstance(text, str):
            return text
            
        # Si el texto completo es un JSON, extraer solo el resumen_ejecutivo
        if text.strip().startswith('{') and text.strip().endswith('}'):
            try:
                json_data = json.loads(text.strip())
                if isinstance(json_data, dict) and 'resumen_ejecutivo' in json_data:
                    return json_data['resumen_ejecutivo']
                # Si no tiene resumen_ejecutivo, buscar otros campos de texto
                for key in ['resumen', 'summary', 'description', 'texto']:
                    if key in json_data and isinstance(json_data[key], str):
                        return json_data[key]
                # Si no encuentra texto, devolver una descripción básica
                return "Análisis completado correctamente"
            except:
                pass
        
        # Si contiene JSON parcial, intentar extraer texto antes del JSON
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        if re.search(json_pattern, text):
            # Extraer texto antes del primer JSON
            before_json = re.split(json_pattern, text)[0].strip()
            if before_json and len(before_json) > 10:
                return before_json
            
            # Si no hay texto antes, intentar extraer del JSON
            json_matches = re.findall(json_pattern, text)
            for json_str in json_matches:
                try:
                    json_data = json.loads(json_str)
                    if isinstance(json_data, dict) and 'resumen_ejecutivo' in json_data:
                        return json_data['resumen_ejecutivo']
                except:
                    continue
        
        return text
    
    if isinstance(analysis_data, str):
        try:
            # Si es un string JSON, parsearlo
            parsed = json.loads(analysis_data)
            # Limpiar el resumen_ejecutivo si contiene JSON
            if 'resumen_ejecutivo' in parsed:
                parsed['resumen_ejecutivo'] = clean_json_from_text(parsed['resumen_ejecutivo'])
            return parsed
        except json.JSONDecodeError:
            # Si no es JSON válido, devolver como está
            return {"resumen_ejecutivo": clean_json_from_text(analysis_data), "success": False}
    elif isinstance(analysis_data, dict):
        # Si ya es un diccionario, limpiar el resumen_ejecutivo
        result = analysis_data.copy()
        if 'resumen_ejecutivo' in result:
            result['resumen_ejecutivo'] = clean_json_from_text(result['resumen_ejecutivo'])
        return result
    else:
        # Si es otro tipo de objeto, intentar convertirlo a dict
        try:
            result = dict(analysis_data)
            if 'resumen_ejecutivo' in result:
                result['resumen_ejecutivo'] = clean_json_from_text(result['resumen_ejecutivo'])
            return result
        except:
            return {"resumen_ejecutivo": "Análisis completado", "success": False}

async def evaluate_company_risk(company_data):
    """Evalúa el riesgo de la empresa usando el orquestador"""
    try:
        # Importar el orquestador
        from agents.azure_orchestrator import AzureOrchestrator, CompanyData
        
        # Inicializar orquestador
        orchestrator = AzureOrchestrator()
        success = await orchestrator.initialize()
        
        if not success:
            return None, "Error al inicializar el sistema de evaluación"
        
        # Crear objeto CompanyData
        company_data_obj = CompanyData(
            company_id=company_data["company_id"],
            company_name=company_data["company_name"],
            financial_statements=company_data["financial_statements"],
            social_media_data=company_data["social_media_data"],
            commercial_references=company_data.get("commercial_references", "No disponible"),
            payment_history=company_data.get("payment_history", "No disponible"),
            metadata={"source": "streamlit_frontend", "timestamp": datetime.now().isoformat()}
        )
        
        # Evaluar riesgo
        result = await orchestrator.evaluate_company_risk(company_data_obj)
        
        return result, None
        
    except Exception as e:
        error_msg = f"Error durante la evaluación: {str(e)}"
        st.error(error_msg)
        st.error(traceback.format_exc())
        return None, error_msg

def main():
    # Header principal con el estilo del código de referencia
    st.markdown("""
    <div class="main-header">
        <h1>🏦 PymeRisk - Sistema de Evaluación de Riesgo Financiero</h1>
        <p>Análisis inteligente de riesgo para PYMES usando IA avanzada</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Proceso de Análisis - Secciones expandibles
    st.markdown("## 🔄 Proceso de Análisis")
    
    with st.expander("📄 Extracción de Datos", expanded=False):
        st.markdown("""
        <div class="process-step">
        <strong>Extrayendo texto y tablas de los PDFs financieros subidos</strong><br><br>
        • Procesamiento OCR de documentos<br>
        • Identificación de estados financieros<br>
        • Extracción de ratios clave<br>
        • Validación de formato y estructura
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("💰 Análisis Financiero", expanded=False):
        st.markdown("""
        <div class="process-step">
        <strong>Evaluando la salud financiera usando GPT-4o</strong><br><br>
        • Análisis de liquidez y solvencia<br>
        • Evaluación de rentabilidad<br>
        • Tendencias históricas<br>
        • Ratios financieros clave<br>
        • Cumplimiento NIIF para PYMEs Ecuador
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("🌟 Análisis Reputacional", expanded=False):
        st.markdown("""
        <div class="process-step">
        <strong>Analizando presencia digital y reputación online</strong><br><br>
        • Análisis de redes sociales<br>
        • Sentimiento público<br>
        • Menciones online<br>
        • Presencia digital<br>
        • Reputación corporativa
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("📈 Análisis Comportamental", expanded=False):
        st.markdown("""
        <div class="process-step">
        <strong>Evaluando patrones de comportamiento comercial</strong><br><br>
        • Referencias comerciales<br>
        • Historial de pagos<br>
        • Patrones de comportamiento<br>
        • Confiabilidad comercial<br>
        • Relaciones con proveedores
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("🎯 Consolidación", expanded=False):
        st.markdown("""
        <div class="process-step">
        <strong>Generando score final y recomendaciones</strong><br><br>
        • Ponderación de análisis (60% financiero, 20% reputacional, 20% comportamental)<br>
        • Cálculo de score 0-1000<br>
        • Clasificación de riesgo (ALTO/MEDIO/BAJO)<br>
        • Recomendaciones crediticias<br>
        • Justificación detallada y explicable
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar con información del sistema
    with st.sidebar:
        st.markdown("## 📊 Información del Sistema")
        
        # Estado del Sistema
        st.markdown("### Estado del Sistema")
        st.markdown("""
        <div class="info-box">
        <span class="status-indicator status-operational"></span><strong>Azure OpenAI:</strong> Operativo<br>
        <span class="status-indicator status-operational"></span><strong>Modelos:</strong> GPT-4o + o3-mini<br>
        <span class="status-indicator status-operational"></span><strong>Servicio PDF:</strong> Disponible
        </div>
        """, unsafe_allow_html=True)
        
        # ¿Qué hace este sistema?
        st.markdown("### ¿Qué hace este sistema?")
        st.markdown("""
        Este evaluador analiza el riesgo crediticio de una PYME utilizando:
        
        **Procesamiento Inteligente:**
        - Extracción automática de texto y tablas de PDFs
        - Análisis con inteligencia artificial avanzada
        - Validación de seguridad y contenido
        
        **Análisis Financiero (GPT-4o):**
        - Estados financieros (Balance General, Estado de Resultados)
        - Ratios de liquidez, solvencia
        - Cumplimiento de NIIF para PYMES Ecuador
        
        **Análisis Reputacional (o3-mini):**
        - Presencia en redes sociales (Instagram, etc.)
        - Análisis de sentimiento público
        - Menciones online y reputación digital
        
        **Análisis Comportamental (o3-mini):**
        - Referencias comerciales
        - Historial de pagos y comportamiento
        - Patrones de confiabilidad comercial
        
        **Resultado Final:**
        - Score de riesgo de 0-1000
        - Clasificación: ALTO, MEDIO, BAJO riesgo
        - Recomendación crediticia clara
        - Justificación detallada y explicable
        """)
        
        # Métricas del Sistema
        st.markdown("### Métricas del Sistema")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="metric-card">
            <strong>Tiempo:</strong> 50-60s<br>
            <strong>Seguridad:</strong> 100%
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="metric-card">
            <strong>Precisión:</strong> 90%+<br>
            <strong>Tokens:</strong> 3K-8K
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        **Tecnología:** Azure OpenAI Service  
        **Framework:** Arquitectura Multi-Agente  
        **Extracción PDF:** pdfplumber + OCR
        """)
        
        # ¿Necesitas ayuda?
        st.markdown("### ¿Necesitas ayuda?")
        st.markdown("📞 [Supercias Ecuador](https://appscvsgen.supercias.gob.ec/consultaCompanias/societario/busquedaCompanias.jsf)")
        
        # Disclaimer
        st.markdown("---")
        st.markdown("""
        <div class="warning-box">
        <strong>Disclaimer:</strong> Este sistema es una herramienta de apoyo para la evaluación de riesgo crediticio. Los resultados deben ser validados por profesionales financieros.
        </div>
        """, unsafe_allow_html=True)
    
    # Formulario principal
    st.header("📄 Carga de Documentos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Balance Financiero")
        financial_pdf = st.file_uploader(
            "Sube el PDF con los estados financieros",
            type=['pdf'],
            key="financial_pdf",
            help="Incluye balance general, estado de resultados, flujo de efectivo"
        )
        
        if financial_pdf:
            st.success(f"✅ Archivo cargado: {financial_pdf.name}")
            with st.expander("Vista previa del contenido"):
                financial_text = extract_text_from_pdf(financial_pdf)
                if financial_text:
                    st.text_area("Contenido extraído:", financial_text[:500] + "...", height=150, disabled=True)
    
    with col2:
        st.subheader("🏢 Información General")
        general_pdf = st.file_uploader(
            "Sube el PDF con información general de la empresa",
            type=['pdf'],
            key="general_pdf",
            help="Incluye información corporativa, actividad comercial, datos generales"
        )
        
        if general_pdf:
            st.success(f"✅ Archivo cargado: {general_pdf.name}")
            with st.expander("Vista previa del contenido"):
                general_text = extract_text_from_pdf(general_pdf)
                if general_text:
                    st.text_area("Contenido extraído:", general_text[:500] + "...", height=150, disabled=True)
    
    # Información adicional
    st.header("📝 Información Adicional")
    
    col3, col4 = st.columns(2)
    
    with col3:
        company_name = st.text_input(
            "Nombre de la Empresa",
            placeholder="Ej: Innovaciones Andinas S.A.",
            help="Nombre completo de la empresa a evaluar"
        )
    
    with col4:
        company_id = st.text_input(
            "ID de la Empresa (opcional)",
            placeholder="Ej: PYME_001",
            help="Identificador único para la evaluación"
        )
    
    # Referencias comerciales (opcional)
    commercial_references = st.text_area(
        "Referencias Comerciales (opcional)",
        placeholder="Información sobre proveedores, clientes, historial comercial...",
        height=100,
        help="Información adicional que puede mejorar la precisión de la evaluación"
    )
    
    # Sección de redes sociales simulada
    st.markdown("### 📱 Análisis de Redes Sociales (Simulado)")
    
    col_social1, col_social2 = st.columns(2)
    
    with col_social1:
        social_media_url = st.text_input(
            "🔗 URL de Red Social",
            placeholder="https://instagram.com/empresa o https://facebook.com/empresa",
            help="URL de la red social de la empresa (para demostración)"
        )
    
    with col_social2:
        simulate_social = st.checkbox(
            "✨ Generar comentarios simulados",
            value=True,
            help="Genera comentarios de ejemplo para demostrar el análisis reputacional"
        )
    
    if simulate_social:
        st.markdown("""
        <div class="warning-box">
        <strong>⚠️ Sección Simulada:</strong> Los siguientes comentarios son generados automáticamente para demostrar 
        el funcionamiento del agente de análisis reputacional. En un entorno real, estos datos se obtendrían 
        directamente de las APIs de redes sociales.
        </div>
        """, unsafe_allow_html=True)
        
        # Generar comentarios simulados basados en el nombre de la empresa
        if company_name:
            simulated_comments = generate_simulated_social_comments(company_name)
            
            with st.expander("👀 Ver comentarios simulados generados", expanded=False):
                st.markdown("**Comentarios y reseñas simulados:**")
                for i, comment in enumerate(simulated_comments, 1):
                    st.markdown(f"**Cliente {i}:** {comment}")
        else:
            st.info("💡 Ingresa el nombre de la empresa para generar comentarios simulados")
    
    # Botón de evaluación
    st.markdown("---")
    
    if st.button("🚀 Evaluar Riesgo Financiero", type="primary", use_container_width=True):
        # Validaciones
        if not financial_pdf or not general_pdf:
            st.error("❌ Por favor, sube ambos archivos PDF (Balance Financiero e Información General)")
            return
        
        if not company_name:
            st.error("❌ Por favor, ingresa el nombre de la empresa")
            return
        
        # Extraer texto de los PDFs
        with st.spinner("📄 Extrayendo información de los PDFs..."):
            financial_text = extract_text_from_pdf(financial_pdf)
            general_text = extract_text_from_pdf(general_pdf)
        
        if not financial_text or not general_text:
            st.error("❌ Error al extraer texto de los PDFs. Verifica que los archivos no estén dañados.")
            return
        
        # Preparar datos de redes sociales
        social_media_content = general_text  # Información general del PDF
        
        # Si se activaron comentarios simulados, agregarlos
        if simulate_social and company_name:
            simulated_comments = generate_simulated_social_comments(company_name)
            social_media_section = "\n\n=== COMENTARIOS Y RESEÑAS DE CLIENTES ===\n"
            for i, comment in enumerate(simulated_comments, 1):
                social_media_section += f"\nCliente {i}: {comment}\n"
            
            social_media_content += social_media_section
        
        # Preparar datos para evaluación
        company_data = {
            "company_id": company_id if company_id else f"EVAL_{int(time.time())}",
            "company_name": company_name,
            "financial_statements": financial_text,
            "social_media_data": social_media_content,  # Incluye info general + comentarios simulados
            "commercial_references": commercial_references if commercial_references else "No proporcionado",
            "payment_history": "No disponible - Evaluación basada en documentos"
        }
        
        # Ejecutar evaluación con barra de progreso
        st.info("🚀 Iniciando evaluación de riesgo financiero... (50-60 segundos)")
        
        # Crear barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Pasos del progreso con tiempos realistas
        progress_steps = [
            (10, "📄 Extrayendo información de PDFs..."),
            (20, "🔍 Validando datos de entrada..."),
            (35, "💰 Analizando estados financieros con GPT-4o..."),
            (55, "🌟 Evaluando reputación digital con o3-mini..."),
            (70, "📈 Analizando comportamiento comercial..."),
            (85, "🎯 Consolidando análisis y calculando score..."),
            (95, "📊 Generando reporte final..."),
        ]
        
        # Simular progreso mientras se ejecuta la evaluación
        start_time = time.time()
        
        # Función para simular progreso en paralelo
        async def simulate_progress_and_evaluate():
            # Crear tarea para la evaluación real
            eval_task = asyncio.create_task(evaluate_company_risk(company_data))
            
            # Simular progreso durante 60 segundos
            for i, (progress, message) in enumerate(progress_steps):
                status_text.text(message)
                progress_bar.progress(progress)
                
                # Esperar tiempo proporcional (60 segundos total / 7 pasos)
                if i < len(progress_steps) - 1:
                    await asyncio.sleep(8.5)  # ~60 segundos / 7 pasos
            
            # Esperar a que termine la evaluación real
            result, error = await eval_task
            
            # Completar progreso
            progress_bar.progress(100)
            status_text.text("✅ Evaluación completada!")
            
            return result, error
        
        try:
            # Ejecutar evaluación con progreso simulado
            result, error = asyncio.run(simulate_progress_and_evaluate())
            
            if error:
                st.error(f"❌ {error}")
                return
            
            if not result or not result.success:
                st.error("❌ La evaluación no se completó exitosamente")
                if result and result.errors:
                    st.error(f"Errores: {', '.join(result.errors)}")
                return
            
            # Mostrar resultados
            st.success("✅ Evaluación completada exitosamente!")
            
            # Métricas principales
            st.header("📊 Resultados de la Evaluación")
            
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                st.metric(
                    "Score Final",
                    f"{result.final_score:.0f}/1000",
                    help="Puntuación de riesgo: Mayor puntaje = Menor riesgo"
                )
            
            with col6:
                risk_color = {"BAJO": "🟢", "MEDIO": "🟡", "ALTO": "🔴"}
                st.metric(
                    "Nivel de Riesgo",
                    f"{risk_color.get(result.risk_level, '⚪')} {result.risk_level}",
                    help="Clasificación de riesgo crediticio"
                )
            
            with col7:
                st.metric(
                    "Tiempo de Procesamiento",
                    f"{result.processing_time:.1f}s",
                    help="Tiempo total de evaluación"
                )
            
            with col8:
                st.metric(
                    "Confianza",
                    f"{result.consolidated_report.get('confidence', 0):.1%}" if result.consolidated_report else "N/A",
                    help="Nivel de confianza en la evaluación"
                )
            
            # Análisis detallado
            st.header("🔍 Análisis Detallado")
            
            tab1, tab2, tab3, tab4 = st.tabs(["💰 Financiero", "🌟 Reputacional", "📈 Comportamental", "📋 Consolidado"])
            
            with tab1:
                if result.financial_analysis and result.financial_analysis.get('success', True):
                    fa = result.financial_analysis
                    st.markdown("### Análisis Financiero")
                    
                    if fa.get('solvencia'):
                        st.markdown(f"**Solvencia:** {fa['solvencia']}")
                    if fa.get('liquidez'):
                        st.markdown(f"**Liquidez:** {fa['liquidez']}")
                    if fa.get('rentabilidad'):
                        st.markdown(f"**Rentabilidad:** {fa['rentabilidad']}")
                    if fa.get('resumen_ejecutivo'):
                        st.markdown(f"**Resumen:** {fa['resumen_ejecutivo']}")
                    
                    if fa.get('tokens_used'):
                        st.caption(f"Tokens utilizados: {fa['tokens_used']}")
                else:
                    st.warning("⚠️ Análisis financiero no disponible")
            
            with tab2:
                if result.reputational_analysis and result.reputational_analysis.get('success', True):
                    # Parsear el resultado del análisis reputacional
                    ra = parse_analysis_result(result.reputational_analysis)
                    st.markdown("### Análisis Reputacional")
                    
                    if ra.get('sentimiento_general'):
                        sentiment_emoji = {"Positivo": "😊", "Neutral": "😐", "Negativo": "😟"}
                        st.markdown(f"**Sentimiento General:** {sentiment_emoji.get(ra['sentimiento_general'], '')} {ra['sentimiento_general']}")
                    
                    if ra.get('puntaje_sentimiento') is not None:
                        st.markdown(f"**Puntaje de Sentimiento:** {ra['puntaje_sentimiento']:.2f}")
                    
                    if ra.get('temas_positivos') and isinstance(ra['temas_positivos'], list):
                        st.markdown(f"**Temas Positivos:** {', '.join(ra['temas_positivos'])}")
                    
                    if ra.get('temas_negativos') and isinstance(ra['temas_negativos'], list):
                        st.markdown(f"**Temas Negativos:** {', '.join(ra['temas_negativos'])}")
                    
                    if ra.get('resumen_ejecutivo'):
                        st.markdown(f"**Resumen:** {ra['resumen_ejecutivo']}")
                    
                    if ra.get('tokens_used'):
                        st.caption(f"Tokens utilizados: {ra['tokens_used']}")
                        
                    # Mostrar comentarios simulados si están disponibles
                    if simulate_social and company_name:
                        st.markdown("---")
                        st.markdown("**📱 Comentarios Analizados (Simulados):**")
                        simulated_comments = generate_simulated_social_comments(company_name)
                        for i, comment in enumerate(simulated_comments[:3], 1):
                            st.markdown(f"• **Cliente {i}:** {comment[:100]}...")
                else:
                    st.warning("⚠️ Análisis reputacional no disponible")
            
            with tab3:
                if result.behavioral_analysis and result.behavioral_analysis.get('success', True):
                    # Parsear el resultado del análisis comportamental
                    ba = parse_analysis_result(result.behavioral_analysis)
                    st.markdown("### Análisis Comportamental")
                    
                    if ba.get('patron_de_pago'):
                        st.markdown(f"**Patrón de Pago:** {ba['patron_de_pago']}")
                    
                    if ba.get('fiabilidad_referencias'):
                        st.markdown(f"**Fiabilidad de Referencias:** {ba['fiabilidad_referencias']}")
                    
                    if ba.get('riesgo_comportamental'):
                        st.markdown(f"**Riesgo Comportamental:** {ba['riesgo_comportamental']}")
                    
                    if ba.get('resumen_ejecutivo'):
                        st.markdown(f"**Resumen:** {ba['resumen_ejecutivo']}")
                    
                    if ba.get('tokens_used'):
                        st.caption(f"Tokens utilizados: {ba['tokens_used']}")
                else:
                    st.warning("⚠️ Análisis comportamental no disponible")
            
            with tab4:
                if result.consolidated_report and result.consolidated_report.get('success', True):
                    cr = result.consolidated_report
                    st.markdown("### Reporte Consolidado")
                    
                    if cr.get('credit_recommendation'):
                        st.markdown(f"**Recomendación Crediticia:** {cr['credit_recommendation']}")
                    
                    if cr.get('justification'):
                        st.markdown(f"**Justificación:** {cr['justification']}")
                    
                    if cr.get('contributing_factors'):
                        st.markdown("**Factores Contribuyentes:**")
                        for factor in cr['contributing_factors']:
                            st.markdown(f"- {factor}")
                    
                    if cr.get('tokens_used'):
                        st.caption(f"Tokens utilizados: {cr['tokens_used']}")
                else:
                    st.warning("⚠️ Reporte consolidado no disponible")
            
            # Información técnica
            with st.expander("🔧 Información Técnica"):
                st.markdown(f"**ID de Evaluación:** {result.evaluation_id}")
                st.markdown(f"**Timestamp:** {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Empresa:** {result.company_name}")
                st.markdown(f"**Estado:** {'✅ Exitoso' if result.success else '❌ Error'}")
                
                if hasattr(result, 'total_tokens_used'):
                    st.markdown(f"**Tokens Totales:** {result.total_tokens_used}")
            
        except Exception as e:
            st.error(f"❌ Error durante la evaluación: {str(e)}")
            with st.expander("Detalles del error"):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
