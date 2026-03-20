# Telegram Business Bot

Бизнес-бот для Telegram на Python (aiogram 3) с PostgreSQL.

## Возможности

- Развёрнутые ответы на личные сообщения (цены, услуги, контакты, заявки)
- Сохранение всех обращений в PostgreSQL
- История обращений по команде `/history`
- Готов к деплою на Railway

## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполните .env своими данными
python -m bot.main
```

## Переменные окружения

| Переменная    | Описание                        |
|---------------|---------------------------------|
| `BOT_TOKEN`   | Токен бота из @BotFather        |
| `DATABASE_URL`| URL подключения к PostgreSQL    |

## Деплой на Railway

1. Создайте проект на [Railway](https://railway.app)
2. Добавьте сервис PostgreSQL
3. Подключите GitHub-репозиторий
4. Добавьте переменные `BOT_TOKEN` и `DATABASE_URL`
5. Деплой произойдёт автоматически

## Структура проекта

```
bot/
├── main.py            # Точка входа
├── config.py          # Конфигурация
├── db/
│   ├── engine.py      # Подключение к БД
│   ├── models.py      # Модели SQLAlchemy
│   └── repo.py        # Репозиторий (запросы к БД)
├── handlers/
│   ├── start.py       # Команда /start
│   ├── history.py     # Команда /history
│   └── messages.py    # Обработка сообщений
└── middlewares/
    └── db.py          # Middleware для сессий БД
```
