# Guía de Deploy - PymeRisk en Streamlit Cloud

## 🚀 Deploy URL
https://deploy-pymerisk-dhtmtkfxynnrd6wqzsztbu.streamlit.app/

## 📋 Pasos para Deploy en Streamlit Cloud

### 1. Preparación del Repositorio
- ✅ Archivo `app.py` creado (frontend principal)
- ✅ `requirements.txt` actualizado con Streamlit y PyPDF2
- ✅ Configuración `.streamlit/config.toml`
- ✅ Ejemplo `.streamlit/secrets.toml.example`

### 2. Configuración de Variables de Entorno en Streamlit Cloud

**IMPORTANTE**: No subas el archivo `.env` al repositorio. En su lugar:

1. Ve a tu app en [share.streamlit.io](https://share.streamlit.io)
2. Haz clic en "Settings" → "Secrets"
3. Añade las siguientes variables:

```toml
# Azure OpenAI Service (REQUERIDO)
AZURE_OPENAI_ENDPOINT = "https://hackathon-openai-svc.openai.azure.com/"
AZURE_OPENAI_API_KEY = "your-azure-openai-api-key-here"
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"

# Modelos Azure OpenAI
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_MODEL = "gpt-4o"
AZURE_OPENAI_DEPLOYMENT_MINI = "o3-mini"
AZURE_OPENAI_MODEL_MINI = "o3-mini"

# Azure Infrastructure (Opcional)
AZURE_SUBSCRIPTION_ID = "-2cb7e9109ea3-4f95-9265-db1da3765484"
AZURE_RESOURCE_GROUP = "HackIAthon"
AZURE_LOCATION = "eastus"

# OpenAI Fallback (Opcional)
OPENAI_API_KEY = "your-openai-api-key-here"
```

### 3. Estructura de Archivos para Deploy

```
PymeRisk/
├── app.py                          # 🎯 ARCHIVO PRINCIPAL DE STREAMLIT
├── requirements.txt                # Dependencias actualizadas
├── .streamlit/
│   ├── config.toml                # Configuración de tema
│   └── secrets.toml.example       # Ejemplo de secrets
├── agents/                        # Sistema de evaluación
│   ├── azure_orchestrator.py     # Orquestador principal
│   ├── business_agents/           # Agentes de negocio
│   └── infrastructure_agents/     # Servicios Azure
├── .gitignore                     # Excluye .env y secrets
└── DEPLOY_GUIDE.md               # Esta guía
```

### 4. Archivos que NO deben subirse al repositorio

Asegúrate de que tu `.gitignore` incluya:

```gitignore
# Variables de entorno sensibles
.env
.streamlit/secrets.toml

# Cache y archivos temporales
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Logs
*.log
audit.log*

# Archivos de desarrollo
.vscode/
.idea/
```

### 5. Comandos para Deploy

```bash
# 1. Verificar que .env no esté en el repo
git status
# No debe aparecer .env

# 2. Añadir archivos al repositorio
git add app.py requirements.txt .streamlit/ DEPLOY_GUIDE.md

# 3. Commit y push
git commit -m "Add Streamlit frontend for hackathon deploy"
git push origin main

# 4. Configurar en Streamlit Cloud:
# - Repository: tu-usuario/PymeRisk
# - Branch: main
# - Main file path: app.py
```

### 6. Testing Local

Para probar localmente antes del deploy:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Ejecutar Streamlit
streamlit run app.py
```

### 7. Funcionalidades del Frontend

- 📄 **Upload de PDFs**: Balance financiero + información general
- 🤖 **Evaluación IA**: Usando Azure OpenAI (GPT-4o + o3-mini)
- 📊 **Resultados**: Score 0-1000, nivel de riesgo, análisis detallado
- 🔍 **Análisis**: Financiero, reputacional, comportamental
- ⏱️ **Tiempo**: 15-20 segundos por evaluación

### 8. Fuente de Datos Recomendada

El sistema está optimizado para procesar documentos de:
**Superintendencia de Compañías del Ecuador**
https://appscvsgen.supercias.gob.ec/consultaCompanias/societario/busquedaCompanias.jsf

### 9. Troubleshooting

**Error de importación de agentes:**
- Verifica que todos los archivos de `agents/` estén en el repositorio
- Asegúrate de que `__init__.py` exista en cada carpeta de agentes

**Error de Azure OpenAI:**
- Verifica que las variables de entorno estén configuradas en Streamlit Cloud
- Confirma que el endpoint y API key sean correctos

**Error de PDF:**
- Verifica que PyPDF2 esté en requirements.txt
- Asegúrate de que los PDFs no estén protegidos con contraseña

### 10. Monitoreo

Una vez desplegado, puedes monitorear:
- Logs en Streamlit Cloud dashboard
- Métricas de uso de Azure OpenAI
- Tiempo de respuesta de evaluaciones

## 🎯 Resultado Final

Frontend funcional en: https://deploy-pymerisk-dhtmtkfxynnrd6wqzsztbu.streamlit.app/

Características:
- ✅ Upload de 2 PDFs
- ✅ Extracción automática de texto
- ✅ Evaluación con IA (Azure OpenAI)
- ✅ Resultados detallados y visualización
- ✅ Tiempo de respuesta optimizado (15-20s)
- ✅ Interfaz intuitiva y profesional