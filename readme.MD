# Отчёт о внедрении S3-хранилища, системы мониторинга (Prometheus + Grafana), CI/CD и модульных тестов

## 1. Введение

В рамках доработки дейтинг-бота были реализованы три ключевых направления:

- **Интеграция S3-совместимого хранилища (MinIO)** для постоянного хранения фотографий пользователей.
- **Система сбора метрик и визуализации (Prometheus + Grafana)** для мониторинга активности и производительности бота.
- **Настройка CI/CD (GitHub Actions)** и **написание модульных тестов** для обеспечения качества кода и автоматизации деплоя.

Все изменения внедрены с полным отказом от временного Telegram-хранилища (`file_id`) – теперь все фотографии хранятся исключительно в S3. Это обеспечивает независимость от Telegram API, масштабируемость и возможность использования CDN.

---

## 2. S3-хранилище (MinIO)

### Цель
Перенести хранение фотографий из Telegram (`file_id`) в постоянное S3-совместимое хранилище.

### Добавленные файлы

| Файл | Назначение |
|------|------------|
| `bot/services/s3_service.py` | Сервис для взаимодействия с S3 (загрузка, получение URL). |
| `docker-compose.yml` (добавлены сервисы) | `minio` – объектный сервер; `minio-init` – инициализация bucket при старте. |
| (файлы конфигурации) | Переменные в `.env` для подключения к MinIO. |

### Изменения в существующих файлах

#### `config.py`
Добавлены параметры для подключения к S3:
```python
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'minioadmin')
S3_BUCKET = os.getenv('S3_BUCKET', 'dating-photos')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')
S3_USE_SSL = os.getenv('S3_USE_SSL', 'false').lower() == 'true'
```

#### `bot/models/photo.py`
Поле `file_id` полностью удалено, оставлено только `s3_key` (строка 512 символов). Модель теперь содержит только:
```python
s3_key = Column(String(512), nullable=False)
```

#### Хендлеры загрузки фото
- `bot/handlers/registration.py` – функция `ask_photo`:
  - Скачивает файл из Telegram, загружает его в S3 через `S3Service`, сохраняет `s3_key` в `context.user_data`. Поле `file_id` не используется.
- `bot/handlers/edit_profile.py` – функция `process_photo`:
  - Аналогично загружает новое фото в S3, удаляет старые фото из БД и создаёт новую запись с `s3_key`.

#### Хендлеры отображения анкет
- `bot/handlers/start.py` – функция `my_profile`:
  - Отправляет фото, используя `s3_key` через `S3Service.get_photo_url`. Если URL недоступен, отправляет только текст.
- `bot/handlers/feed.py` – функция `show_next_profile`:
  - Аналогично отправляет фото по S3-ссылке.

#### Функция сохранения профиля
- `bot/handlers/registration.py` – `save_profile`:
  - При создании записи `Photo` сохраняет только `s3_key`.

#### Модели и сервисы
- В `bot/models/photo.py` удалено поле `file_id` и все ссылки на него.
- В `bot/services/s3_service.py` реализованы методы `upload_photo` и `get_photo_url` с поддержкой как MinIO, так и реального AWS S3 (через подписанные URL).

### Использованные библиотеки
- **boto3** – официальный AWS SDK для работы с S3 (добавлен в `requirements.txt`).

### Новые сервисы в `docker-compose.yml`
- **minio**: образ `minio/minio:latest`, порты 9000 (API) и 9001 (консоль), команда `server /data --console-address ":9001"`.
- **minio-init**: образ `minio/mc:latest`, однократный запуск для создания bucket `dating-photos` и установки публичного доступа.

### Переменные окружения
Добавлены в `.env`:
```
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=dating-photos
S3_REGION=us-east-1
S3_USE_SSL=false
```

---

## 3. Система мониторинга (Prometheus + Grafana)

### Цель
Собирать метрики работы бота (количество активных пользователей, лайков, мэтчей, время ответа API) и визуализировать их.

### Добавленные файлы

| Файл | Назначение |
|------|------------|
| `bot/metrics.py` | Определение метрик (Gauge, Counter, Histogram), декоратор для измерения времени выполнения, запуск HTTP-сервера для экспорта метрик. |
| `prometheus.yml` | Конфигурация Prometheus для сбора метрик с бота (target `bot:8000`). |
| `grafana/provisioning/datasources/prometheus.yaml` | Автоматическое добавление источника данных Prometheus в Grafana. |
| `grafana/provisioning/dashboards/default.yaml` | Настройка provisioning дашбордов из файлов. |
| `grafana/dashboards/dating-bot-dashboard.json` | Готовый дашборд с панелями для активных пользователей, лайков, мэтчей и времени ответа. |

### Изменения в существующих файлах

#### `config.py`
Добавлен параметр:
```python
METRICS_PORT = int(os.getenv('METRICS_PORT', 8000))
```

#### `bot.py`
- Импортирован `init_metrics` из `bot.metrics` и вызван в `main()` для запуска HTTP-сервера метрик на порту 8000.

#### Хендлеры
- `bot/handlers/feed.py`:
  - При лайке инкрементируется метрика `total_likes`.
  - В `MatchingService` при создании мэтча инкрементируется `total_matches`.
- `bot/tasks.py`:
  - Добавлена периодическая задача `update_active_users_metric` для обновления Gauge `active_users` (запускается Celery Beat каждую минуту).

#### `celery_config.py`
Добавлен `beat_schedule` для задачи обновления активных пользователей.

#### `docker-compose.yml`
Добавлены сервисы:
- **prometheus** – сбор метрик с бота, порт 9090.
- **grafana** – визуализация, порт 3000, с монтированием provisioning и дашбордов.

### Использованные библиотеки
- **prometheus-client** – для создания и экспорта метрик (добавлен в `requirements.txt`).

### Переменные окружения
Добавлена в `.env`:
```
METRICS_PORT=8000
```

---

## 4. CI/CD (GitHub Actions)

### Цель
Автоматизировать проверку качества кода (запуск тестов) и деплой приложения на сервер.

### Добавленный файл
- `.github/workflows/ci.yml` – конфигурация пайплайна, состоящего из трёх этапов:
  1. **test** – установка зависимостей, запуск тестов с покрытием, загрузка отчёта в Codecov.
  2. **build-and-push** – сборка Docker-образа и публикация в Docker Hub (только при пуше в `main`).
  3. **deploy** – обновление контейнеров на сервере через SSH (только при пуше в `main`).

### Использованные технологии
- GitHub Actions (встроенный CI/CD).
- Docker Buildx для сборки образов.
- Docker Hub для хранения образов.

### Секреты, требуемые для работы
- `DOCKER_USERNAME`, `DOCKER_PASSWORD` – для авторизации в Docker Hub.
- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` – для доступа к серверу по SSH.

---

## 5. Модульные тесты

### Цель
Покрыть ключевую бизнес-логику тестами для предотвращения регрессий и обеспечения стабильности.

### Добавленные файлы

| Файл | Назначение |
|------|------------|
| `tests/conftest.py` | Фикстуры: `db_session` (in-memory SQLite), `fake_redis` (подмена Redis), `sample_user`, `sample_profile`. |
| `tests/test_user_service.py` | Тесты для `UserService`. |
| `tests/test_ranking_service.py` | Тесты для `RankingService`. |
| `tests/test_matching_service.py` | Тесты для `MatchingService`. |
| `tests/test_cache_service.py` | Тесты для `CacheService`. |
| `tests/test_s3_service.py` | Тесты для `S3Service` с использованием `moto` (мок S3). |
| `pytest.ini` | Настройка pytest (добавление корневой директории в `sys.path` для корректного импорта модулей). |

### Особенности реализации
- Для тестов используется in-memory SQLite с включёнными внешними ключами.
- Redis подменяется на `fakeredis.FakeRedis`.
- S3-запросы подменяются через `moto.mock_aws`, чтобы не обращаться к реальному MinIO.

### Использованные библиотеки
- **pytest**, **pytest-cov** – запуск тестов и измерение покрытия.
- **fakeredis** – эмуляция Redis.
- **moto** – эмуляция AWS S3.

### Интеграция в CI
В этапе `test` пайплайна выполняются все тесты с измерением покрытия, и результат загружается в Codecov (опционально).

---

## 6. Новые и обновлённые зависимости

`requirements.txt` дополнен следующими пакетами:

```
boto3                    # для работы с S3
prometheus-client        # для метрик
pytest                   # тестирование
pytest-cov               # покрытие тестами
fakeredis                # эмуляция Redis в тестах
moto                     # эмуляция S3 в тестах
```

---

## 7. Изменения в инфраструктуре (Docker Compose)

### Добавленные сервисы

| Сервис | Образ | Порты | Назначение |
|--------|-------|-------|------------|
| `minio` | `minio/minio:latest` | 9000, 9001 | S3-сервер |
| `minio-init` | `minio/mc:latest` | – | Создание bucket при старте |
| `prometheus` | `prom/prometheus:latest` | 9090 | Сбор метрик |
| `grafana` | `grafana/grafana:latest` | 3000 | Визуализация |

### Обновлённые сервисы
- В сервис `bot` добавлен проброс порта `8000:8000` для экспорта метрик.
- В сервис `grafana` добавлены тома для provisioning и дашбордов.

---

## 8. Итог

Все три направления (S3, мониторинг, CI/CD и тесты) полностью интегрированы в проект и готовы к использованию. Разработка велась с учётом обратной совместимости и последующего масштабирования. Инфраструктура описана в `docker-compose.yml`, все настройки вынесены в `.env`, а тесты запускаются автоматически при каждом пуше.

Благодаря этим улучшениям проект соответствует современным стандартам разработки, обеспечивает надёжное хранение данных, прозрачность работы и высокое качество кода.