# 🔒 Poprawki Bezpieczeństwa - DO NATYCHMIASTOWEGO WDROŻENIA

## 1. Zaktualizowany app.py z zabezpieczeniami

```python
import os
import secrets
from datetime import datetime, date, timedelta
from pathlib import Path
from functools import wraps
from sqlalchemy.orm import joinedload

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.security import generate_password_hash, check_password_hash
import logging

from models import db, User, Car, Reservation, ForumTopic, ForumPost, ChatMessage

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # BEZPIECZEŃSTWO: Generowanie SECRET_KEY
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Konfiguracja bazy danych
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////app/data/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # BEZPIECZEŃSTWO: Konfiguracja sesji
    app.config.update(
        SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',  # HTTPS w produkcji
        SESSION_COOKIE_HTTPONLY=True,  # Niedostępne dla JS
        SESSION_COOKIE_SAMESITE='Strict',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # Timeout sesji
    )

    # Inicjalizacja rozszerzeń
    db.init_app(app)

    # CSRF Protection
    csrf = CSRFProtect(app)

    # Rate Limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

    # Security Headers (tylko w produkcji)
    if os.environ.get('FLASK_ENV') == 'production':
        Talisman(app,
            force_https=True,
            strict_transport_security=True,
            content_security_policy={
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline'",  # Dla inline JS (lepiej byłoby usunąć)
                'style-src': "'self' 'unsafe-inline'",   # Dla inline CSS
            }
        )

    # Login Manager
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.session_protection = "strong"  # Dodatkowa ochrona sesji
    login_manager.init_app(app)

    # ... reszta kodu bez zmian ...

    # NOWY ENDPOINT: Health check dla AWS
    @app.route('/health')
    def health_check():
        try:
            # Sprawdź połączenie z bazą
            db.session.execute('SELECT 1')
            return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

    # ZABEZPIECZENIE: Rate limiting na login
    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute")  # Max 5 prób logowania na minutę
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            # Logowanie prób logowania
            logger.info(f"Login attempt for email: {email} from IP: {request.remote_addr}")

            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user, remember=False)  # Nie używaj "remember me" domyślnie
                session.permanent = True  # Ustaw timeout
                logger.info(f"Successful login for user: {email}")
                flash("Zalogowano.", "success")
                return redirect(url_for("index"))

            logger.warning(f"Failed login attempt for email: {email}")
            flash("Błędny e-mail lub hasło.", "error")
        return render_template("login.html")

    # ... reszta endpointów ...

    return app
```

## 2. Nowe wymagania - requirements.txt

```txt
Flask==3.0.3
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.2.1
Flask-Limiter==3.5.0
Flask-Talisman==1.1.0
psycopg2==2.9.9
python-dotenv==1.0.0
gunicorn==21.2.0
```

## 3. Plik .env.example

```bash
# Application
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-min-32-chars

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bsiaw

# AWS (dla produkcji)
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET=bsiaw-static-files

# Security
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
RATE_LIMIT_ENABLED=true

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn-optional
```

## 4. Walidacja danych wejściowych

```python
# utils/validators.py
import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError

def validate_safe_input(form, field):
    """Sprawdza czy input nie zawiera niebezpiecznych znaków"""
    dangerous_patterns = ['<script', 'javascript:', 'onclick', 'onerror', 'onload']
    if any(pattern in field.data.lower() for pattern in dangerous_patterns):
        raise ValidationError('Niedozwolone znaki w polu')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=8)])

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Imię', validators=[DataRequired(), Length(min=2, max=120), validate_safe_input])
    password = PasswordField('Hasło', validators=[
        DataRequired(),
        Length(min=8, message='Hasło musi mieć minimum 8 znaków')
    ])

class ReservationForm(FlaskForm):
    start_date = DateField('Data rozpoczęcia', validators=[DataRequired()])
    end_date = DateField('Data zakończenia', validators=[DataRequired()])

    def validate_end_date(form, field):
        if field.data <= form.start_date.data:
            raise ValidationError('Data zakończenia musi być po dacie rozpoczęcia')
```

## 5. Nginx config dla produkcji

```nginx
# config/nginx.conf
server {
    listen 80;
    server_name your-domain.com;

    # Przekierowanie na HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (from Let's Encrypt or AWS ACM)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    location /login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static {
        alias /app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 6. Docker-compose dla produkcji

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn --workers 4 --bind 0.0.0.0:8000 "app:create_app()"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    networks:
      - app-network
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    volumes:
      - ./config/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./static:/app/static
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
    networks:
      - app-network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    networks:
      - app-network
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## 7. Gunicorn config

```python
# config/gunicorn.conf.py
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'bsiaw_app'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None
```

## 8. GitHub Actions CI/CD

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, development]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov bandit safety

    - name: Run tests
      run: pytest tests/ --cov=app --cov-report=xml

    - name: Security scan - Bandit
      run: bandit -r app.py models.py

    - name: Dependency check - Safety
      run: safety check --json

    - name: SonarCloud Scan
      uses: SonarSource/sonarcloud-github-action@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: eu-central-1

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-get-login@v1

    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: bsiaw-app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
```

## PRIORYTET - CO ZROBIĆ NAJPIERW:

1. ✅ Dodaj `Flask-WTF` i `Flask-Limiter` do requirements.txt
2. ✅ Utwórz `.env` file z SECRET_KEY (używaj `secrets.token_hex(32)` do wygenerowania)
3. ✅ Dodaj CSRF protection do app.py
4. ✅ Dodaj rate limiting na endpoint `/login`
5. ✅ Dodaj `/health` endpoint dla load balancera
6. ✅ Skonfiguruj secure cookies
7. ✅ Dodaj logging

Te zmiany zabezpieczą aplikację przed:
- CSRF attacks
- Brute force na login
- Session hijacking
- XSS attacks
- Clickjacking
- Information disclosure

Po wdrożeniu tych zmian możecie zacząć pracę nad deploymentem na AWS!