# OSSC — обёртка над OpenStack CLI

Небольшая утилита, которая читает `rc-*.sh` (или их импорт в конфиг), применяет переменные `OS_*` и прозрачно проксирует команды в `openstack`.

## Предпочтительно: через Docker

- Почему так лучше:
  - не нужен локальный Python и клиенты OpenStack
  - изоляция окружения, воспроизводимость
  - конфиг пользователя монтируется и сохраняется вне контейнера

1) Соберите образ
```bash
docker build -t ossc:latest .
```

2) Загрузите враппер-функцию в текущую сессию
```bash
source ./ossc-docker.sh
```

3) Импортируйте RC-файлы (они должны быть доступны в рабочей директории)
```bash
ossc config import-rc --profile dev  --catalog app --rc-file dev/rc-app.sh
ossc config import-rc --profile prod --catalog net --rc-file prod/rc-net.sh
# или пакетно по директории
ossc config import-rc --profile dev --rc-dir ./dev
```

4) Запускайте команды OpenStack
```bash
ossc --profile dev --catalog app server list
```

Примечания
- Внутри контейнера `HOME=/tmp`, `XDG_CONFIG_HOME=/tmp/.config`.
- Файл конфига хранится на хосте: `~/.config/ossc/profiles.json` (враппер монтирует его в контейнер).
- Можно переопределить образ переменной `OSSC_IMAGE` до `source ./ossc-docker.sh`.

## Альтернатива: локально (Python)

1) Требуется Python 3.8+
2) Подготовьте окружение:
```bash
make setup
```
3) Запуск:
```bash
./ossc --profile <p> --catalog <c> <openstack args>
```

Полезно
```bash
# Справка по обёртке и подкомандам
ossc -h
ossc config -h
ossc report -h

# Передать аргументы напрямую в openstack
ossc --profile <p> --catalog <c> -- --help

# Проверка без выполнения
ossc --profile <p> --catalog <c> --dry-run server list
```

## Конфиг и креды

- Путь конфига: `~/.config/ossc/profiles.json` (или `$XDG_CONFIG_HOME/ossc/profiles.json`).
- Приоритет значений:
  1) флаги `--username` / `--password`
  2) переменные окружения `OSS_USERNAME` / `OSS_PASSWORD`
  3) пользовательский конфиг `profiles.json`
  4) `OS_USERNAME` из RC (только для имени пользователя)
- Секреты не хранятся в репозитории.

## Подкоманды

- `config import-rc`: импорт RC-файлов в конфиг (одиночный или пакетный `--rc-dir`).
- `config list`: список профилей и их каталогов.
- `config set-cred`: установка пароля для профиля (логин берётся из RC/конфига каталога).
- `report [-f table|json|yaml|csv|value] [--out DIR]`: сформировать отчёты `openstack server list` по выбранным профилям/каталогам.

Примеры
```bash
# Список профилей/каталогов
ossc config list

# Пароль для профиля
ossc config set-cred --profile dev                      # спросит пароль скрытым вводом
ossc config set-cred --profile dev --password 'secret'  # без запроса

# Отчёты
ossc report                               # все профили/каталоги
ossc --profile dev report                  # только профиль dev
ossc --profile dev --catalog app report    # только dev/app
ossc --catalog app report                  # все профили с каталогом app
```

## Тесты

```bash
make test                   # создаст .venv и запустит unittest
# или
python3 -m unittest -v
```

## Устройство

- `core/cli.py` — парсинг CLI, роутинг и прокси вызова
- `core/config.py` — чтение/запись `profiles.json`, структура, резолв кредов
- `core/rc.py` — парсинг `rc-*.sh`, построение путей
- `core/env.py` — поиск/подготовка `openstack` (локальный .venv, пользовательский venv)
- `core/commands/config_cmd.py` — команды `config`
- `core/commands/report_cmd.py` — команда `report`
- Точки входа: `ossc` (bash-скрипт), `ossc.py`
