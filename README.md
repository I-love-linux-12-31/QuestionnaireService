# Questionnaire Service
**[README on Russian 🇷🇺](https://github.com/I-love-linux-12-31/QuestionnaireService/blob/master/docs/README_RU.md)**
## About project:
Web-app for online surveys.

## How to launch

Example of .env file:
```dotenv
# Database Configuration
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

# Application Configuration
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Development Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000

```

### dev-mode

```bash
# Create .env file first!
DOTENV=1 python3 app.py
```

### docker

```bash
docker-compose up
```

## Technologies:
* python3
* Flask
  * flask-login
  * flask_jwt_extended
  * flask_swagger_ui
* SQLAlchemy
* sqlite3, mariadb, mysql (Different types of DB supported)
* OpenAPI(swagger) docs
* JS (For front-end)
* pytest (For automated testing)


## Docs generation

To setup docs using doxygen run:
```bash
doxygen
# To open documentation
xdg-open ./docs/html/index.html
```

## Tests

To run automated tests:

```bash
# Run all tests
python -m pytest tests/

# Run with coverage report
python -m pytest --cov=. tests/
```

See [Tests README](tests/README.md) for more details on testing.

## API Documentation



### Authentication

The API uses JWT (JSON Web Token) authentication. To access protected endpoints, you need to include an Authorization header with a valid JWT token.

#### Getting a Token

```
POST /api/token
```

Request body:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciO...",
  "refresh_token": "eyJhbGciO...",
  "user_id": 1,
  "username": "your_username",
  "is_admin": false
}
```

#### Refreshing a Token

```
POST /api/refresh
```

Headers:
```
Authorization: Bearer your_refresh_token
```

Response:
```json
{
  "access_token": "eyJhbGciO..."
}
```

### API Endpoints

#### Users (Admin only)

- `GET /api/users` - Get all users
- `GET /api/users/{id}` - Get user by ID
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

#### Surveys

- `GET /api/surveys` - Get all surveys
- `GET /api/surveys/{id}` - Get survey by ID
- `POST /api/surveys` - Create a new survey
- `PUT /api/surveys/{id}` - Update survey (only by author or admin)
- `DELETE /api/surveys/{id}` - Delete survey (only by author or admin)

#### Answers

- `GET /api/answers` - Get answers (filtered by access rights)
- `GET /api/answers/{id}` - Get answer by ID (access restricted)
- `PUT /api/answers/{id}` - Update answer (access restricted)
- `DELETE /api/answers/{id}` - Delete answer (access restricted)

### Access Control

- Only admins can manage user data
- Users can only access their own answers
- Survey authors can read answers to their surveys, but cannot modify them
- Admins have full access to all data

