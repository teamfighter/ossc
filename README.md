# OSSC — обёртка над OpenStack CLI

Небольшая утилита, которая читает `rc-*.sh` (или их импортированные эквиваленты в конфиге), применяет переменные окружения `OS_*` и прозрачно проксирует команды в `openstack`. Поддерживаются Linux и macOS.

## Установка и авто‑настройка

- Требуется установленный Python 3.8+.
- При первом запуске `ossc` автоматически подготовит окружение:
  - создаст пользовательский venv в `~/.config/ossc/venv`
  - установит пакеты из `requirements.txt`: `python-openstackclient`, `python-octaviaclient`, `python-glanceclient`, `python-manilaclient==3.4.0`
- Альтернатива (ручная подготовка окружения в репозитории):

```bash
make setup                # Linux/macOS
```

## Быстрый старт

1) Импортируйте выданные RC-файлы в конфиг:

```bash
./ossc config import-rc --profile dev  --catalog app --rc-file dev/rc-app.sh
./ossc config import-rc --profile prod --catalog net --rc-file prod/rc-net.sh
```

Или выполните пакетный импорт из директории с RC-файлами:

```bash
./ossc config import-rc --profile dev --rc-dir ./dev
# Для каждого rc-*.sh каталог берётся из имени файла (rc-<catalog>.sh).
# Если имя не распарсилось, используется OS_PROJECT_ID из файла.
```

2) Выполните команду (на первом запуске будет авто‑установка клиентов и запрос недостающих кредов):

```bash
./ossc --profile dev --catalog app server list
```

3) Посмотреть доступные профили/каталоги:

```bash
./ossc config list
```

4) Проверить без выполнения (dry‑run):

```bash
./ossc --profile dev --catalog app --dry-run server list
```

Примечание: первый запуск может занять 1–2 минуты из‑за установки клиентов.

## Запуск

- Локально: `./ossc --profile <p> --catalog <c> <openstack args>`

Примеры:

```bash
./ossc --profile dev  --catalog app         server list
./ossc --profile prod --catalog vpc-transit server list
```

## Справка и помощь

- Помощь по обёртке:
  - `ossc -h`
  - `ossc config -h`
  - `ossc report -h`

- Полная помощь OpenStack (минуя парсер обёртки):
  - `ossc --profile <p> --catalog <c> -- --help`
  - `ossc --profile <p> --catalog <c> help`
  - По теме: `ossc --profile <p> --catalog <c> help server`

Примеры:

```bash
./ossc --profile dev --catalog app -- --help
./ossc --profile dev --catalog app help server
```

## Опции ossc

- `--profile`: имя профиля (например, `dev`, `prod`). Обязательно для режима прокси и команд.
- `--catalog`: имя каталога/проекта (например, `app`, `infra`). Обязательно для режима прокси.
- `--rc-file`: явный путь к RC-файлу для одиночного импорта или разового запуска.
- `--username`: переопределение `OS_USERNAME` (обычно берётся из RC/конфига).
- `--password`: переопределение `OS_PASSWORD` (иначе берётся из конфига или спрашивается при первом запуске).
- `--dry-run`: показать финальные `OS_*` и команду, но не выполнять.
- `--`: разделитель; всё после `--` передаётся напрямую в `openstack`.

Подкоманды:

- `config import-rc`: импорт одного RC (`--rc-file` и `--catalog`) или пакетный импорт (`--rc-dir`).
- `config list`: список профилей и их каталогов.
- `config set-cred`: установка пароля для профиля (логин берётся из RC/конфига каталога).
- `report [--out DIR]`: сформировать отчёты (`openstack server list`) по всем каталогам всех профилей.

## Конфиги вместо RC

Рекомендуется хранить конфигурации в пользовательском конфиге, без зависимости от `rc-*.sh`.

- Импорт RC в конфиг (см. «Быстрый старт») и пользуйтесь как обычно.
- Если в конфиге нет записи для пары `profile/catalog`, будет прочитан `rc-*.sh` по схеме `<profile>/rc-<catalog>.sh` (fallback).
- Добавление нового каталога: положите новый `rc-*.sh` в репозиторий и выполните `ossc config import-rc ...`.

Настройка пароля для профиля (логин берётся из RC/конфига каталога):

```bash
ossc config set-cred --profile dev              # спросит пароль скрытым вводом
ossc config set-cred --profile dev --password 'secret'
```

## Креды и конфиг

- Основной конфиг: `~/.config/ossc/profiles.json`.
- Приоритет значений:
  1) флаги `--username` / `--password`
  2) переменные окружения `OSS_USERNAME` / `OSS_PASSWORD`
  3) пользовательский конфиг `profiles.json`
  4) `OS_USERNAME` из RC (для имени пользователя)
- Безопасность: чувствительные данные (логины/пароли/токены) не хранятся в репозитории. Секреты — только в пользовательском конфиге.

## Отчёты

Сводный отчёт по всем профилям/каталогам из конфига (выполняет `openstack server list` для каждого):

```bash
./ossc report
./ossc --profile dev report                  # только профиль dev
./ossc --profile dev --catalog app report    # только dev/app
./ossc --catalog app report                  # все профили, где есть catalog=app

# Формат вывода как в OpenStack: table|json|yaml|csv|value (по умолчанию table)
./ossc report -f json
```

Результаты сохраняются в `out/reports/{profile}/{catalog}/report.txt` с заголовком (время, команда, профиль/каталог) и stdout/stderr команды. Путь можно изменить опцией `--out`.

## Архитектура

- Пакет `core/` — ядро:
  - `core/cli.py`: сборка CLI, маршрутизация субкоманд.
  - `core/config.py`: чтение/запись `~/.config/ossc/profiles.json`, структура, резолв кредов.
  - `core/rc.py`: парсинг `rc-*.sh`, построение путей.
  - `core/env.py`: авто‑подготовка окружения, поиск `openstack` (venv по умолчанию в `~/.config/ossc/venv`).
  - `core/commands/`:
    - `config_cmd.py`: `ossc config import-rc`, `ossc config list`.
    - `report_cmd.py`: `ossc report` — формирование отчётов.
- Точка входа `ossc.py` — тонкая обёртка, вызывает `core.cli.main()`.

## Структура

- Скрипты запуска: `ossc` (Linux/macOS)
- Основная логика: `ossc.py`, пакет `core/`
- Зависимости: `requirements.txt`

## Контейнеризация (Docker)

Чтобы избежать локальной установки зависимостей, можно использовать Docker-образ.

Сборка образа:

```bash
docker build -t ossc:latest .
```

Упрощённый запуск через wrapper (рекомендуется):

```bash
# Подгрузить функцию в текущую сессию
source ./ossc-docker.sh

# Использовать как обычный ossc
ossc --profile dev --catalog app server list
```

Что делает wrapper:
- монтирует текущую директорию в контейнер (`/workspace`)
- монтирует пользовательский конфиг `~/.config/ossc` внутрь контейнера в `/tmp/.config/ossc`
- запускает образ `ossc:latest` с `HOME=/tmp` и `XDG_CONFIG_HOME=/tmp/.config`

Можно обойтись без wrapper и вызывать напрямую:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e XDG_CONFIG_HOME=/tmp/.config \
  -v "$HOME/.config/ossc:/tmp/.config/ossc" \
  -v "$(pwd):/workspace" -w /workspace \
  ossc:latest --profile dev --catalog app server list
```

## Тесты

- Запуск напрямую:

```bash
python3 -m unittest discover -v
```

- Через виртуальное окружение проекта:

```bash
make setup
.venv/bin/python -m unittest -v
```

- Упрощённо одной командой:

```bash
make test
```
