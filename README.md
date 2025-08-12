# 🏦 PymeRisk - Sistema de Evaluación de Riesgo Financiero

## 🚀 **ESTADO: FUNCIONAL Y DESPLEGADO**
- **URL Deploy**: https://deploy-pymerisk-dhtmtkfxynnrd6wqzsztbu.streamlit.app/
- **Versión**: 1.0 - Producción
- **Última actualización**: Enero 2025

## 📋 Descripción

Sistema de inteligencia artificial que evalúa el riesgo crediticio de PYMEs ecuatorianas en 50-60 segundos, utilizando Azure OpenAI (GPT-4o + o3-mini) y análisis multidimensional de documentos financieros.

## ✨ Características Principales

- 📊 **Análisis Financiero**: Estados financieros con GPT-4o
- 🌟 **Análisis Reputacional**: Comentarios y redes sociales con o3-mini  
- 📈 **Análisis Comportamental**: Patrones de pago y referencias
- 🎯 **Score Final**: 0-1000 con clasificación ALTO/MEDIO/BAJO
- ⚡ **Tiempo**: 50-60 segundos por evaluación
- 🔒 **Seguridad**: Validación y sanitización completa

## 🛠️ Tecnologías

- **Frontend**: Streamlit
- **Backend**: Python + AsyncIO
- **IA**: Azure OpenAI Service (GPT-4o + o3-mini)
- **Extracción**: PyPDF2 con mejoras de espaciado
- **Deploy**: Streamlit Cloud

## 🚀 Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/PymeRisk.git
cd PymeRisk
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
# Crear archivo .env con:
AZURE_OPENAI_ENDPOINT=https://tu-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=tu-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_DEPLOYMENT_MINI=o3-mini
```

### 4. Ejecutar la aplicación
```bash
streamlit run app.py
```

## 📱 Uso del Sistema

1. **Subir PDFs**: Balance financiero + información general
2. **Datos de empresa**: Nombre y referencias comerciales
3. **Comentarios simulados**: Activar para demostrar análisis reputacional
4. **Ejecutar evaluación**: Esperar 50-60 segundos
5. **Ver resultados**: Score, análisis detallado y recomendaciones

## 📊 Fuente de Datos Recomendada

[Superintendencia de Compañías del Ecuador](https://appscvsgen.supercias.gob.ec/consultaCompanias/societario/busquedaCompanias.jsf)

## 🏗️ Arquitectura

```
Frontend (Streamlit) → AzureOrchestrator → [Financial, Reputational, Behavioral] → Score Final
```

### Componentes Clave:
- `app.py` - Frontend Streamlit
- `agents/azure_orchestrator.py` - Orquestador principal
- `agents/business_agents/` - Agentes de análisis
- `agents/infrastructure_agents/` - Servicios Azure

## 📈 Métricas de Rendimiento

- ⏱️ **Tiempo**: 50-60 segundos por evaluación
- 🎯 **Success Rate**: 100%
- 💰 **Tokens**: 3K-8K por evaluación
- 🔄 **Concurrencia**: Soporte para múltiples evaluaciones

## 🔧 Deploy en Streamlit Cloud

1. **Configurar secrets** en Streamlit Cloud:
```toml
AZURE_OPENAI_ENDPOINT = "https://tu-endpoint.openai.azure.com/"
AZURE_OPENAI_API_KEY = "tu-api-key"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_DEPLOYMENT_MINI = "o3-mini"
```

2. **Deploy automático** desde GitHub

## 📚 Documentación Adicional

- `DOCUMENTATION.md` - Documentación técnica completa
- `DEPLOY_GUIDE.md` - Guía detallada de deploy
- `SISTEMA_INFO.txt` - Información técnica del sistema

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Create Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## 👥 Autores

- **Equipo PymeRisk** - Desarrollo inicial

## 🙏 Agradecimientos

- Azure OpenAI Service por la infraestructura de IA
- Streamlit por la plataforma de frontend
- Superintendencia de Compañías del Ecuador por los datos de referencia