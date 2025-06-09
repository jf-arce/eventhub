# Imagen base oficial de Python, versión slim para menor tamaño
FROM python:3.13.4-slim-bullseye

# Variables de entorno para evitar archivos .pyc y logs en buffer
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Actualiza el sistema y pip, y limpia la caché de apt
RUN apt-get update \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

# Copia el archivo de requerimientos primero para aprovechar la cache de Docker
COPY requirements.txt .

# Instala las dependencias de Python sin guardar archivos temporales de instalación
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código fuente de la aplicación al contenedor
COPY . .

# Ejecutar migraciones (solo por usar sqlite como base de datos)
RUN python manage.py migrate

# Expone el puerto 8000 (por defecto para Django)
EXPOSE 8000

# Comando por defecto para iniciar la app con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "eventhub.wsgi:application"]