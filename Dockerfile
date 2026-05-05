FROM python:3.11-slim

#EVITA BUFFER NO PYTHON

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

#Instalar dependências

RUN apt-get update && apt-get install -y \
    ffmpeg\
    gifsicle\
    && rm -rf /var/lib/lists/*

#Diretírio do app

WORKDIR /app

#Copia dependencias 

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

#Copia o restente do projeto

COPY . .

#PORTA django

EXPOSE 8000

#Comando padrão

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]