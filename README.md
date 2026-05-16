# tg-keyword-monitor

Телеграм userbot, который мониторит все группы и чаты, фильтрует сообщения по ключевым словам и пересылает совпадения в указанный чат.

## Требования

- Docker + Docker Compose (рекомендуется)
- или Python 3.12+ для локального запуска
- Аккаунт Telegram и API credentials с [my.telegram.org](https://my.telegram.org)

## Получение API credentials

1. Зайти на [my.telegram.org](https://my.telegram.org) под своим аккаунтом
2. Перейти в **API development tools**
3. Создать приложение (название и платформа — любые)
4. Скопировать `App api_id` и `App api_hash`

## Конфигурация

```bash
cp config.example.yaml config.yaml
```

Открыть `config.yaml` и заполнить обязательные поля:

```yaml
api_id: 12345678
api_secret: "your_api_hash"

destination_chat: "@username"  # куда пересылать (username или числовой ID)

keywords:
  - "важное слово"
  - "re:invoice\\s*#?\\d+"  # regex — добавить префикс "re:"
```

Полный список настроек — в `config.example.yaml`.

## Запуск через Docker (рекомендуется)

### Первый запуск — авторизация

При первом запуске нужно ввести номер телефона и код из Telegram.
Запускать без `-d`, чтобы был доступ к stdin:

```bash
docker compose run --rm monitor
```

```
Phone number (international format): +79991234567
Enter the code you received: 12345
Enter your 2FA password (if set, else press Enter):
```

После авторизации в корне проекта появится `monitor.session`. Контейнер можно остановить.

### Обычный запуск

```bash
docker compose up -d
```

Логи:

```bash
docker compose logs -f
```

Остановка:

```bash
docker compose down
```

### Узнать chat_id группы

Если не знаешь точный ID для `destination_chat`:

```bash
docker compose run --rm monitor /venv/bin/python list_dialogs.py
```

Выведет список всех диалогов в формате `ID  Название`. Найди нужную группу и скопируй ID в конфиг.

### Обновление зависимостей

Если изменился `requirements.txt`, нужно пересоздать venv-volume:

```bash
docker compose down
docker volume rm tg-keyword-monitor_venv
docker compose up -d
```

---

## Локальный запуск (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Фоновый запуск через systemd (Linux)

Создать файл `/etc/systemd/system/tgmon.service`:

```ini
[Unit]
Description=tg-keyword-monitor
After=network.target

[Service]
WorkingDirectory=/path/to/tg-keyword-monitor
ExecStart=/path/to/tg-keyword-monitor/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now tgmon
sudo systemctl status tgmon
```

---

## Файлы, которые создаются при работе

| Файл | Описание |
|---|---|
| `monitor.session` | Telegram-сессия (не удалять) |
| `seen.db` | SQLite база для дедупликации |
| `monitor.log` | Лог (если указан `log_file` в конфиге) |

Все файлы добавлены в `.gitignore`.
