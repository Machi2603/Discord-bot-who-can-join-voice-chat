FROM python:3.9-slim

# 1. Instalar FFmpeg (El motor de audio)
RUN apt-get update && \
    apt-get install -y ffmpeg libffi-dev libnacl-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

# 2. Preparar la carpeta
WORKDIR /app

# 3. Copiar e instalar librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el código
COPY . .

# 5. Arrancar
CMD ["python", "main.py"]