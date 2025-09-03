# app/web/wsgi.py
# WSGI файл для PythonAnywhere

import sys
import os

# Добавляем путь к проекту (ЗАМЕНИТЬ yourusername на свой username)
project_home = '/home/yourusername/stylenest_bot'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Устанавливаем рабочую директорию
os.chdir(project_home)

# Импортируем Flask приложение
from app.web.dashboard import app

# Это нужно для PythonAnywhere
application = app

if __name__ == "__main__":
    app.run(debug=False)
