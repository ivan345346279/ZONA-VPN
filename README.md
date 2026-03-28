# 🛡️ VPN Site — Flask

Красивый VPN-сайт с Telegram-авторизацией и админ-панелью.

## Быстрый старт

```bash
# 1. Установите зависимости
pip install flask

# 2. Запустите сервер
python server.py
```

Сайт будет доступен на **http://localhost:5000**

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `SECRET_KEY` | `change-me-...` | Секретный ключ Flask (обязательно смените!) |
| `TELEGRAM_BOT_TOKEN` | `YOUR_BOT_TOKEN_HERE` | Токен Telegram-бота |
| `ADMIN_PASSWORD` | `admin123` | Пароль для входа в админ-панель |

```bash
# Пример запуска с переменными
SECRET_KEY=my-super-secret \
TELEGRAM_BOT_TOKEN=1234567890:ABC... \
ADMIN_PASSWORD=securepassword \
python server.py
```

## Страницы

| URL | Описание |
|---|---|
| `/` | Главная страница |
| `/pricing` | Страница тарифов |
| `/admin` | Админ-панель |
| `/admin/login` | Вход в админ-панель |
| `/api/plans` | JSON API тарифов |

## Подключение реального Telegram Login

1. Создайте бота у **@BotFather**, получите `BOT_TOKEN`
2. Выполните `/setdomain` → укажите ваш домен
3. Установите `TELEGRAM_BOT_TOKEN=ваш_токен`
4. В `templates/base.html` замените `BOT_NAME` на username бота
5. Раскомментируйте блок **Real Telegram Widget** в JS

## Структура проекта

```
vpn-site/
├── server.py              # Flask backend
├── requirements.txt
├── vpn.db                 # SQLite (создаётся автоматически)
└── templates/
    ├── base.html          # Базовый шаблон (nav, footer, modal)
    ├── index.html         # Главная страница
    ├── pricing.html       # Страница тарифов
    ├── admin.html         # Админ-панель
    ├── admin_login.html   # Страница входа в админку
    └── plan_form.html     # Форма тарифа (переиспользуется)
```

## Админ-панель

- **Дашборд**: статистика пользователей и тарифов
- **Тарифы**: добавление, редактирование, удаление тарифов
- **Настройки**: название сайта, заголовки, цвета темы
