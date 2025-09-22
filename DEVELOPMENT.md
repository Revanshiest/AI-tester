# Руководство разработчика AI-tester

Подробное руководство для разработчиков, желающих внести вклад в проект или расширить его функциональность.

## 🚀 Быстрый старт для разработчиков

### Настройка окружения разработки

1. **Клонирование и настройка:**
```bash
git clone <repository-url>
cd AI-tester
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или
.venv\Scripts\activate  # Windows
```

2. **Установка зависимостей:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # если есть dev зависимости
```

3. **Настройка переменных окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл
```

4. **Запуск в режиме разработки:**
```bash
python -m src.app
```

## 🏗 Архитектура кода

### Структура проекта
```
AI-tester/
├── src/
│   ├── __init__.py          # Инициализация пакета
│   ├── app.py              # Основное приложение
│   ├── commands.py         # Обработчики команд
│   ├── session.py          # Управление сессиями
│   ├── ollama_client.py    # Ollama API клиент
│   ├── texts.py           # Текстовые константы
│   └── constants.py       # Константы приложения
├── tests/                  # Тесты (создать)
├── docs/                   # Документация
├── requirements.txt        # Зависимости
├── .env.example           # Пример конфигурации
└── README.md              # Основная документация
```

### Принципы архитектуры

1. **Разделение ответственности** - каждый модуль отвечает за свою область
2. **Асинхронность** - использование async/await для неблокирующих операций
3. **Изоляция** - пользователи изолированы друг от друга
4. **Расширяемость** - легко добавлять новые функции
5. **Тестируемость** - код написан с учетом тестирования

## 📝 Стиль кода

### Python стиль
Следуйте PEP 8 с некоторыми исключениями:

```python
# Импорты
import os
import sys
from typing import Optional, List, Dict

# Константы
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0

# Классы
class UserSession:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.model_id: Optional[str] = None

# Функции
async def process_message(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обрабатывает входящее сообщение."""
    if not update.message:
        return
    # ... код функции
```

### Именование
- **Функции и переменные:** `snake_case`
- **Классы:** `PascalCase`
- **Константы:** `UPPER_SNAKE_CASE`
- **Приватные методы:** `_leading_underscore`

### Типизация
Всегда используйте type hints:

```python
from typing import Optional, List, Dict, Any, Union

def process_data(
    data: List[Dict[str, Any]], 
    timeout: float = 30.0
) -> Optional[Dict[str, Any]]:
    """Обрабатывает данные с таймаутом."""
    pass
```

## 🧪 Тестирование

### Структура тестов
```
tests/
├── __init__.py
├── test_commands.py        # Тесты команд
├── test_session.py         # Тесты сессий
├── test_ollama_client.py   # Тесты Ollama клиента
├── test_app.py            # Тесты приложения
└── conftest.py            # Конфигурация pytest
```

### Пример теста
```python
import pytest
from unittest.mock import Mock, patch
from src.commands import cmd_pingollama
from src.ollama_client import ping_ollama

@pytest.mark.asyncio
async def test_cmd_pingollama_success():
    """Тест успешной проверки Ollama."""
    with patch('src.commands.ping_ollama') as mock_ping:
        mock_ping.return_value = {"version": "0.1.0"}
        
        update = Mock()
        update.message = Mock()
        context = Mock()
        
        await cmd_pingollama(update, context)
        
        update.message.reply_text.assert_called_once()
        assert "Оllama доступна" in update.message.reply_text.call_args[0][0]
```

### Запуск тестов
```bash
# Все тесты
pytest

# Конкретный файл
pytest tests/test_commands.py

# С покрытием
pytest --cov=src

# С подробным выводом
pytest -v
```

## 🔧 Добавление новых функций

### 1. Добавление новой команды

#### Шаг 1: Создайте обработчик в `commands.py`
```python
async def cmd_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Описание новой команды."""
    if not update.message:
        return
    
    # Логика команды
    await update.message.reply_text("Ответ команды")
```

#### Шаг 2: Зарегистрируйте в `app.py`
```python
def main() -> None:
    # ... существующий код ...
    app.add_handler(CommandHandler("newcommand", cmd_new_command))
```

#### Шаг 3: Добавьте описание в `texts.py`
```python
NEW_COMMAND_HELP = "Описание новой команды"
```

### 2. Добавление нового параметра сессии

#### Шаг 1: Обновите `UserSession` в `session.py`
```python
@dataclass
class UserSession:
    # ... существующие поля ...
    new_parameter: str = "default_value"
```

#### Шаг 2: Добавьте команду для настройки
```python
async def cmd_setnewparam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Установка нового параметра."""
    if not update.message:
        return
    await session_manager.set_pending(update.effective_user.id, "setnewparam")
    await update.message.reply_text("Введите новое значение:")
```

#### Шаг 3: Обработайте в `handle_text`
```python
if sess.pending_action == "setnewparam":
    sess.new_parameter = text
    await session_manager.set_pending(update.effective_user.id, None)
    await update.message.reply_text(f"Новый параметр установлен: {text}")
    return
```

### 3. Добавление нового провайдера моделей

#### Создайте новый клиент
```python
# src/providers/openai_client.py
from typing import List, Dict, Any

def chat_with_openai(
    model: str,
    messages: List[Dict[str, str]],
    **kwargs
) -> Dict[str, Any]:
    """Интеграция с OpenAI API."""
    # Реализация
    pass
```

#### Адаптируйте session manager
```python
# В session.py добавьте поддержку провайдеров
@dataclass
class UserSession:
    # ... существующие поля ...
    provider: str = "ollama"  # ollama, openai, etc.
```

## 🐛 Отладка

### Логирование
```python
import logging

logger = logging.getLogger(__name__)

async def debug_function():
    logger.debug("Отладочная информация")
    logger.info("Информационное сообщение")
    logger.warning("Предупреждение")
    logger.error("Ошибка")
```

### Отладка Ollama
```python
# Проверка доступности
from src.ollama_client import ping_ollama
print("Ollama status:", ping_ollama())

# Проверка моделей
from src.ollama_client import list_ollama_models
print("Models:", list_ollama_models())
```

### Отладка сессий
```python
# Проверка состояния сессии
from src.session import session_manager
import asyncio

async def debug_session(user_id: int):
    session = await session_manager.get_status(user_id)
    print(f"Session for {user_id}: {session}")
```

## 📊 Профилирование

### Профилирование производительности
```python
import cProfile
import pstats

def profile_function():
    # Ваш код
    pass

# Запуск профилирования
cProfile.run('profile_function()', 'profile_output.prof')

# Анализ результатов
stats = pstats.Stats('profile_output.prof')
stats.sort_stats('cumulative').print_stats(10)
```

### Мониторинг памяти
```python
import tracemalloc

# Начало отслеживания
tracemalloc.start()

# Ваш код
# ...

# Анализ использования памяти
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

## 🔄 CI/CD

### GitHub Actions
Создайте `.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
```

## 📚 Документация

### Docstrings
Используйте Google style docstrings:

```python
def process_data(data: List[Dict], timeout: float = 30.0) -> Optional[Dict]:
    """Обрабатывает данные с указанным таймаутом.
    
    Args:
        data: Список словарей с данными для обработки
        timeout: Таймаут в секундах (по умолчанию 30.0)
    
    Returns:
        Словарь с результатами обработки или None при ошибке
        
    Raises:
        ValueError: Если данные некорректны
        TimeoutError: Если превышен таймаут
    """
    pass
```

### Генерация документации
```bash
# Установка Sphinx
pip install sphinx sphinx-rtd-theme

# Инициализация
sphinx-quickstart docs/

# Генерация
sphinx-build -b html docs/ docs/_build/html
```

## 🚀 Развертывание

### Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.app"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  ai-tester:
    build: .
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

## 🤝 Вклад в проект

### Процесс разработки

1. **Fork репозитория**
2. **Создайте ветку для функции:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Внесите изменения и зафиксируйте:**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```
4. **Отправьте в ваш fork:**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Создайте Pull Request**

### Code Review

#### Что проверять:
- [ ] Код соответствует стилю проекта
- [ ] Добавлены тесты для новой функциональности
- [ ] Обновлена документация
- [ ] Нет breaking changes без обоснования
- [ ] Обработка ошибок реализована корректно

#### Чек-лист для автора:
- [ ] Код протестирован локально
- [ ] Все тесты проходят
- [ ] Документация обновлена
- [ ] Commit messages информативны
- [ ] PR содержит описание изменений

## 📞 Поддержка

### Получение помощи
- Создайте issue в репозитории
- Опишите проблему подробно
- Приложите логи и конфигурацию
- Укажите версию Python и ОС

### Сообщение об ошибках
При сообщении об ошибке укажите:
1. Версию Python
2. Версию Ollama
3. Операционную систему
4. Полный traceback ошибки
5. Конфигурацию (без токенов)
6. Шаги для воспроизведения
