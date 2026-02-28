FROM python:3.14
WORKDIR /app
RUN pip install --no-cache-dir aiogram python-dotenv
COPY . /app
CMD ["python3", "bot.py"]
