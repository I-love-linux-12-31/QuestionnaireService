# Questionnaire Service
## 📌 О проекте
Веб-приложение для проведения онлайн-опросов.

## 🚀 Как запустить

Пример файла ``.env``:

```dotenv
# Конфигурация базы данных
# MariaDB/MySQL
# DB_TYPE=mariadb+pymysql
# DB_USER=questionnaire_user
# DB_PASSWORD=questionnaire_password
# DB_SERVER=mariadb
# DB_PORT=3306
# DB=questionnaire_db

# Sqlite3
DB="QuestionnaireService"
DB_TYPE="sqlite3"

# Конфигурация приложения
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Параметры разработки
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
```

### 🔧 Режим разработки

```bash
# Сначала создайте .env файл!
DOTENV=1 python3 app.py
```

### 🐳 Docker

```bash
docker-compose up
```

## 🛠️ Используемые технологии
* python3
* Flask
  * flask-login
  * flask_jwt_extended
  * flask_swagger_ui
* SQLAlchemy
* sqlite3, mariadb, mysql
* OpenAPI(swagger) для документации
* JS (для фронтенда)
* pytest (для автоматического тестирования)


## 📄 Генерация документации

Для генерации документации с помощью Doxygen:
```bash
doxygen
# Открыть документацию
xdg-open ./docs/html/index.html
```

## ✅ Тесты

Для запуска тестов:

```bash
# Запустить все тесты
python -m pytest tests/

# Запустить с отчетом о покрытии
python -m pytest --cov=. tests/
```

Дополнительная информация в README по тестированию.

## 📚 API Документация



### 🔐 Аутентификация

API использует JWT (JSON Web Token) для авторизации. Для доступа к защищённым эндпоинтам необходимо передавать заголовок Authorization с действительным JWT-токеном.

#### Получение токена

```
POST /api/token
```

Тело запроса:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

Ответ:
```json
{
  "access_token": "eyJhbGciO...",
  "refresh_token": "eyJhbGciO...",
  "user_id": 1,
  "username": "your_username",
  "is_admin": false
}
```

#### Обновление токена

```
POST /api/refresh
```

Заголовки:
```
Authorization: Bearer your_refresh_token
```

Ответ:
```json
{
  "access_token": "eyJhbGciO..."
}
```

### 📌 API-эндпоинты

#### Пользователи (только для администраторов)

- `GET /api/users` – Получить список пользователей
- `GET /api/users/{id}` – Получить пользователя по ID
- `PUT /api/users/{id}` – Обновить пользователя
- `DELETE /api/users/{id}` – Удалить пользователя

#### Опросы

- `GET /api/surveys`  – Получить все опросы
- `GET /api/surveys/{id}` – Получить опрос по ID
- `POST /api/surveys` – Создать новый опрос
- `PUT /api/surveys/{id}` – Обновить опрос (только автор или админ)
- `DELETE /api/surveys/{id}` – Удалить опрос (только автор или админ)

#### Ответы

- `GET /api/answers`  – Получить ответы (в зависимости от прав доступа)
- `GET /api/answers/{id}` – Получить ответ по ID (доступ ограничен)
- `PUT /api/answers/{id}` – Обновить ответ (доступ ограничен)
- `DELETE /api/answers/{id}` – Удалить ответ (доступ ограничен)

### 🔒 Контроль доступа

- Только администраторы могут управлять данными пользователей
- Пользователи могут видеть только свои ответы
- Авторы опросов могут просматривать, но не редактировать ответы на свои опросы
- Администраторы имеют полный доступ ко всем данным
