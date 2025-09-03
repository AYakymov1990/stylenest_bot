# Анализ совместимости с PythonAnywhere Hacker планом

## 📊 Характеристики Hacker плана ($5/месяц):
- **CPU**: 2000 секунд/день для always-on tasks
- **RAM**: ~512 МБ
- **Диск**: 1 ГБ
- **Веб-приложения**: 1 приложение
- **Always-on tasks**: до 2 задач
- **Домен**: yourusername.pythonanywhere.com

## 🔍 Анализ твоего бота:

### 1. **Worker (основная задача)**
```python
# 4 цикла каждые 60 секунд:
- reminders_loop()    # напоминания о подписках
- expiry_loop()       # обработка истекших подписок  
- winback_loop()      # winback-сообщения
- polling (aiogram)   # обработка Telegram updates
```

**Потребление CPU:**
- Каждый цикл: ~0.1-0.5 CPU секунд
- 4 цикла × 60 раз/час × 24 часа = 5760 циклов/день
- **Итого**: ~50-200 CPU секунд/день ✅

### 2. **Веб-дашборд**
```python
# Flask приложение с маршрутами:
- / (dashboard)       # главная страница
- /users             # список пользователей
- /payments          # список платежей
- /subscriptions     # список подписок
- /api/stats         # JSON API
```

**Потребление CPU:**
- Обработка запросов: ~0.01-0.1 CPU секунд/запрос
- При 100 запросах/день: ~1-10 CPU секунд/день ✅

### 3. **База данных (SQLite)**
```python
# Таблицы:
- users (с winback полями)
- payments  
- subscriptions
- alembic_version
```

**Потребление ресурсов:**
- Размер БД: ~1-10 МБ ✅
- RAM для SQLite: ~5-20 МБ ✅
- CPU для запросов: минимальный ✅

### 4. **Логирование**
```python
# Файлы логов:
- logs/bot.log       # общие логи
- logs/tasks.log     # логи задач
```

**Потребление ресурсов:**
- Размер логов: ~10-50 МБ/месяц ✅
- CPU для записи: минимальный ✅

## ⚠️ Потенциальные проблемы:

### 1. **WayForPay Webhook**
```python
WFP_SERVICE_URL: str = "https://5a48d4465205.ngrok-free.app/wfp/callback"
```
**Проблема**: Используется ngrok (временный URL)
**Решение**: Изменить на PythonAnywhere URL:
```python
WFP_SERVICE_URL: str = "https://yourusername.pythonanywhere.com/wfp/callback"
```

### 2. **Always-on tasks лимит**
**Проблема**: Hacker план позволяет только 2 always-on tasks
**Текущее использование**: 1 task (worker) + 1 task (веб-дашборд)
**Статус**: ✅ В пределах лимита

### 3. **CPU лимит при высокой нагрузке**
**Проблема**: При >1000 активных пользователей может превысить 2000 CPU секунд/день
**Решение**: Мониторить CPU usage, при необходимости перейти на Web Developer ($12/месяц)

## 🎯 Рекомендации:

### ✅ **Hacker план ДОСТАТОЧЕН для:**
- До 1000 активных пользователей
- До 100 платежей/день
- До 100 подписок
- Нормальная работа всех функций

### ⚠️ **Перейти на Web Developer ($12/месяц) если:**
- >1000 активных пользователей
- >100 платежей/день
- CPU usage >1500 секунд/день
- Нужно больше always-on tasks

### 🔧 **Обязательные изменения для PythonAnywhere:**

1. **Обновить WFP_SERVICE_URL:**
```python
WFP_SERVICE_URL: str = "https://yourusername.pythonanywhere.com/wfp/callback"
```

2. **Обновить PUBLIC_BASE_URL:**
```python
PUBLIC_BASE_URL: str = "https://yourusername.pythonanywhere.com"
```

3. **Настроить веб-приложение для WayForPay webhook:**
```python
# Создать маршрут для webhook
@app.route('/wfp/callback', methods=['POST'])
def wfp_callback():
    # Обработка webhook от WayForPay
    pass
```

## 📈 **План масштабирования:**

### Этап 1: Hacker ($5/месяц)
- До 500 пользователей
- Все функции работают
- Мониторинг CPU usage

### Этап 2: Web Developer ($12/месяц)  
- До 2000 пользователей
- Больше CPU и always-on tasks
- При необходимости

### Этап 3: Custom ($20+/месяц)
- >2000 пользователей
- Выделенные ресурсы
- При росте бизнеса

## ✅ **Вывод: Hacker план ДОСТАТОЧЕН для старта!**

Твой бот будет отлично работать на Hacker плане. Основные ограничения:
- Мониторить CPU usage
- Обновить URL для WayForPay
- При росте перейти на Web Developer

**Начинай с Hacker плана - это оптимальный выбор для старта!** 🚀
