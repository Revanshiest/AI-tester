# Конфигурация AI-tester

Подробное руководство по настройке и конфигурации системы AI-tester.

## 🔧 Переменные окружения

### Обязательные переменные

#### `TELEGRAM_BOT_TOKEN`
**Описание:** Токен вашего Telegram бота, полученный от @BotFather.

**Формат:** Строка вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

**Получение токена:**
1. Откройте чат с [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

**Пример:**
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
```

### Опциональные переменные

#### `OLLAMA_HOST`
**Описание:** URL сервера Ollama для подключения.

**По умолчанию:** `http://127.0.0.1:11434`

**Возможные значения:**
- `http://127.0.0.1:11434` - локальный сервер (по умолчанию)
- `http://localhost:11434` - альтернативный локальный адрес
- `http://192.168.1.100:11434` - удаленный сервер в локальной сети
- `https://ollama.example.com` - удаленный сервер с SSL

**Пример:**
```env
OLLAMA_HOST=http://192.168.1.100:11434
```

## 📁 Файл конфигурации .env

Создайте файл `.env` в корневой директории проекта:

```env
# Обязательные настройки
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Опциональные настройки
OLLAMA_HOST=http://127.0.0.1:11434
```

### Безопасность .env файла

**⚠️ Важно:** Никогда не коммитьте файл `.env` в репозиторий!

Убедитесь, что `.env` добавлен в `.gitignore`:
```gitignore
.env
.env.local
.env.*.local
```

## ⚙️ Константы приложения

Константы настраиваются в файле `src/constants.py`:

### `MAX_TELEGRAM_CHUNK`
**Описание:** Максимальный размер сообщения для отправки в Telegram.

**Значение по умолчанию:** `3800`

**Причина ограничения:** Telegram имеет лимит на размер сообщения (4096 символов). Оставляем запас для форматирования.

**Рекомендации:**
- Не увеличивайте без необходимости
- При увеличении проверьте стабильность работы
- Учитывайте производительность при отправке больших сообщений

### `MAX_HISTORY_MESSAGES`
**Описание:** Максимальное количество сообщений в истории диалога на пользователя.

**Значение по умолчанию:** `20`

**Влияние на производительность:**
- Больше сообщений = больше памяти на пользователя
- Больше сообщений = больше данных в запросе к модели
- Больше сообщений = медленнее обработка

**Рекомендации:**
- Для простых задач: 10-20 сообщений
- Для сложных диалогов: 30-50 сообщений
- Для серверов с ограниченной памятью: 10-15 сообщений

### `INACTIVITY_TIMEOUT_SECONDS`
**Описание:** Время неактивности в секундах до автоматического завершения сессии.

**Значение по умолчанию:** `600` (10 минут)

**Влияние на ресурсы:**
- Меньше времени = быстрее освобождение моделей
- Больше времени = больше потребление памяти
- Слишком мало = неудобство для пользователей

**Рекомендации:**
- Для тестирования: 300-600 секунд (5-10 минут)
- Для продакшена: 600-1800 секунд (10-30 минут)
- Для серверов с ограниченной памятью: 300-600 секунд

## 🐳 Конфигурация Ollama

### Базовые настройки Ollama

#### Запуск сервера
```bash
# Стандартный запуск
ollama serve

# Запуск на другом порту
OLLAMA_HOST=0.0.0.0:11435 ollama serve

# Запуск с логированием
ollama serve --verbose
```

#### Переменные окружения Ollama
```bash
# Хост для привязки (по умолчанию: 127.0.0.1)
OLLAMA_HOST=0.0.0.0:11434

# Путь к моделям
OLLAMA_MODELS=/path/to/models

# Уровень логирования
OLLAMA_DEBUG=1
```

### Настройка моделей

#### Установка популярных моделей
```bash
# Llama 2 (7B параметров)
ollama pull llama2:7b

# Llama 2 (13B параметров)
ollama pull llama2:13b

# Code Llama
ollama pull codellama:7b

# Mistral
ollama pull mistral:7b

# Neural Chat
ollama pull neural-chat:7b
```

#### Проверка установленных моделей
```bash
ollama list
```

#### Удаление моделей
```bash
ollama rm model_name
```

## 🔒 Настройки безопасности

### Telegram Bot Security

#### Ограничение доступа
1. Создайте приватного бота через @BotFather
2. Отключите групповые чаты в настройках бота
3. Используйте команду `/setprivacy` для ограничения команд

#### Команды безопасности:
```
/setprivacy - настройка приватности
/setcommands - настройка списка команд
/setdescription - описание бота
/setabouttext - информация о боте
```

### Ollama Security

#### Сетевая безопасность
```bash
# Запуск только на localhost (по умолчанию)
ollama serve

# Запуск на всех интерфейсах (только в доверенной сети)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Запуск с аутентификацией (если поддерживается)
OLLAMA_AUTH=username:password ollama serve
```

#### Firewall настройки
```bash
# Разрешить только локальные подключения
iptables -A INPUT -p tcp --dport 11434 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 11434 -j DROP

# Разрешить подключения из локальной сети
iptables -A INPUT -p tcp --dport 11434 -s 192.168.1.0/24 -j ACCEPT
```

## 📊 Мониторинг и логирование

### Логирование приложения

#### Настройка уровней логирования
```python
import logging

# В app.py добавьте:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai-tester.log'),
        logging.StreamHandler()
    ]
)
```

#### Логирование Ollama
```bash
# Запуск с подробным логированием
OLLAMA_DEBUG=1 ollama serve

# Логи в файл
OLLAMA_DEBUG=1 ollama serve 2>&1 | tee ollama.log
```

### Мониторинг ресурсов

#### Мониторинг памяти
```bash
# Проверка использования памяти Ollama
ps aux | grep ollama

# Мониторинг в реальном времени
htop | grep ollama
```

#### Мониторинг моделей
```bash
# Список загруженных моделей
ollama ps

# Информация о модели
ollama show model_name
```

## 🚀 Производительность

### Оптимизация Ollama

#### Настройки GPU
```bash
# Проверка доступности GPU
nvidia-smi

# Запуск с GPU (если доступно)
CUDA_VISIBLE_DEVICES=0 ollama serve
```

#### Настройки памяти
```bash
# Ограничение использования памяти
OLLAMA_MAX_LOADED_MODELS=2 ollama serve

# Очистка неиспользуемых моделей
ollama ps
ollama stop model_name
```

### Оптимизация бота

#### Настройки Telegram
```python
# В app.py можно добавить:
application = ApplicationBuilder().token(token).build()

# Настройки для больших нагрузок
application = ApplicationBuilder().token(token)\
    .concurrent_updates(True)\
    .build()
```

## 🔧 Troubleshooting

### Частые проблемы

#### Ollama недоступна
```bash
# Проверка статуса
curl http://127.0.0.1:11434/api/version

# Перезапуск Ollama
pkill ollama
ollama serve
```

#### Модель не загружается
```bash
# Проверка доступности модели
ollama list

# Принудительная загрузка
ollama pull model_name

# Проверка логов
ollama logs model_name
```

#### Ошибки Telegram
```bash
# Проверка токена
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверка webhook (если используется)
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### Диагностические команды

#### Проверка конфигурации
```python
# В Python консоли:
from src.ollama_client import ping_ollama, list_ollama_models
print("Ollama status:", ping_ollama())
print("Available models:", list_ollama_models())
```

#### Тестирование подключений
```bash
# Тест Ollama API
curl -X POST http://127.0.0.1:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2:7b", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 📋 Чек-лист конфигурации

### Перед запуском
- [ ] Ollama установлена и запущена
- [ ] Модели загружены (`ollama list`)
- [ ] Telegram бот создан и токен получен
- [ ] Файл `.env` создан с правильными настройками
- [ ] Зависимости Python установлены
- [ ] Порты 11434 (Ollama) и 443/80 (Telegram) доступны

### После запуска
- [ ] Бот отвечает на `/start`
- [ ] Команда `/pingollama` работает
- [ ] Команда `/omodels` показывает модели
- [ ] Можно выбрать модель и начать диалог
- [ ] Логи не содержат ошибок

### Мониторинг
- [ ] Настроено логирование
- [ ] Мониторинг использования ресурсов
- [ ] Проверка доступности сервисов
- [ ] Резервное копирование конфигурации
