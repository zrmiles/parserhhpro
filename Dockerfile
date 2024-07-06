# Используем официальный образ Python
FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы requirements.txt и устанавливаем зависимости
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Указываем команду для запуска приложения
CMD ["python", "app.py"]
