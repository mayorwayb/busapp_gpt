from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret")

# SQLite config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bus_safety.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="User")
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # passenger, driver, admin

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passenger_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trip_date = db.Column(db.String(50), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Booked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    passenger = db.relationship("User", backref=db.backref("bookings", lazy=True))

with app.app_context():
    db.create_all()

# ---------- Helpers ----------
def login_required(fn):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

def require_role(role):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "error")
                return redirect(url_for("login"))
            if session.get("role") != role:
                flash("You are not authorized to view that page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# ---------- Routes ----------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "User"
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "passenger")

        if not email or not password or role not in ("passenger", "driver", "admin"):
            flash("Please fill all fields correctly.", "error")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "error")
            return redirect(url_for("login"))

        hashed = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed, role=role)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["role"] = user.role
        session["name"] = user.name
        flash("Signup successful. Welcome!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            session["name"] = user.name
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    name = session.get("name", "User")
    if role == "admin":
        total_users = User.query.count()
        total_passengers = User.query.filter_by(role="passenger").count()
        total_drivers = User.query.filter_by(role="driver").count()
        total_bookings = Booking.query.count()
        return render_template(
            "admin_dashboard.html",
            name=name,
            role=role,
            active="dashboard",
            total_users=total_users,
            total_passengers=total_passengers,
            total_drivers=total_drivers,
            total_bookings=total_bookings,
        )
    elif role == "driver":
        # Offline placeholder: show no assigned trips yet
        assigned_trips = []
        return render_template(
            "driver_dashboard.html",
            name=name,
            role=role,
            active="dashboard",
            assigned_trips=assigned_trips,
            current=None,
        )
    else:
        # passenger
        uid = session.get("user_id")
        upcoming = (
            Booking.query.filter_by(passenger_id=uid)
            .filter(Booking.status != "Completed")
            .order_by(Booking.created_at.desc())
            .all()
        )
        history = (
            Booking.query.filter_by(passenger_id=uid, status="Completed")
            .order_by(Booking.created_at.desc())
            .all()
        )
        return render_template(
            "passenger_dashboard.html",
            name=name,
            role=role,
            active="dashboard",
            trips=upcoming,
            history=history,
        )

# ----- Passenger features -----
@app.route("/book-trip", methods=["GET", "POST"])
@require_role("passenger")
def book_trip():
    if request.method == "POST":
        trip_date = request.form.get("trip_date", "").strip()
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        if not trip_date or not origin or not destination:
            flash("Please complete all trip fields.", "error")
            return redirect(url_for("book_trip"))

        booking = Booking(
            passenger_id=session["user_id"],
            trip_date=trip_date,
            origin=origin,
            destination=destination,
            status="Booked",
        )
        db.session.add(booking)
        db.session.commit()
        flash("Trip booked successfully!", "success")
        return redirect(url_for("view_bookings"))

    return render_template("book_trip.html", active="book_trip")

@app.route("/view-bookings")
@require_role("passenger")
def view_bookings():
    bookings = Booking.query.filter_by(passenger_id=session["user_id"]).order_by(Booking.created_at.desc()).all()
    return render_template("view_bookings.html", bookings=bookings, active="view_bookings")

@app.route("/send-alert", methods=["GET", "POST"])
@login_required
def send_alert():
    if request.method == "POST":
        # Offline: just acknowledge
        flash("Emergency alert sent (demo).", "success")
        return redirect(url_for("dashboard"))
    return render_template("sendalert.html", active="send_alert")

# ----- Profile -----
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pwd = request.form.get("password", "").strip()
        if name:
            user.name = name
            session["name"] = name
        if pwd:
            user.password = generate_password_hash(pwd)
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user, active="profile")

# ----- Simple admin/driver placeholders for completeness -----
@app.route("/reports")
@require_role("admin")
def reports():
    return render_template("admin_dashboard.html", active="reports", name=session.get("name"), role="admin")

@app.route("/manage-users")
@require_role("admin")
def manage_users():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin_dashboard.html", active="manage_users", name=session.get("name"), role="admin", users=users)

@app.route("/trips-overview")
@require_role("admin")
def trips_overview():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template("admin_dashboard.html", active="trips_overview", name=session.get("name"), role="admin", bookings=bookings)

@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
