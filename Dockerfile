FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 443
CMD ["python", "bot.py", "main.py"]