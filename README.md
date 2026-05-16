# tg-keyword-monitor

Телеграм userbot, который мониторит все группы и чаты, фильтрует сообщения по ключевым словам и пересылает совпадения в указанный чат.

## Требования

- Python 3.11+
- Аккаунт Telegram
- API credentials с [my.telegram.org](https://my.telegram.org)

## Установка

```bash
git clone <repo>
cd tg-keyword-monitor
pip install -r requirements.txt
```

## Получение API credentials

1. Зайти на [my.telegram.org](https://my.telegram.org) под своим аккаунтом
2. Перейти в **API development tools**
3. Создать приложение (название и платформа — любые)
4. Скопировать `App api_id` и `App api_hash`

## Конфигурация

```bash
cp config.example.yaml config.yaml
```

Открыть `config.yaml` и заполнить:

```yaml
api_id: 12345678           # из my.telegram.org
api_secret: "abc123..."    # из my.telegram.org

destination_chat: "@username"  # куда пересылать (username или числовой ID чата)

keywords:
  - "важное слово"
  - "re:invoice\\s*#?\\d+"  # regex — добавить префикс "re:"
```

Полный список настроек с описанием — в `config.example.yaml`.

## Запуск

```bash
python main.py
```

При первом запуске потребуется авторизация:

```
Phone number (international format): +79991234567
Enter the code you received: 12345
Enter your 2FA password (if set, else press Enter):
```

После этого создастся файл `monitor.session` — повторная авторизация не потребуется.

## Фоновый запуск (24/7)

**Через screen:**
```bash
screen -dmS tgmon python main.py
# вернуться к логам:
screen -r tgmon
```

**Через systemd (Linux):**

Создать файл `/etc/systemd/system/tgmon.service`:

```ini
[Unit]
Description=tg-keyword-monitor
After=network.target

[Service]
WorkingDirectory=/path/to/tg-keyword-monitor
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now tgmon
sudo systemctl status tgmon
```

## Файлы, которые создаются при работе

| Файл | Описание |
|---|---|
| `monitor.session` | Telegram-сессия (не удалять) |
| `seen.db` | SQLite база для дедупликации |
| `monitor.log` | Лог (если указан `log_file` в конфиге) |

Все три файла добавлены в `.gitignore`.
