FROM python:3.10-slim

WORKDIR /app

# Копируем зависимости и устанавливаем их с зеркалом
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple/

# Копируем весь код
COPY . .

CMD ["python", "bot.py"]