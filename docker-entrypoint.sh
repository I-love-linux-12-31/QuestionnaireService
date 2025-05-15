#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for MariaDB to be ready..."
python3 -c "
import sys
import time
import pymysql
import os

for _ in range(30):
    try:
        pymysql.connect(
            host=os.environ.get('DB_SERVER', 'mariadb'),
            user=os.environ.get('DB_USER', 'questionnaire_user'),
            password=os.environ.get('DB_PASSWORD', 'questionnaire_password'),
            database=os.environ.get('DB', 'questionnaire_db')
        )
        print('Database connection successful')
        sys.exit(0)
    except pymysql.Error as e:
        print(f'Waiting for database connection... {e}')
        time.sleep(2)

print('Could not connect to database after 60 seconds')
sys.exit(1)
"

# Initialize the application
echo "Starting application..."
exec "$@" 