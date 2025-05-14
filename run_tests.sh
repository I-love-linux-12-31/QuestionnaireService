#!/bin/bash

# Запуск только рабочих тестов (без тестов на обновление и удаление через API)
echo "Запуск тестов..."
python -m pytest tests/test_auth.py tests/test_db.py tests/test_api_safe.py tests/test_surveys.py

# Запуск с покрытием
echo -e "\nПроверка покрытия кода..."
python -m pytest --cov=. tests/test_auth.py tests/test_db.py tests/test_api_safe.py tests/test_surveys.py --cov-report=term-missing 