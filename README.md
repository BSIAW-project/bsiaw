# Wypożyczalnia Samochodów — prosta aplikacja (Flask) z logowaniem, forum i chatem (Docker)

**Funkcje**:
- Logowanie/rejestracja (sesje) — `Flask-Login`
- Interakcje użytkowników:
  - Forum (tematy + posty/komentarze)
  - Chat (globalny pokój, odświeżanie co 2s)
- Baza danych: SQLite (plik w wolumenie Dockera)
- Uruchamianie przez Docker + docker-compose

## Szybki start

1. Zbuduj i uruchom:
   ```bash
   docker compose up --build
   ```
2. Aplikacja będzie dostępna na: http://localhost:8000
3. Dane startowe:
   - Użytkownik administrator: `admin@example.com` / hasło: `admin123`
   - Kilka przykładowych samochodów

## Struktura
```text
car_rental_app/
├─ app.py                    # główna aplikacja Flask
├─ models.py                
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ data/                    
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  ├─ login.html
│  ├─ register.html
│  ├─ cars.html
│  ├─ forum.html
│  ├─ forum_topic.html
│  └─ chat.html
└─ static/
   └─ style.css
```

## Przydatne komendy

- (opcjonalnie) Wyczyść wolumen (reset bazy danych):
  ```bash
  docker compose down
  rm -rf data/
  docker compose up --build
  ```

## Notatki bezpieczeństwa (skrót)
Ta aplikacja jest **demo**. W realnym projekcie dodaj:
- CSRF (np. Flask-WTF/Flask-SeaSurf),
- walidacje formularzy,
- lepsze zarządzanie hasłami i reset hasła,
- produkcyjny serwer (np. gunicorn + reverse proxy),
- testy i logowanie zdarzeń.
