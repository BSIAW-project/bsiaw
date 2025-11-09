# Plan Projektu BSIAW - System Wypożyczalni Samochodów

## 📋 Status Projektu
- **Aplikacja:** Flask + PostgreSQL (Docker)
- **Funkcjonalności:** ✅ Logowanie, ✅ Forum, ✅ Chat, ✅ Rezerwacje, ✅ Panel admina
- **Stan:** Działająca aplikacja lokalna w Docker

---

## 🎯 Plan Działania

### L1-L2: Podstawowa funkcjonalność ✅ UKOŃCZONE
- [x] Aplikacja z logowaniem i sesją
- [x] Forum i chat
- [x] Baza danych PostgreSQL
- [x] Docker i docker-compose

### L3: Architektura Cloud AWS (DO ZROBIENIA)
#### Komponenty do wdrożenia:
1. **Load Balancer (ALB)**
   - Application Load Balancer z Auto Scaling Group
   - Minimum 2 instancje EC2 w różnych AZ

2. **Baza danych**
   - RDS PostgreSQL (Multi-AZ dla wysokiej dostępności)
   - Lub Aurora PostgreSQL Serverless

3. **Domena i SSL**
   - Route 53 dla domeny
   - Certyfikat SSL z AWS Certificate Manager
   - Terminacja SSL na Load Balancerze

4. **Architektura docelowa:**
```
Internet → Route53 → CloudFront → ALB (SSL) → EC2 (Auto Scaling) → RDS
                         ↓
                     S3 (static files)
```

### L4: Implementacja w AWS
#### Kroki implementacji:
1. **Przygotowanie kodu:**
   - Zmiana konfiguracji na zmienne środowiskowe
   - Separacja plików statycznych (S3)
   - Health check endpoint

2. **Terraform/CloudFormation:**
   - Infrastruktura jako kod
   - VPC, Subnets, Security Groups
   - EC2 Launch Template
   - RDS instance

3. **Deployment:**
   - ECR dla obrazów Docker
   - ECS/Fargate lub EC2 z docker-compose

### L5: CI/CD Pipeline
#### GitHub Actions / AWS CodePipeline:
```yaml
Stages:
1. Source (GitHub)
2. Build (Docker build)
3. Test (Unit tests, Integration tests)
4. Security Scan (Trivy, Snyk)
5. Deploy to Staging
6. Manual Approval
7. Deploy to Production
```

### L6: Bezpieczeństwo CI/CD
- **SAST:** SonarQube, Bandit (Python)
- **DAST:** OWASP ZAP
- **Container Scan:** Trivy, Clair
- **Secrets Management:** AWS Secrets Manager
- **Pipeline Security:** Branch protection, signed commits

### L7: Bezpieczeństwo Aplikacji
#### Do implementacji w kodzie:
1. **Sesje:**
   - Session timeout
   - Secure cookies (httponly, secure, samesite)
   - CSRF tokens

2. **Headers:**
   - CSP (Content Security Policy)
   - X-Frame-Options
   - X-Content-Type-Options

3. **Infrastruktura:**
   - AWS WAF
   - CloudFront (CDN + DDoS protection)
   - AWS Shield

### L8: Hardening
- **EC2:** CIS Amazon Linux 2 Benchmark
- **RDS:** Szyfrowanie, backup, monitoring
- **Network:** Security Groups, NACLs
- **IAM:** Principle of least privilege

### L9: Testy
1. **Testy aplikacji:**
   - pytest dla unit tests
   - OWASP ZAP dla security testing
   - Burp Suite dla penetration testing

2. **Testy infrastruktury:**
   - AWS Security Hub
   - Prowler
   - ScoutSuite

---

## 🔧 DO NATYCHMIASTOWEJ POPRAWY

### Krytyczne (Bezpieczeństwo):
```python
# 1. app.py:17 - Zmienić SECRET_KEY
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
# POPRAWKA: Generować losowy klucz, nie używać domyślnego

# 2. Dodać CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# 3. Dodać session timeout
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# 4. Secure cookie config
app.config.update(
    SESSION_COOKIE_SECURE=True,  # tylko HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict'
)
```

### Ważne (Funkcjonalność):
1. **Health check endpoint:**
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200
```

2. **Logging:**
```python
import logging
logging.basicConfig(level=logging.INFO)
```

3. **Rate limiting:**
```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: get_remote_address())
```

4. **Input validation** - dodać walidację wszystkich formularzy

5. **SQL Injection** - sprawdzić czy SQLAlchemy wszędzie używa parametryzowanych zapytań

### Konfiguracja dla AWS:
1. **Environment variables:**
```python
# .env.example
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/dbname
SECRET_KEY=generate-random-key-here
FLASK_ENV=production
AWS_REGION=eu-central-1
S3_BUCKET=my-static-files
```

2. **Dockerfile optymalizacja:**
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
# ... build dependencies ...

FROM python:3.11-slim
# ... tylko runtime ...
```

3. **Requirements rozdzielenie:**
```
requirements.txt         # produkcja
requirements-dev.txt    # development
```

---

## 📁 Struktura plików do utworzenia:

```
bsiaw/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── scripts/
│       ├── deploy.sh
│       └── health_check.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── config/
│   ├── nginx.conf
│   └── gunicorn.conf.py
├── .env.example
├── security-headers.py
└── requirements-dev.txt
```

---

## 📅 Harmonogram

| Tydzień | Zadanie | Odpowiedzialny |
|---------|---------|----------------|
| 1 | Poprawa bezpieczeństwa kodu | Wszyscy |
| 2 | Setup AWS + Terraform | Osoba 1 |
| 2 | CI/CD Pipeline | Osoba 2 |
| 3 | Security scanning | Osoba 3 |
| 3 | Testy i dokumentacja | Osoba 4 |
| 4 | Wdrożenie i prezentacja | Wszyscy |

---

## 📝 Dokumentacja do przygotowania

1. **Sprawozdania (max 1 strona/lab):**
   - L1-L2: Opis aplikacji i funkcjonalności
   - L3: Schemat architektury AWS
   - L4: Screenshot działającej aplikacji w chmurze
   - L5: Diagram pipeline CI/CD
   - L6: Raport z security scanning
   - L7: Lista zabezpieczeń
   - L8: Checklist hardening
   - L9: Wyniki testów

2. **Dokumentacja projektowa (max 3 strony):**
   - Architektura (diagram)
   - Technologie bezpieczeństwa
   - Instrukcja deployment

3. **Prezentacja (20-30 min):**
   - Demo aplikacji (5 min)
   - Architektura (5 min)
   - Security (10 min)
   - Q&A (5-10 min)

---

## ⚠️ PRIORYTET 1 - DO ZROBIENIA TERAZ

1. **Utworzyć repozytorium GitHub** (prywatne)
2. **Poprawić bezpieczeństwo:**
   - SECRET_KEY z environment variable
   - CSRF protection
   - Security headers
3. **Dodać .env.example** z wszystkimi zmiennymi
4. **Utworzyć branch 'development'** dla pracy
5. **Zacząć pisać testy** (pytest)

---

## 🎯 Cele na następne zajęcia

- [ ] Działające repo na GitHub
- [ ] Poprawione bezpieczeństwo podstawowe
- [ ] Plan architektury AWS (diagram)
- [ ] Wybór usług AWS (EC2 vs ECS vs Fargate)
- [ ] Konto AWS z credits studenckie
