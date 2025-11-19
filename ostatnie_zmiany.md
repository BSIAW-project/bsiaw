MEGA SKROT

Funkcjonalność	    Plik	Linie
Walidacja hasła	    app.py	78-89
Sesja 6 minut	    app.py	39
Hasło admina	    app.py	417
Security code pole	models.py	13
Generowanie kodu	models.py	21-24
Rejestracja z kodem	app.py	94-100
Forgot password	    app.py	~121-159
Migracja	        app.py	356-370
Link reset	        login.html	10
NOWY: Success page	    register_success.html	-
NOWY: Forgot page	    forgot_password.html	-
\

TU TROCHE DOKLADNIEJ


🔐 1. Walidacja hasła przy rejestracji
Plik: 
/home/kali/bsiaw/app.py
Funkcja: 
register()
 (linie 78-89)

Dodane zasady:
python
# Minimalna długość
if len(password) < 12:
    flash("Hasło musi mieć co najmniej 12 znaków.", "error")

# Wielka litera
if not re.search(r"[A-Z]", password):
    flash("Hasło musi zawierać co najmniej jedną wielką literę.", "error")

# Mała litera  
if not re.search(r"[a-z]", password):
    flash("Hasło musi zawierać co najmniej jedną małą literę.", "error")

# Znak specjalny
if not re.search(r"[^A-Za-z0-9]", password):
    flash("Hasło musi zawierać co najmniej jeden znak specjalny.", "error")
Wymagania hasła:
✅ Minimum 12 znaków
✅ Co najmniej 1 wielka litera (A-Z)
✅ Co najmniej 1 mała litera (a-z)
✅ Co najmniej 1 znak specjalny (np. !@#$%^&)
Import wymagany: import re (linia 3)

⏱️ 2. Skrócenie czasu trwania sesji cookie
Plik: 
/home/kali/bsiaw/app.py
Linia: 39

Zmiana:
python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=6)
Szczegóły:
Przed: Domyślnie sesja trwała 31 dni
Po: Sesja trwa 6 minut
Użytkownik musi ustawić session.permanent = True przy logowaniu (linia 110)
Po 6 minutach nieaktywności użytkownik zostanie automatycznie wylogowany
Import wymagany: from datetime import timedelta (linia 15)

🛡️ 3. Zmiana hasła administratora
Plik: 
/home/kali/bsiaw/app.py
Funkcja: 
seed()
 (linia 417)

Zmiana:
python
# PRZED:
password_hash=generate_password_hash("admin123")

# PO:
admin_password = "Admin123!@#$"
password_hash=generate_password_hash(admin_password)
Nowe hasło admina: Admin123!@#$

Spełnia wszystkie wymagania (12 znaków, wielkie/małe litery, znaki specjalne)
📊 Podsumowanie zmian:
Funkcjonalność	Plik	Linie	Opis
Walidacja długości hasła	
app.py
78-79	Min. 12 znaków
Walidacja wielkiej litery	
app.py
81-83	Minimum 1x A-Z
Walidacja małej litery	
app.py
84-86	Minimum 1x a-z
Walidacja znaku specjalnego	
app.py
87-89	Minimum 1x znak specjalny
Czas sesji cookie	
app.py
39	6 minut
Hasło admina	
app.py
417	Admin123!@#$


📁 Zmodyfikowane pliki:
1. 
models.py
Import secrets
Pole security_code VARCHAR(32)
Metoda 
generate_security_code()
2. 
app.py
Rejestracja generuje kod (linie 94-100)
Nowa funkcja 
forgot_password()
 (po linii 120)
Migracja dla starych użytkowników (linie 356-370)
Admin z security code (linia 422)
3. 
login.html
Link "Zapomniałeś hasła?" (linia 10)
4. 
register_success.html
 ⭐ NOWY
Wyświetlanie security code raz
5. 
forgot_password.html
 ⭐ NOWY
Formularz resetowania (email + kod + nowe hasło)
