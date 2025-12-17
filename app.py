import os
import time
import re 
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from functools import wraps
from sqlalchemy.orm import joinedload
from sqlalchemy import text

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Car, Reservation, ForumTopic, ForumPost, ChatMessage

def wait_for_db(app, max_retries=30, delay=2):
    """Wait for database to be available"""
    with app.app_context():
        for i in range(max_retries):
            try:
                # Try to execute a simple query
                db.session.execute(text('SELECT 1'))
                print(f"Database is available after {i} attempts")
                return True
            except Exception as e:
                if i == max_retries - 1:
                    print(f"Could not connect to database after {max_retries} attempts")
                    raise
                print(f"Waiting for database... (attempt {i+1}/{max_retries})")
                time.sleep(delay)
        return False


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////app/data/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=6)
    app.config['SESSION_COOKIE_SECURE'] = True 
    # Blokuje kradzież sesji przez JavaScript (ochrona XSS)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    # Chroni przed CSRF
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    if not app.debug:
        # Przekieruj logi na standardowe wyjście (dla AWS CloudWatch)
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Security Monitoring Enabled')


    db.init_app(app)

    # Konfiguracja CORS
    CORS(app, 
        resources={r"/api/*": {"origins": "https://trusted-domain.com"}}, 
        supports_credentials=True, 
        allow_headers=["Authorization"]
    )

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_admin:
                flash("Dostęp tylko dla administratora.", "error")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def index():
        cars_count = Car.query.count()
        topics_count = ForumTopic.query.count()
        messages_count = ChatMessage.query.count()
        return render_template("index.html", cars_count=cars_count, topics_count=topics_count, messages_count=messages_count)

    # ---------- Auth ----------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")

            if not email or not name or not password:
                flash("Wypełnij wszystkie pola.", "error")
                return redirect(url_for("register"))
            if len(password) < 12:
                flash("Hasło musi mieć co najmniej 12 znaków.", "error")
                return redirect(url_for("register"))
            if not re.search(r"[A-Z]", password):
                flash("Hasło musi zawierać co najmniej jedną wielką literę.", "error")
                return redirect(url_for("register"))
            if not re.search(r"[a-z]", password):
                flash("Hasło musi zawierać co najmniej jedną małą literę.", "error")
                return redirect(url_for("register"))
            if not re.search(r"[^A-Za-z0-9]", password):
                flash("Hasło musi zawierać co najmniej jeden znak specjalny.", "error")
                return redirect(url_for("register"))
            if User.query.filter_by(email=email).first():
                flash("Użytkownik o tym e-mailu już istnieje.", "error")
                return redirect(url_for("register"))

            security_code = User.generate_security_code()
            user = User(email=email, name=name, password_hash=generate_password_hash(password), security_code=security_code)
            db.session.add(user)
            db.session.commit()
            # Pass security code to template to display to user
            return render_template("register_success.html", security_code=security_code)
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                session.permanent = True
                flash("Zalogowano.", "success")
                return redirect(url_for("index"))
            flash("Błędny e-mail lub hasło.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Wylogowano.", "success")
        return redirect(url_for("index"))

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            security_code = request.form.get("security_code", "").strip().upper()
            new_password = request.form.get("new_password", "")

            if not email or not security_code or not new_password:
                flash("Wypełnij wszystkie pola.", "error")
                return redirect(url_for("forgot_password"))
            
            # Walidacja nowego hasła
            if len(new_password) < 12:
                flash("Hasło musi mieć co najmniej 12 znaków.", "error")
                return redirect(url_for("forgot_password"))
            if not re.search(r"[A-Z]", new_password):
                flash("Hasło musi zawierać co najmniej jedną wielką literę.", "error")
                return redirect(url_for("forgot_password"))
            if not re.search(r"[a-z]", new_password):
                flash("Hasło musi zawierać co najmniej jedną małą literę.", "error")
                return redirect(url_for("forgot_password"))
            if not re.search(r"[^A-Za-z0-9]", new_password):
                flash("Hasło musi zawierać co najmniej jeden znak specjalny.", "error")
                return redirect(url_for("forgot_password"))
            
            # Znajdź użytkownika i zweryfikuj kod bezpieczeństwa
            user = User.query.filter_by(email=email, security_code=security_code).first()
            if not user:
                flash("Nieprawidłowy e-mail lub kod bezpieczeństwa.", "error")
                return redirect(url_for("forgot_password"))
            
            if user.is_admin:
                flash("Ta funkcja jest dostępna tylko dla zwykłych użytkowników. Skontaktuj się z innym administratorem.", "error")
                return redirect(url_for("login"))
        
            # Zresetuj hasło
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Hasło zostało zresetowane. Możesz się teraz zalogować.", "success")
            return redirect(url_for("login"))
        
        return render_template("forgot_password.html")

    # ---------- Cars & Reservations ----------
    @app.route("/cars")
    def cars():
        cars = Car.query.order_by(Car.make, Car.model).all()
        return render_template("cars.html", cars=cars)

    @app.route("/my-reservations")
    @login_required
    def my_reservations():
        # Zawsze sortujemy od najnowszych
        q = Reservation.query.order_by(Reservation.start_date.desc())
        
        if current_user.is_admin:
            # ADMIN: Widzi wszystko. 
            # Pobieramy rezerwacje, od razu ładując dane auta i użytkownika
            reservations = q.options(
                joinedload(Reservation.user), 
                joinedload(Reservation.car)
            ).all()
            title = "Wszystkie rezerwacje"
        else:
            # ZWYKŁY USER: Widzi tylko swoje.
            # Filtrujemy po ID zalogowanego usera
            reservations = q.filter_by(user_id=current_user.id).options(
                joinedload(Reservation.car) # tu user jest niepotrzebny, bo to on
            ).all()
            title = "Moje rezerwacje"
            
        return render_template("reservations.html", 
                               reservations=reservations, 
                               title=title)
    

    @app.post("/reservations/<int:res_id>/delete")
    @login_required
    @admin_required  # Absolutnie kluczowe!
    def delete_reservation(res_id):
        res = Reservation.query.get_or_404(res_id)
        
        # Przechowajmy informację, kto to był, zanim usuniemy
        user_email = res.user.email 
        
        res.status = 'anulowana'
        db.session.commit()
        
        flash(f"Rezerwacja dla {user_email} została anulowana.", "success")
        return redirect(url_for('my_reservations'))

# ... po funkcji delete_reservation()

    # ---------- Admin Panel ----------
    @app.route("/admin/cars", methods=["GET"])
    @login_required
    @admin_required
    def admin_cars():
        cars = Car.query.order_by(Car.make, Car.model).all()
        return render_template("admin_cars.html", cars=cars)

    @app.post("/admin/cars/add")
    @login_required
    @admin_required
    def admin_add_car():
        try:
            make = request.form.get("make")
            model = request.form.get("model")
            year = int(request.form.get("year"))
            price_per_day = float(request.form.get("price_per_day"))

            if not make or not model or not year or not price_per_day:
                flash("Wypełnij wszystkie pola.", "error")
                return redirect(url_for('admin_cars'))
            
            new_car = Car(make=make, model=model, year=year, price_per_day=price_per_day, available=True)
            db.session.add(new_car)
            db.session.commit()
            flash(f"Samochód {make} {model} został dodany.", "success")
            
        except ValueError:
            flash("Rok i cena muszą być poprawnymi liczbami.", "error")
        except Exception as e:
            flash(f"Wystąpił błąd: {e}", "error")
            
        return redirect(url_for('admin_cars'))

    @app.post("/admin/cars/<int:car_id>/delete")
    @login_required
    @admin_required
    def admin_delete_car(car_id):
        car = Car.query.get_or_404(car_id)
        
        # Bezpiecznik: Sprawdź, czy auto ma rezerwacje (nawet anulowane)
        if car.reservations:
            flash(f"Nie można usunąć auta {car.make} {car.model}, ponieważ ma powiązane rezerwacje w historii.", "error")
            return redirect(url_for('admin_cars'))
            
        # Jeśli nie ma rezerwacji, można usunąć
        db.session.delete(car)
        db.session.commit()
        flash(f"Samochód {car.make} {car.model} został usunięty.", "success")
        return redirect(url_for('admin_cars'))
    
    # ---------- Forum ----------
    # ... reszta kodu, np. funkcja forum()



    @app.post("/cars/<int:car_id>/reserve")

    @login_required
    def reserve(car_id):
        car = Car.query.get_or_404(car_id)
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except Exception:
            flash("Podaj poprawne daty.", "error")
            return redirect(url_for("cars"))
        if end_date < start_date:
            flash("Data zakończenia nie może być wcześniejsza niż początek.", "error")
            return redirect(url_for("cars"))
        # Proste sprawdzenie konfliktu (demo)
        conflict = Reservation.query.filter(
            Reservation.car_id == car.id,
            Reservation.start_date <= end_date,
            Reservation.end_date >= start_date,
            Reservation.status == 'aktywna'
        ).first()
        if conflict:
            flash("Samochód jest już zarezerwowany w wybranym okresie.", "error")
            return redirect(url_for("cars"))

        res = Reservation(user_id=current_user.id, car_id=car.id,
                          start_date=start_date, end_date=end_date)
        db.session.add(res)
        db.session.commit()
        flash("Rezerwacja zapisana.", "success")
        return redirect(url_for("my_reservations"))

    # ---------- Forum ----------
    @app.route("/forum", methods=["GET", "POST"])
    @login_required
    def forum():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Podaj tytuł tematu.", "error")
            else:
                topic = ForumTopic(title=title, user_id=current_user.id)
                db.session.add(topic)
                db.session.commit()
                return redirect(url_for("forum_topic", topic_id=topic.id))
        topics = ForumTopic.query.order_by(ForumTopic.created_at.desc()).all()
        return render_template("forum.html", topics=topics)

    @app.route("/forum/topic/<int:topic_id>", methods=["GET", "POST"])
    @login_required
    def forum_topic(topic_id):
        topic = ForumTopic.query.get_or_404(topic_id)
        if request.method == "POST":
            content = request.form.get("content", "").strip()
            if content:
                post = ForumPost(topic_id=topic.id, user_id=current_user.id, content=content)
                db.session.add(post)
                db.session.commit()
                return redirect(url_for("forum_topic", topic_id=topic.id))
            flash("Wpis nie może być pusty.", "error")
        posts = ForumPost.query.filter_by(topic_id=topic.id).order_by(ForumPost.created_at.asc()).all()
        return render_template("forum_topic.html", topic=topic, posts=posts)

    # ---------- Chat (prosty polling) ----------
    @app.route("/chat")
    @login_required
    def chat():
        return render_template("chat.html")

    @app.get("/api/chat/messages")
    @login_required
    def chat_messages():
        after = request.args.get("after")
        q = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(50)
        messages = list(reversed(q.all()))  # najnowsze 50, odwrócone do rosnącego
        if after:
            try:
                after_dt = datetime.fromisoformat(after)
                messages = [m for m in messages if m.created_at > after_dt]
            except Exception:
                pass
        data = [{
            "id": m.id,
            "user": m.user.name,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        } for m in messages]
        return jsonify(data)

    @app.post("/api/chat/send")
    @login_required
    def chat_send():
        content = (request.json or {}).get("content", "").strip()
        if not content:
            return jsonify({"ok": False, "error": "empty"}), 400
        m = ChatMessage(user_id=current_user.id, content=content)
        db.session.add(m)
        db.session.commit()
        return jsonify({"ok": True, "id": m.id, "created_at": m.created_at.isoformat()})


    @app.post("/api/chat/message/<int:message_id>/delete")
    @login_required
    @admin_required # Kluczowe!
    def delete_chat_message(message_id):
        msg = ChatMessage.query.get_or_404(message_id)
        
        db.session.delete(msg)
        db.session.commit()
        
        return jsonify({"ok": True})

    # ---------- Helpers ----------
    @app.template_filter("fmt_dt")
    def fmt_dt(dt: datetime):
        return dt.strftime("%Y-%m-%d %H:%M")

    # ========================================================
    # SECURITY HEADERS (L7 - Naprawa błędów OWASP ZAP)
    # ========================================================
    @app.after_request
    def add_security_headers(response):
        # 1. Content-Security-Policy (CSP)
        # Pozwalamy na skrypty/style lokalne ('self') i inline
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:;"
        )
        response.headers['Content-Security-Policy'] = csp_policy

        # 2. Strict-Transport-Security (HSTS)
        # Wymusza HTTPS przez 1 rok
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # 3. X-Frame-Options (Anti-Clickjacking)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # 4. X-Content-Type-Options
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # 5. Server Obfuscation (Ukrywamy wersję serwera)
        response.headers['Server'] = 'BSIAW-Secure-Server'

        # 6. Permissions-Policy (Blokujemy zbędne API przeglądarki)
        response.headers['Permissions-Policy'] = "geolocation=(), microphone=(), camera=()"

        # 7. Site Isolation (Naprawa błędu Spectre z ZAP) - TEGO BRAKUJE
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        
        # 8. Cache (Wymuszamy odświeżanie, żeby skaner widział zmiany)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        return response
    # ========================================================

    return app


    
def seed(app):
    with app.app_context():
        # Utwórz katalog na bazę
        Path("/app/data").mkdir(parents=True, exist_ok=True)
        db.create_all()
        
        # Migracja: Dodaj security_code dla starych użytkowników
        try:
            users_without_code = User.query.filter(
                (User.security_code == None) | (User.security_code == '')
            ).all()
            if users_without_code:
                print(f"Generating security codes for {len(users_without_code)} existing users...")
                for user in users_without_code:
                    user.security_code = User.generate_security_code()
                    print(f"  {user.email}: {user.security_code}")
                db.session.commit()
                print("Security codes migration completed!")
        except Exception as e:
            print(f"Migration note: {e}")
            db.session.rollback()
        
        # Admin
        admin_email = "admin@example.com"
        admin = User.query.filter_by(email=admin_email).first()
        
        # Pobierz nowe hasło ze zmiennych
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_password:
             raise ValueError("CRITICAL ERROR: Zmienna 'ADMIN_PASSWORD' brakująca!")

        if not admin:
            # Scenariusz 1: Admina nie ma -> Tworzymy nowego
            admin = User(
                email=admin_email,
                name="Admin",
                password_hash=generate_password_hash(admin_password),
                security_code=User.generate_security_code(),
                is_admin=True
            )
            db.session.add(admin)
            print(f"Admin created - Email: {admin_email}")
        else:
            # Scenariusz 2: Admin już jest (stare hasło) -> AKTUALIZUJEMY HASŁO
            # To naprawi problem na AWS i localhost bez kasowania bazy!
            admin.password_hash = generate_password_hash(admin_password)
            # Upewniamy się, że ma uprawnienia admina
            admin.is_admin = True
            print(f"Admin updated - Password reset for: {admin_email}")
        
        
        # Samochody
        if Car.query.count() == 0:
            cars = [
                Car(make="Toyota", model="Corolla", year=2020, price_per_day=120.0, available=True),
                Car(make="Skoda", model="Octavia", year=2019, price_per_day=110.0, available=True),
                Car(make="BMW", model="3", year=2021, price_per_day=220.0, available=True),
                Car(make="Kia", model="Ceed", year=2018, price_per_day=95.0, available=True),
            ]
            db.session.add_all(cars)
        db.session.commit()

if __name__ == "__main__":
    app = create_app()
    # Wait for database to be available before seeding
    wait_for_db(app)
    seed(app)
    # Uruchom wbudowany serwer (demo). W produkcji użyj gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
