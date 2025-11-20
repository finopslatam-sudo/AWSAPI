#!/bin/bash
echo "🚀 Configurando proyecto AWS API..."

# Crear entorno virtual
echo "🐍 Creando entorno virtual..."
python3 -m venv venv

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install boto3 python-dotenv flask pandas

# Verificar instalación
echo "✅ Verificando instalación..."
python -c "import boto3; print('boto3: OK')"
python -c "from dotenv import load_dotenv; print('python-dotenv: OK')"
python -c "import flask; print('flask: OK')"

echo "🎉 ¡Configuración completada!"
echo "💡 Recuerda activar el entorno con: source venv/bin/activate"