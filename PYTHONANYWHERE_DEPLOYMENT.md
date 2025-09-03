# Развертывание на PythonAnywhere

## Совместимость проекта с PythonAnywhere

### ✅ Поддерживаемые компоненты:

1. **Python 3.12** - ✅ Поддерживается
2. **SQLite** - ✅ Идеально подходит (файловая БД)
3. **Flask** - ✅ Встроенная поддержка
4. **SQLAlchemy + Alembic** - ✅ Полная поддержка
5. **Aiogram** - ✅ Работает без проблем
6. **Логирование** - ✅ Поддерживается

### 📊 Анализ ресурсов (Hacker план - $5/месяц):

- **CPU**: 2000 секунд/день для always-on tasks
- **RAM**: Достаточно для бота
- **Диск**: 1 ГБ (SQLite + логи + код)
- **Веб-приложение**: 1 приложение (для дашборда)
- **Always-on tasks**: До 2 задач (bot + worker)

### 🚀 План развертывания:

#### 1. Загрузка кода
```bash
# На PythonAnywhere
git clone https://github.com/yourusername/stylenest_bot.git
cd stylenest_bot
```

#### 2. Установка зависимостей
```bash
pip3.12 install --user -r requirements.txt
```

#### 3. Настройка переменных окружения
```bash
# В файле .env
BOT_TOKEN=your_bot_token
CHANNEL_ID=your_channel_id
TARIFF_1M_PRICE_EUR=15
TARIFF_2M_PRICE_EUR=25
TARIFF_3M_PRICE_EUR=35
WFP_MERCHANT_ACCOUNT=your_merchant_account
WFP_MERCHANT_SECRET_KEY=your_secret_key
WFP_SERVICE_URL=https://yourusername.pythonanywhere.com/wfp/callback
```

#### 4. Инициализация БД
```bash
alembic upgrade head
```

#### 5. Настройка Always-on tasks

**Task 1: Bot Worker**
```bash
cd /home/yourusername/stylenest_bot
python3.12 -m app.tasks.worker
```

**Task 2: Web Dashboard (опционально)**
```bash
cd /home/yourusername/stylenest_bot
python3.12 -m app.web.dashboard
```

#### 6. Настройка Web App

**Source code**: `/home/yourusername/stylenest_bot/app/web/wsgi.py`

**Working directory**: `/home/yourusername/stylenest_bot`

### 🔧 Настройки для PythonAnywhere:

#### Пути к файлам:
- **База данных**: `/home/yourusername/stylenest_bot/stylenest.db`
- **Логи**: `/home/yourusername/stylenest_bot/logs/`
- **Alembic**: `/home/yourusername/stylenest_bot/alembic/`

#### Обновление wsgi.py:
```python
# Замените yourusername на ваш username
sys.path.insert(0, '/home/yourusername/stylenest_bot')
```

### 📈 Мониторинг ресурсов:

#### CPU Usage:
- **Bot worker**: ~10-50 CPU секунд/день (зависит от активности)
- **Web dashboard**: ~5-20 CPU секунд/день
- **Итого**: ~15-70 CPU секунд/день (в пределах лимита 2000)

#### Memory Usage:
- **SQLite**: ~1-10 МБ
- **Python процессы**: ~50-100 МБ каждый
- **Итого**: ~150-250 МБ (в пределах лимитов)

#### Disk Usage:
- **Код**: ~50 МБ
- **SQLite БД**: ~1-10 МБ
- **Логи**: ~10-50 МБ
- **Итого**: ~100 МБ (в пределах лимита 1 ГБ)

### 🚨 Потенциальные проблемы и решения:

#### 1. Timezone issues
```python
# В config.py добавить
import os
os.environ['TZ'] = 'UTC'
```

#### 2. Пути к файлам
```python
# Использовать абсолютные пути
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "stylenest.db"
LOG_DIR = BASE_DIR / "logs"
```

#### 3. Логирование
```python
# Настроить логирование для PythonAnywhere
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/yourusername/stylenest_bot/logs/bot.log'),
        logging.StreamHandler()
    ]
)
```

### 🔄 Процесс обновления:

1. **Обновление кода**:
```bash
cd /home/yourusername/stylenest_bot
git pull origin main
```

2. **Обновление зависимостей**:
```bash
pip3.12 install --user -r requirements.txt
```

3. **Миграции БД**:
```bash
alembic upgrade head
```

4. **Перезапуск задач**:
- Остановить always-on tasks
- Запустить заново

### 📊 Дашборд доступен по адресу:
`https://yourusername.pythonanywhere.com/`

### ✅ Преимущества PythonAnywhere для этого проекта:

1. **Простота развертывания** - не нужно настраивать сервер
2. **Автоматические обновления** - Python, библиотеки обновляются автоматически
3. **Встроенная поддержка Flask** - веб-дашборд работает из коробки
4. **Always-on tasks** - бот работает 24/7
5. **SSL сертификаты** - HTTPS из коробки
6. **Backup** - автоматические бэкапы файлов
7. **Мониторинг** - встроенные инструменты мониторинга

### 💡 Рекомендации:

1. **Начать с Hacker плана** ($5/месяц) - достаточно для начала
2. **Мониторить CPU usage** - при превышении лимитов перейти на Web Developer ($12/месяц)
3. **Настроить автоматические бэкапы** БД
4. **Использовать git** для версионирования кода
5. **Настроить логирование** для мониторинга работы бота
