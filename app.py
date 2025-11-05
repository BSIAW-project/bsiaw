import os
from datetime import datetime, date
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Car, Reservation, ForumTopic, ForumPost, ChatMessage

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////app/data/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

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
            if User.query.filter_by(email=email).first():
                flash("Użytkownik o tym e-mailu już istnieje.", "error")
                return redirect(url_for("register"))

            user = User(email=email, name=name, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash("Konto utworzone. Możesz się zalogować.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
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

    # ---------- Cars & Reservations ----------
    @app.route("/cars")
    def cars():
        cars = Car.query.order_by(Car.make, Car.model).all()
        return render_template("cars.html", cars=cars)

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
            Reservation.end_date >= start_date
        ).first()
        if conflict:
            flash("Samochód jest już zarezerwowany w wybranym okresie.", "error")
            return redirect(url_for("cars"))

        res = Reservation(user_id=current_user.id, car_id=car.id,
                          start_date=start_date, end_date=end_date)
        db.session.add(res)
        db.session.commit()
        flash("Rezerwacja zapisana.", "success")
        return redirect(url_for("cars"))

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

    # ---------- Helpers ----------
    @app.template_filter("fmt_dt")
    def fmt_dt(dt: datetime):
        return dt.strftime("%Y-%m-%d %H:%M")

    return app

def seed(app):
    with app.app_context():
        # Utwórz katalog na bazę
        Path("/app/data").mkdir(parents=True, exist_ok=True)
        db.create_all()
        # Admin
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(
                email="admin@example.com",
                name="Admin",
                password_hash=generate_password_hash("admin123")
            )
            db.session.add(admin)
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
    seed(app)
    # Uruchom wbudowany serwer (demo). W produkcji użyj gunicorn/uwsgi.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
