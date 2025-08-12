#!/bin/bash

echo "🧹 Limpiando proyecto PymeRisk para producción..."

# Eliminar archivos de testing y debug
echo "🗑️ Eliminando archivos de testing..."
rm -f test_*.py
rm -f debug_*.py
rm -f main_integrated.py

# Eliminar documentación redundante
echo "🗑️ Eliminando documentación redundante..."
rm -f "explicacion de agentes.txt"
rm -f FRONTEND_INTEGRATION_GUIDE.md
rm -f GUIA_SOLUCION_NA_FINANCIERO.md

# Eliminar carpetas innecesarias
echo "🗑️ Eliminando carpetas innecesarias..."
rm -rf frontend/
rm -rf Planificacion/
rm -rf pdf/
rm -rf __pycache__/
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Eliminar logs de desarrollo
echo "🗑️ Eliminando logs de desarrollo..."
rm -f audit.log
rm -f audit.log.backup

# Eliminar archivos temporales
echo "🗑️ Eliminando archivos temporales..."
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*~" -delete
find . -name ".DS_Store" -delete

echo "✅ Limpieza completada!"
echo ""
echo "📁 Archivos mantenidos para producción:"
echo "   ✅ app.py (Frontend Streamlit)"
echo "   ✅ agents/ (Sistema de evaluación)"
echo "   ✅ requirements.txt (Dependencias)"
echo "   ✅ .streamlit/ (Configuración)"
echo "   ✅ .gitignore"
echo "   ✅ README.md, DOCUMENTATION.md, DEPLOY_GUIDE.md"
echo "   ✅ SISTEMA_INFO.txt"
echo ""
echo "⚠️  IMPORTANTE: Asegúrate de configurar las variables de entorno en Streamlit Cloud"
echo "⚠️  NO subas el archivo .env al repositorio"
echo ""
echo "🚀 El proyecto está listo para deploy en producción!"