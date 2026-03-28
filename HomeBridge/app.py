from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from geopy.distance import geodesic
import requests
import re
import math

from zoneinfo import ZoneInfo

# UK timezone - handles GMT/BST transitions automatically
UK_TZ = ZoneInfo("Europe/London")

def uk_now():
    """Returns current datetime in UK time (handles BST/GMT automatically)"""
    return datetime.now(UK_TZ).replace(tzinfo=None)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rita-zambito-secret-key-2245801'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteer_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ============ DATABASE MODELS ============

class ServiceUser(db.Model):
    __tablename__ = 'service_users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    postcode = db.Column(db.String(10))
    latitude = db.Column(db.Float)  # Cached coordinates
    longitude = db.Column(db.Float)  # Cached coordinates
    conditions = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    registered_date = db.Column(db.DateTime, default=uk_now)
    status = db.Column(db.String(20), default='active')


class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    postcode = db.Column(db.String(10))
    latitude = db.Column(db.Float)  # Cached coordinates
    longitude = db.Column(db.Float)  # Cached coordinates
    skills = db.Column(db.Text)
    bio = db.Column(db.Text)  # Short presentation
    # Availability grid - one slot per day
    monday_slot = db.Column(db.String(20), default='Not Available')
    tuesday_slot = db.Column(db.String(20), default='Not Available')
    wednesday_slot = db.Column(db.String(20), default='Not Available')
    thursday_slot = db.Column(db.String(20), default='Not Available')
    friday_slot = db.Column(db.String(20), default='Not Available')
    saturday_slot = db.Column(db.String(20), default='Not Available')
    sunday_slot = db.Column(db.String(20), default='Not Available')
    registered_date = db.Column(db.DateTime, default=uk_now)
    status = db.Column(db.String(20), default='active')
    total_completed = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('service_users.id'), nullable=False)
    support_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    urgency = db.Column(db.String(20))
    preferred_date = db.Column(db.String(50))
    time_slot = db.Column(db.String(20))  # e.g., "09:00-12:00"
    status = db.Column(db.String(30), default='pending')
    is_saved = db.Column(db.Boolean, default=False)  # True = saved search, False = temporary/in progress
    created_date = db.Column(db.DateTime, default=uk_now)
    matched_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'))
    cancelled_by_name = db.Column(db.String(100))  # Name of who cancelled
    cancelled_volunteer_name = db.Column(db.String(100))  # Volunteer assigned at time of cancellation
    cancelled_date = db.Column(db.DateTime)  # When it was cancelled
    hidden_by_user = db.Column(db.Boolean, default=False)  # Hidden from user dashboard but visible to admin
    hidden_by_volunteer = db.Column(db.Boolean, default=False)  # Hidden from volunteer dashboard but visible to admin

    # Relationships
    volunteer = db.relationship('Volunteer', backref='assigned_requests', foreign_keys=[volunteer_id])
    user = db.relationship('ServiceUser', backref='requests', foreign_keys=[user_id])
    feedback = db.relationship('Feedback', backref='request', uselist=False)
    
    @property
    def has_feedback(self):
        return self.feedback is not None
    
    @property
    def booking_datetime(self):
        """Returns the booking datetime (start of time slot)"""
        if self.preferred_date and self.time_slot:
            try:
                start_time = self.time_slot.split('-')[0]  # e.g., "09:00"
                date_str = f"{self.preferred_date} {start_time}"
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                return None
        return None
    
    @property
    def can_volunteer_cancel(self):
        """Check if volunteer can cancel (more than 48 hours before booking)"""
        booking = self.booking_datetime
        if booking:
            time_until_booking = booking - uk_now()
            return time_until_booking.total_seconds() > 48 * 3600  # 48 hours
        return True  # If no valid date, allow cancellation


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('service_users.id'))
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=uk_now)


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    # Conversation is identified by participant_id + participant_type (the non-admin user)
    participant_id = db.Column(db.Integer, nullable=False)
    participant_type = db.Column(db.String(20), nullable=False)  # 'user' or 'volunteer'
    # Who sent this specific message
    sender_type = db.Column(db.String(20), nullable=False)  # 'user', 'volunteer', 'admin'
    sender_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=uk_now)
    linked_request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=True)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, nullable=False)
    recipient_type = db.Column(db.String(20), nullable=False)  # 'user', 'volunteer', 'admin'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(300))  # URL to redirect when clicked
    link_expires = db.Column(db.String(10))  # Date string YYYY-MM-DD - link hidden after this date
    is_read = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=uk_now)


def create_notification(recipient_id, recipient_type, title, message, link=None, link_expires=None):
    """Helper function to create a notification"""
    notif = Notification(
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        title=title,
        message=message,
        link=link,
        link_expires=link_expires
    )
    db.session.add(notif)
    return notif


# ============ USER LOADER FOR FLASK-LOGIN ============

class User(UserMixin):
    def __init__(self, id, email, name, user_type):
        self.id = id
        self.email = email
        self.name = name
        self.user_type = user_type


@login_manager.user_loader
def load_user(user_id):
    user_type, actual_id = user_id.split('_')
    actual_id = int(actual_id)

    if user_type == 'user':
        user_obj = ServiceUser.query.get(actual_id)
        if user_obj:
            return User(user_id, user_obj.email, user_obj.name, 'user')
    elif user_type == 'volunteer':
        volunteer_obj = Volunteer.query.get(actual_id)
        if volunteer_obj:
            return User(user_id, volunteer_obj.email, volunteer_obj.name, 'volunteer')
    elif user_type == 'admin':
        admin_obj = Admin.query.get(actual_id)
        if admin_obj:
            return User(user_id, admin_obj.email, admin_obj.name, 'admin')

    return None


@app.after_request
def add_no_cache(response):
    """Prevent browser from caching pages so back button shows fresh data"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.context_processor
def inject_notification_count():
    """Make unread notification count available in all templates"""
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        actual_id = int(current_user.id.split('_')[1])
        count = Notification.query.filter_by(
            recipient_id=actual_id,
            recipient_type=current_user.user_type,
            is_read=False
        ).count()
        return {'unread_notifications': count}
    return {'unread_notifications': 0}


@app.template_filter('format_date')
def format_date_filter(date_str):
    """Convert '2026-02-19' to '19 Feb 2026'"""
    if not date_str:
        return 'Flexible'
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d %b %Y')
    except (ValueError, TypeError):
        return date_str

def fmt_date(date_str):
    """Python helper - same as format_date_filter"""
    return format_date_filter(date_str)


# ============ MATCHING ALGORITHM ============

def get_slot_name(time_slot):
    """Convert time slot to slot name"""
    slot_map = {
        '09:00-12:00': 'Morning',
        '12:00-15:00': 'Afternoon',
        '15:00-18:00': 'Late Afternoon'
    }
    return slot_map.get(time_slot, None)

def get_volunteer_slot_for_day(volunteer, day):
    """Get volunteer's availability for a specific day"""
    day_map = {
        'Monday': volunteer.monday_slot,
        'Tuesday': volunteer.tuesday_slot,
        'Wednesday': volunteer.wednesday_slot,
        'Thursday': volunteer.thursday_slot,
        'Friday': volunteer.friday_slot,
        'Saturday': volunteer.saturday_slot,
        'Sunday': volunteer.sunday_slot
    }
    return day_map.get(day, 'Not Available')

def calculate_match_score(volunteer, request_obj, user):
    """
    SMART MATCHING ALGORITHM
    
    Multi-criteria weighted scoring with normalised sub-scores.
    Each criterion produces a value between 0.0 and 1.0, then
    multiplied by its weight. Final score is a percentage out of 100.
    
    Weights:
    - Availability (day + time slot):  40 points
    - Distance (exponential decay):    40 points
    - Skills (exact match):            15 points
    - Reliability (rating + history):   5 points
    
    Techniques used:
    - Geodesic distance with exponential decay function
    - Normalised sub-scores for fair cross-criteria comparison
    """
    
    WEIGHT_AVAILABILITY = 40
    WEIGHT_DISTANCE = 40
    WEIGHT_SKILLS = 15
    WEIGHT_RELIABILITY = 5
    
    score = 0
    details = {}
    
    # ──────────────────────────────────────────────
    # 1. AVAILABILITY MATCH (35 points)
    # ──────────────────────────────────────────────
    # Normalised scoring:
    #   Perfect match (same day + slot) or Flexible → 1.0
    #   Same day, different time slot               → 0.55
    #   No specific day requested                   → 0.5
    #   Day not available at all                    → 0.0
    
    is_available = False
    availability_score = 0.0
    
    request_day = None
    if request_obj.preferred_date:
        try:
            date_obj = datetime.strptime(request_obj.preferred_date, "%Y-%m-%d")
            request_day = date_obj.strftime("%A")
            details['request_day'] = request_day
        except (ValueError, TypeError):
            pass
    
    requested_slot = get_slot_name(request_obj.time_slot) if request_obj.time_slot else None
    
    if request_day:
        volunteer_slot = get_volunteer_slot_for_day(volunteer, request_day)
        
        if volunteer_slot == 'Not Available':
            availability_score = 0.0
            details['availability_match'] = '❌ Not available this day'
            details['volunteer_slot'] = 'Not Available'
        elif volunteer_slot == 'Flexible':
            availability_score = 1.0
            is_available = True
            details['availability_match'] = '✅ Available (Flexible)'
            details['volunteer_slot'] = 'Flexible'
        elif requested_slot and volunteer_slot == requested_slot:
            availability_score = 1.0
            is_available = True
            details['availability_match'] = f'✅ Available ({volunteer_slot})'
            details['volunteer_slot'] = volunteer_slot
        else:
            # Same day but different time slot — partial credit
            availability_score = 0.55
            details['availability_match'] = f'⚠️ Available but at {volunteer_slot}'
            details['volunteer_slot'] = volunteer_slot
    else:
        availability_score = 0.5
        is_available = True
        details['availability_match'] = '⚡ Flexible'
        details['volunteer_slot'] = 'Flexible'
    
    # Check for existing booking conflict
    if is_available and request_obj.preferred_date and request_obj.time_slot:
        existing_booking = Request.query.filter(
            Request.volunteer_id == volunteer.id,
            Request.preferred_date == request_obj.preferred_date,
            Request.time_slot == request_obj.time_slot,
            Request.status.in_(['awaiting', 'in_progress']),
            Request.id != request_obj.id
        ).first()
        if existing_booking:
            is_available = False
            availability_score = 0.0
            details['availability_match'] = '❌ Already booked for this date and time'
            details['volunteer_slot'] = 'Booked'
    
    score += round(availability_score * WEIGHT_AVAILABILITY)
    
    # ──────────────────────────────────────────────
    # 2. DISTANCE — Exponential Decay (40 points)
    # ──────────────────────────────────────────────
    # Instead of fixed brackets, uses a smooth decay curve:
    #   score = e^(-decay_rate × distance_in_miles)
    #
    # With decay_rate = 0.15:
    #   0 miles  → 1.00 (40 pts)    5 miles  → 0.47 (19 pts)
    #   1 mile   → 0.86 (34 pts)   10 miles  → 0.22 (9 pts)
    #   2 miles  → 0.74 (30 pts)   20 miles  → 0.05 (2 pts)
    #   3 miles  → 0.64 (26 pts)   50+ miles → ~0   (0 pts)
    
    DECAY_RATE = 0.15
    distance_score = 0.0
    
    try:
        user_coords = None
        vol_coords = None
        
        if user.latitude and user.longitude:
            user_coords = (user.latitude, user.longitude)
        else:
            user_coords = get_coordinates(user.postcode)
            
        if volunteer.latitude and volunteer.longitude:
            vol_coords = (volunteer.latitude, volunteer.longitude)
        else:
            vol_coords = get_coordinates(volunteer.postcode)
            
        if user_coords and vol_coords:
            distance = geodesic(user_coords, vol_coords).miles
            details['distance'] = round(distance, 2)
            distance_score = math.exp(-DECAY_RATE * distance)
        else:
            details['distance'] = 'N/A'
            distance_score = 0.4  # Neutral fallback when coordinates unavailable
    except Exception:
        details['distance'] = 'N/A'
        distance_score = 0.4
    
    score += round(distance_score * WEIGHT_DISTANCE)
    
    # ──────────────────────────────────────────────
    # 3. SKILLS MATCH (15 points)
    # ──────────────────────────────────────────────
    # Exact match:  1.0 (15 pts)
    # No match:     0.0 (0 pts)
    # No data:      0.25 (4 pts) — benefit of the doubt
    
    skills_match = False
    skills_score = 0.0
    
    if volunteer.skills and request_obj.support_type:
        volunteer_skills = [s.strip().lower() for s in volunteer.skills.split(',')]
        requested_skill = request_obj.support_type.lower()
        
        if requested_skill in volunteer_skills:
            skills_score = 1.0
            skills_match = True
            details['skills_status'] = '✅ Offers this service'
        else:
            skills_score = 0.0
            details['skills_status'] = '❌ Does not offer this service'
    else:
        skills_score = 0.25
        details['skills_status'] = '⚡ General support'
    
    score += round(skills_score * WEIGHT_SKILLS)
    
    # ──────────────────────────────────────────────
    # 4. RELIABILITY — Rating + Track Record (5 points)
    # ──────────────────────────────────────────────
    # Combines two factors into a single normalised score:
    #
    #   a) Average rating (70% of reliability score):
    #      rating_component = average_rating / 5.0
    #      New volunteers (0 rating) get 0.5 baseline
    #
    #   b) Track record (30% of reliability score):
    #      Completion rate based on total_completed,
    #      capped at 10 for normalisation:
    #      track_component = min(total_completed, 10) / 10
    
    # a) Rating component
    if volunteer.average_rating > 0:
        rating_component = volunteer.average_rating / 5.0
    else:
        rating_component = 0.5  # New volunteers: neutral baseline
    
    # b) Track record component
    completed = volunteer.total_completed if volunteer.total_completed else 0
    track_component = min(completed, 10) / 10.0
    
    reliability_score = (rating_component * 0.70) + (track_component * 0.30)
    
    score += round(reliability_score * WEIGHT_RELIABILITY)
    
    # ──────────────────────────────────────────────
    # FINAL SCORE AND DETAILS
    # ──────────────────────────────────────────────
    
    details['score'] = score
    details['skills_match'] = volunteer.skills if volunteer.skills else 'General support'
    details['has_skill'] = skills_match
    details['is_available'] = is_available
    
    # Badge type for UI display
    volunteer_slot_value = details.get('volunteer_slot', 'Not Available')
    if is_available:
        details['badge_type'] = 'perfect'
    elif volunteer_slot_value not in ['Not Available', 'Booked']:
        details['badge_type'] = 'different_slot'
    else:
        details['badge_type'] = 'day_unavailable'

    return score, details


def get_coordinates(postcode):
    """
    Get latitude and longitude for UK postcode using Postcodes.io API.
    Falls back to hardcoded postcodes if API is unavailable.
    """
    if not postcode:
        return None
    
    # Clean the postcode
    postcode_clean = postcode.strip().upper().replace('  ', ' ')
    
    try:
        # Use Postcodes.io API - best for UK postcodes
        url = f"https://api.postcodes.io/postcodes/{postcode_clean}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('result'):
                latitude = data['result']['latitude']
                longitude = data['result']['longitude']
                print(f"✓ Geocoded {postcode_clean}: {latitude:.4f}, {longitude:.4f}")
                return (latitude, longitude)
        
        print(f"API call failed for {postcode_clean}, using fallback")
        
    except Exception as e:
        print(f"Error geocoding {postcode_clean}: {e}, using fallback")
    
    # Fallback: hardcoded postcodes for offline/testing
    postcode_map = {
        # Birmingham area
        'B15': (52.4508, -1.9305),
        'B17': (52.4562, -1.9659),
        'B11': (52.4575, -1.8614),
        'B16': (52.4862, -1.9241),
        'B18': (52.4989, -1.9152),
        'B10': (52.4642, -1.8586),
        'B5': (52.4751, -1.8870),
        'B21': (52.5151, -1.9225),
        'B12': (52.4586, -1.8798),
        'B8': (52.4814, -1.8386),
        'B20': (52.5089, -1.9401),
        'B24': (52.5234, -1.8178),
        'B23': (52.5308, -1.8443),
        'B29': (52.4394, -1.9629),
        'B42': (52.5456, -1.8897),
        # Swansea area
        'SA1': (51.6214, -3.9436),
        'SA2': (51.6154, -3.9831),
        'SA3': (51.5699, -4.0588),
        'SA4': (51.6590, -4.0823),
        'SA5': (51.6562, -3.9189),
        'SA6': (51.6890, -3.9143),
        'SA7': (51.7128, -3.8842),
    }
    
    area = postcode_clean.split()[0][:3]
    fallback_coords = postcode_map.get(area)
    if fallback_coords:
        print(f"Using fallback coordinates for {postcode_clean}")
    return fallback_coords


# ============ ROUTES ============

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        user_obj = None
        db_user = None

        if user_type == 'admin':
            db_user = Admin.query.filter_by(email=email).first()
        elif user_type == 'volunteer':
            db_user = Volunteer.query.filter_by(email=email).first()
        else:
            db_user = ServiceUser.query.filter_by(email=email).first()

        if db_user and check_password_hash(db_user.password, password):
            # Check if account is suspended (only for users and volunteers)
            if user_type in ['user', 'volunteer'] and hasattr(db_user, 'status') and db_user.status == 'suspended':
                flash('Your account has been suspended. Please contact the administrator.', 'danger')
                return redirect(url_for('login'))
            
            user_obj = User(f'{user_type}_{db_user.id}', db_user.email, db_user.name, user_type)
            login_user(user_obj, remember=False)

            if user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user_type == 'volunteer':
                return redirect(url_for('volunteer_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        postcode = request.form.get('postcode')

        # Check if email exists
        if ServiceUser.query.filter_by(email=email).first() or Volunteer.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        # Password validation
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('register'))
        if not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter', 'danger')
            return redirect(url_for('register'))
        if not re.search(r'[a-z]', password):
            flash('Password must contain at least one lowercase letter', 'danger')
            return redirect(url_for('register'))
        if not re.search(r'[0-9]', password):
            flash('Password must contain at least one number', 'danger')
            return redirect(url_for('register'))
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must contain at least one special character (!@#$%^&* etc.)', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        # Geocode postcode once during registration
        coords = get_coordinates(postcode)
        latitude = coords[0] if coords else None
        longitude = coords[1] if coords else None

        if user_type == 'volunteer':
            # Get checkbox values (multiple selections)
            skills_list = request.form.getlist('skills')
            skills = ','.join(skills_list)
            
            new_volunteer = Volunteer(
                name=name,
                email=email,
                password=hashed_password,
                phone=phone,
                address=address,
                postcode=postcode,
                latitude=latitude,
                longitude=longitude,
                skills=skills,
                bio=request.form.get('bio', ''),
                monday_slot=request.form.get('monday_slot', 'Not Available'),
                tuesday_slot=request.form.get('tuesday_slot', 'Not Available'),
                wednesday_slot=request.form.get('wednesday_slot', 'Not Available'),
                thursday_slot=request.form.get('thursday_slot', 'Not Available'),
                friday_slot=request.form.get('friday_slot', 'Not Available'),
                saturday_slot=request.form.get('saturday_slot', 'Not Available'),
                sunday_slot=request.form.get('sunday_slot', 'Not Available')
            )
            db.session.add(new_volunteer)
        else:
            new_user = ServiceUser(
                name=name,
                email=email,
                password=hashed_password,
                phone=phone,
                address=address,
                postcode=postcode,
                latitude=latitude,
                longitude=longitude,
                conditions=', '.join(request.form.getlist('conditions')),
                emergency_contact=request.form.get('emergency_contact', '')
            )
            db.session.add(new_user)

        db.session.commit()
        
        # Notify admin of new registration
        admins = Admin.query.all()
        for admin in admins:
            create_notification(
                recipient_id=admin.id,
                recipient_type='admin',
                title=f'New {user_type.title()} Registered',
                message=f'{name} has registered as a {"volunteer" if user_type == "volunteer" else "service user"}.',
                link=f'/admin/{"volunteers" if user_type == "volunteer" else "users"}'
            )
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.user_type != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user_id = int(current_user.id.split('_')[1])
    
    # Auto-delete expired saved searches (date has passed)
    today = uk_now().strftime('%Y-%m-%d')
    yesterday = (uk_now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    expired_searches = Request.query.filter_by(
        user_id=user_id,
        status='pending',
        is_saved=True
    ).filter(Request.preferred_date <= today).all()
    
    for expired in expired_searches:
        db.session.delete(expired)
    if expired_searches:
        db.session.commit()

    # Auto-cancel awaiting requests where date passed yesterday (day after = gone)
    stale_awaiting = Request.query.filter_by(
        user_id=user_id,
        status='awaiting'
    ).filter(Request.preferred_date <= yesterday).all()
    
    for stale in stale_awaiting:
        stale.status = 'cancelled'
        stale.cancelled_by_name = 'System'
        stale.cancelled_date = uk_now()
    if stale_awaiting:
        db.session.commit()

    # Send notification for awaiting requests expiring today (date is today or passed)
    expiring_awaiting = Request.query.filter_by(
        user_id=user_id,
        status='awaiting'
    ).filter(Request.preferred_date <= today).all()
    
    for exp_req in expiring_awaiting:
        # Check if we already sent an expiry notification for this request
        existing_notif = Notification.query.filter_by(
            recipient_id=user_id,
            recipient_type='user',
            title='Request Not Accepted'
        ).filter(Notification.message.like(f'%request #{exp_req.id}%')).first()
        
        if not existing_notif:
            create_notification(
                recipient_id=user_id,
                recipient_type='user',
                title='Request Not Accepted',
                message=f'Your {exp_req.support_type} request #{exp_req.id} for {fmt_date(exp_req.preferred_date)} was not accepted in time.',
                link=None
            )

    my_requests = Request.query.filter_by(user_id=user_id).filter(
        Request.hidden_by_user == False,
        # Exclude temporary unsaved searches (pending + not saved)
        db.or_(Request.status != 'pending', Request.is_saved == True)
    ).order_by(Request.created_date.desc()).all()
    
    # Count unread chat messages from admin
    unread_replies = ChatMessage.query.filter_by(
        participant_id=user_id,
        participant_type='user',
        sender_type='admin',
        is_read=False
    ).count()

    return render_template('user/dashboard.html', requests=my_requests, unread_replies=unread_replies, today=today)


@app.route('/user/profile')
@login_required
def user_profile():
    if current_user.user_type != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user_id = int(current_user.id.split('_')[1])
    user = ServiceUser.query.get_or_404(user_id)

    return render_template('user/profile.html', user=user)


@app.route('/user/edit-profile', methods=['GET', 'POST'])
@login_required
def user_edit_profile():
    if current_user.user_type != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user_id = int(current_user.id.split('_')[1])
    user = ServiceUser.query.get_or_404(user_id)

    if request.method == 'POST':
        new_email = request.form.get('email')
        if new_email != user.email:
            if ServiceUser.query.filter_by(email=new_email).first() or Volunteer.query.filter_by(email=new_email).first():
                flash('That email is already in use.', 'danger')
                return render_template('user/edit_profile.html', user=user)
        user.name = request.form.get('name')
        user.email = new_email
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        
        new_postcode = request.form.get('postcode')
        # If postcode changed, update coordinates
        if new_postcode != user.postcode:
            user.postcode = new_postcode
            coords = get_coordinates(new_postcode)
            if coords:
                user.latitude = coords[0]
                user.longitude = coords[1]
        
        user.conditions = ', '.join(request.form.getlist('conditions'))
        user.emergency_contact = request.form.get('emergency_contact')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('user/edit_profile.html', user=user)


@app.route('/volunteer/dashboard')
@login_required
def volunteer_dashboard():
    if current_user.user_type != 'volunteer':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    volunteer_id = int(current_user.id.split('_')[1])

    # Pending requests
    pending_requests = Request.query.filter_by(status='pending').all()

    # My assigned requests (exclude hidden ones)
    my_requests = Request.query.filter_by(volunteer_id=volunteer_id, hidden_by_volunteer=False).order_by(Request.created_date.desc()).all()
    
    # Pass today's date for template
    today = uk_now().strftime('%Y-%m-%d')
    yesterday = (uk_now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Auto-cancel awaiting requests where date passed yesterday (day after = gone)
    stale_awaiting = Request.query.filter_by(
        volunteer_id=volunteer_id,
        status='awaiting'
    ).filter(Request.preferred_date <= yesterday).all()
    
    for stale in stale_awaiting:
        stale.status = 'cancelled'
        stale.cancelled_by_name = 'System'
        stale.cancelled_date = uk_now()
    if stale_awaiting:
        db.session.commit()
    
    # Count unread chat messages from admin
    unread_replies = ChatMessage.query.filter_by(
        participant_id=volunteer_id,
        participant_type='volunteer',
        sender_type='admin',
        is_read=False
    ).count()

    # Find requests with cancellation already requested (check chat messages)
    pending_cancel_messages = ChatMessage.query.filter_by(
        participant_id=volunteer_id,
        participant_type='volunteer'
    ).filter(ChatMessage.message.like('%cancel Request%')).all()
    pending_cancel_ids = [m.linked_request_id for m in pending_cancel_messages if m.linked_request_id]

    return render_template('volunteer/dashboard.html',
                           pending_requests=pending_requests,
                           my_requests=my_requests,
                           today=today,
                           unread_replies=unread_replies,
                           pending_cancel_ids=pending_cancel_ids)


@app.route('/volunteer/profile')
@login_required
def volunteer_profile():
    if current_user.user_type != 'volunteer':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    volunteer_id = int(current_user.id.split('_')[1])
    volunteer = Volunteer.query.get_or_404(volunteer_id)

    return render_template('volunteer/profile.html', volunteer=volunteer)


@app.route('/volunteer/edit-profile', methods=['GET', 'POST'])
@login_required
def volunteer_edit_profile():
    if current_user.user_type != 'volunteer':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    volunteer_id = int(current_user.id.split('_')[1])
    volunteer = Volunteer.query.get_or_404(volunteer_id)

    if request.method == 'POST':
        new_email = request.form.get('email')
        if new_email != volunteer.email:
            if ServiceUser.query.filter_by(email=new_email).first() or Volunteer.query.filter_by(email=new_email).first():
                flash('That email is already in use.', 'danger')
                return render_template('volunteer/edit_profile.html', volunteer=volunteer)
        volunteer.name = request.form.get('name')
        volunteer.email = new_email
        volunteer.phone = request.form.get('phone')
        volunteer.address = request.form.get('address')
        
        new_postcode = request.form.get('postcode')
        # If postcode changed, update coordinates
        if new_postcode != volunteer.postcode:
            volunteer.postcode = new_postcode
            coords = get_coordinates(new_postcode)
            if coords:
                volunteer.latitude = coords[0]
                volunteer.longitude = coords[1]
        
        volunteer.bio = request.form.get('bio')
        
        # Skills (checkboxes)
        skills_list = request.form.getlist('skills')
        volunteer.skills = ','.join(skills_list)
        
        # Availability
        volunteer.monday_slot = request.form.get('monday_slot', 'Not Available')
        volunteer.tuesday_slot = request.form.get('tuesday_slot', 'Not Available')
        volunteer.wednesday_slot = request.form.get('wednesday_slot', 'Not Available')
        volunteer.thursday_slot = request.form.get('thursday_slot', 'Not Available')
        volunteer.friday_slot = request.form.get('friday_slot', 'Not Available')
        volunteer.saturday_slot = request.form.get('saturday_slot', 'Not Available')
        volunteer.sunday_slot = request.form.get('sunday_slot', 'Not Available')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('volunteer_profile'))

    return render_template('volunteer/edit_profile.html', volunteer=volunteer)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    # Statistics
    total_users = ServiceUser.query.count()
    total_volunteers = Volunteer.query.count()
    total_requests = Request.query.filter(Request.status != 'pending').count()  # Exclude saved searches
    # Don't count pending/saved searches in admin stats
    awaiting = Request.query.filter_by(status='awaiting').count()
    in_progress = Request.query.filter_by(status='in_progress').count()
    completed = Request.query.filter_by(status='completed').count()
    cancelled = Request.query.filter_by(status='cancelled').count()

    # Recent activity (for Overview tab) - exclude pending/saved searches
    recent_requests = Request.query.filter(Request.status != 'pending').order_by(Request.created_date.desc()).limit(10).all()
    recent_users = ServiceUser.query.order_by(ServiceUser.registered_date.desc()).limit(5).all()
    recent_volunteers = Volunteer.query.order_by(Volunteer.registered_date.desc()).limit(5).all()

    # Messages
    unread_messages = ChatMessage.query.filter_by(is_read=False).filter(ChatMessage.sender_type != 'admin').count()

    stats = {
        'total_users': total_users,
        'total_volunteers': total_volunteers,
        'total_requests': total_requests,
        'awaiting': awaiting,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
        'unread_messages': unread_messages
    }

    # Calculate success rate (completed vs cancelled - in_progress are still ongoing)
    if completed + cancelled > 0:
        stats['success_rate'] = round((completed / (completed + cancelled)) * 100, 1)
    else:
        stats['success_rate'] = 0

    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_requests=recent_requests,
                           recent_users=recent_users,
                           recent_volunteers=recent_volunteers)


@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    users = ServiceUser.query.order_by(ServiceUser.id.asc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/suspend-user/<int:user_id>', methods=['POST'])
@login_required
def admin_suspend_user(user_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    user = ServiceUser.query.get_or_404(user_id)
    
    # Toggle status between active and suspended
    if user.status == 'active':
        user.status = 'suspended'
        flash(f'User {user.name} has been suspended', 'warning')
    else:
        user.status = 'active'
        flash(f'User {user.name} has been reactivated', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    user = ServiceUser.query.get_or_404(user_id)
    
    # Check if user has pending or in-progress requests
    active_requests = Request.query.filter_by(user_id=user_id).filter(
        Request.status.in_(['pending', 'matched', 'in_progress', 'awaiting'])
    ).count()
    
    if active_requests > 0:
        flash(f'Cannot delete user {user.name}. They have {active_requests} active request(s). Please complete or cancel them first, or suspend the account instead.', 'danger')
        return redirect(url_for('admin_users'))
    
    # Delete user's completed requests and feedback
    completed_requests = Request.query.filter_by(user_id=user_id).all()
    for req in completed_requests:
        if req.feedback:
            db.session.delete(req.feedback)
        db.session.delete(req)
    
    # Delete user's chat messages
    ChatMessage.query.filter_by(participant_id=user_id, participant_type='user').delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.name} has been permanently deleted', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/volunteers')
@login_required
def admin_volunteers():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    volunteers = Volunteer.query.order_by(Volunteer.id.asc()).all()
    return render_template('admin/volunteers.html', volunteers=volunteers)


@app.route('/admin/suspend-volunteer/<int:volunteer_id>', methods=['POST'])
@login_required
def admin_suspend_volunteer(volunteer_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    
    # Toggle status between active and suspended
    if volunteer.status == 'active':
        volunteer.status = 'suspended'
        flash(f'Volunteer {volunteer.name} has been suspended', 'warning')
    else:
        volunteer.status = 'active'
        flash(f'Volunteer {volunteer.name} has been reactivated', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_volunteers'))


@app.route('/admin/delete-volunteer/<int:volunteer_id>', methods=['POST'])
@login_required
def admin_delete_volunteer(volunteer_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    
    # Check if volunteer has pending or in-progress requests
    active_requests = Request.query.filter_by(volunteer_id=volunteer_id).filter(
        Request.status.in_(['matched', 'in_progress', 'awaiting'])
    ).count()
    
    if active_requests > 0:
        flash(f'Cannot delete volunteer {volunteer.name}. They have {active_requests} active request(s). Please complete or cancel them first, or suspend the account instead.', 'danger')
        return redirect(url_for('admin_volunteers'))
    
    # Update completed requests to remove volunteer reference but keep history
    completed_requests = Request.query.filter_by(volunteer_id=volunteer_id).all()
    for req in completed_requests:
        req.volunteer_id = None
    
    # Delete volunteer's feedback received
    feedbacks = Feedback.query.filter_by(volunteer_id=volunteer_id).all()
    for feedback in feedbacks:
        db.session.delete(feedback)
    
    # Delete volunteer's chat messages
    ChatMessage.query.filter_by(participant_id=volunteer_id, participant_type='volunteer').delete()
    
    db.session.delete(volunteer)
    db.session.commit()
    
    flash(f'Volunteer {volunteer.name} has been permanently deleted', 'success')
    return redirect(url_for('admin_volunteers'))


@app.route('/admin/requests')
@login_required
def admin_requests():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    filter_status = request.args.get('filter')
    single_request_id = request.args.get('request_id')
    
    if single_request_id:
        # Show a single specific request
        requests_list = Request.query.filter_by(id=int(single_request_id)).all()
    elif filter_status:
        requests_list = Request.query.filter_by(status=filter_status).order_by(Request.created_date.desc()).all()
    else:
        # Don't show pending/saved searches - only actual requests
        requests_list = Request.query.filter(Request.status != 'pending').order_by(Request.created_date.desc()).all()
    
    return render_template('admin/requests.html', requests=requests_list, filter=filter_status, single_request_id=single_request_id)


@app.route('/create-request', methods=['GET', 'POST'])
@login_required
def create_request():
    if current_user.user_type != 'user':
        flash('Only service users can create requests', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = int(current_user.id.split('_')[1])
        
        # Clean up old unsaved searches (older than 1 hour)
        one_hour_ago = uk_now() - timedelta(hours=1)
        Request.query.filter(
            Request.user_id == user_id,
            Request.status == 'pending',
            Request.is_saved == False,
            Request.created_date < one_hour_ago
        ).delete()
        db.session.commit()

        # Calculate urgency server-side based on preferred date
        try:
            selected_date = datetime.strptime(request.form.get('preferred_date'), '%Y-%m-%d').date()
            today = uk_now().date()
            diff_days = (selected_date - today).days
            if diff_days < 1:
                flash('Please select a future date.', 'danger')
                return redirect(url_for('create_request'))
            if diff_days <= 7:
                computed_urgency = 'High'
            elif diff_days <= 13:
                computed_urgency = 'Medium'
            else:
                computed_urgency = 'Low'
        except (ValueError, TypeError):
            computed_urgency = request.form.get('urgency', 'Medium')

        new_request = Request(
            user_id=user_id,
            support_type=request.form.get('support_type'),
            description=request.form.get('description'),
            urgency=computed_urgency,
            preferred_date=request.form.get('preferred_date'),
            time_slot=request.form.get('time_slot'),
            is_saved=False  # Not saved by default - user must click save button
        )

        db.session.add(new_request)
        db.session.commit()

        return redirect(url_for('select_volunteer', request_id=new_request.id))

    # Pre-fill from URL params (from re-search notification)
    prefill = {
        'support_type': request.args.get('support_type', ''),
        'description': request.args.get('description', ''),
        'preferred_date': request.args.get('preferred_date', ''),
        'time_slot': request.args.get('time_slot', ''),
        'urgency': request.args.get('urgency', 'Medium')
    }
    
    return render_template('user/create_request.html', prefill=prefill)


@app.route('/select-volunteer/<int:request_id>')
@login_required
def select_volunteer(request_id):
    if current_user.user_type != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    request_obj = Request.query.get_or_404(request_id)
    user_id = int(current_user.id.split('_')[1])
    user = ServiceUser.query.get(user_id)

    # Get all active volunteers
    all_volunteers = Volunteer.query.filter_by(status='active').all()
    
    # OPTIMIZED ALGORITHM: Calculate distance first, then check availability in order
    volunteers_with_distance = []
    user_coords = None
    
    # Get user coordinates once
    if user.latitude and user.longitude:
        user_coords = (user.latitude, user.longitude)
    else:
        user_coords = get_coordinates(user.postcode)
    
    # Calculate distance for all volunteers
    if user_coords:
        for volunteer in all_volunteers:
            vol_coords = None
            if volunteer.latitude and volunteer.longitude:
                vol_coords = (volunteer.latitude, volunteer.longitude)
            else:
                vol_coords = get_coordinates(volunteer.postcode)
            
            if vol_coords:
                distance = geodesic(user_coords, vol_coords).miles
                volunteers_with_distance.append({
                    'volunteer': volunteer,
                    'distance': round(distance, 2)
                })
        
        # Sort by distance (closest first)
        volunteers_with_distance.sort(key=lambda x: x['distance'])
    else:
        # Fallback if no coordinates
        volunteers_with_distance = [{'volunteer': v, 'distance': 'N/A'} for v in all_volunteers]
    
    # Now check availability and skills in order, stop at 5 good matches
    available_matches = []
    unavailable_matches = []
    
    for vol_data in volunteers_with_distance:
        volunteer = vol_data['volunteer']
        distance = vol_data['distance']
        
        # Calculate full match score
        score, details = calculate_match_score(volunteer, request_obj, user)
        
        match_data = {
            'volunteer': volunteer,
            'score': score,
            'distance': distance,
            'skills': details.get('skills_match', ''),
            'is_available': details.get('is_available', False),
            'has_skill': details.get('has_skill', False),
            'availability_match': details.get('availability_match', ''),
            'volunteer_slot': details.get('volunteer_slot', ''),
            'badge_type': details.get('badge_type', 'day_unavailable')
        }
        
        if match_data['is_available']:
            available_matches.append(match_data)
        else:
            # Keep some unavailable for backup (max 3)
            if len(unavailable_matches) < 5:
                unavailable_matches.append(match_data)
    
    # If we don't have 5 available, continue checking for unavailable
    if len(available_matches) < 10 and len(unavailable_matches) < 5:
        for vol_data in volunteers_with_distance[len(available_matches) + len(unavailable_matches):]:
            if len(unavailable_matches) >= 3:
                break
            
            volunteer = vol_data['volunteer']
            distance = vol_data['distance']
            score, details = calculate_match_score(volunteer, request_obj, user)
            
            match_data = {
                'volunteer': volunteer,
                'score': score,
                'distance': distance,
                'skills': details.get('skills_match', ''),
                'is_available': details.get('is_available', False),
                'has_skill': details.get('has_skill', False),
                'availability_match': details.get('availability_match', ''),
                'volunteer_slot': details.get('volunteer_slot', ''),
                'badge_type': details.get('badge_type', 'day_unavailable')
            }
            
            if not match_data['is_available']:
                unavailable_matches.append(match_data)
    
    # Combine: available first, then unavailable - SORTED BY SCORE
    available_matches.sort(key=lambda x: x['score'], reverse=True)
    unavailable_matches.sort(key=lambda x: x['score'], reverse=True)
    
    top_matches = available_matches.copy()
    if len(top_matches) < 5:
        top_matches.extend(unavailable_matches[:5-len(top_matches)])
    
    has_available = len(available_matches) > 0

    # Determine if any volunteer is available on this day (even if different time slot)
    has_day_available = any(
        m.get('volunteer_slot', 'Not Available') != 'Not Available' and m.get('volunteer_slot', '') != 'Booked'
        for m in available_matches + unavailable_matches
    )
    
    # Determine match scenario for message display:
    # "perfect" = volunteers available in requested time slot
    # "different_slot" = volunteers available on same day but different time slot
    # "day_unavailable" = no volunteers available on the day at all
    if has_available:
        match_scenario = "perfect"
    elif has_day_available:
        match_scenario = "different_slot"
    else:
        match_scenario = "day_unavailable"

    return render_template('user/select_volunteer.html',
                           request=request_obj,
                           matches=top_matches,
                           has_available=has_available,
                           has_day_available=has_day_available,
                           total_available=len(available_matches),
                           match_scenario=match_scenario)


@app.route('/save-search/<int:request_id>')
@login_required
def save_search(request_id):
    """Toggle save/unsave search results (AJAX endpoint)"""
    if current_user.user_type != 'user':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    request_obj = Request.query.get_or_404(request_id)
    user_id = int(current_user.id.split('_')[1])
    
    # Verify ownership
    if request_obj.user_id != user_id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Toggle saved status
    request_obj.is_saved = not request_obj.is_saved
    db.session.commit()
    
    message = 'Search results saved!' if request_obj.is_saved else 'Search removed from saved'
    return jsonify({'success': True, 'message': message, 'is_saved': request_obj.is_saved})


@app.route('/confirm-volunteer/<int:request_id>/<int:volunteer_id>')
@login_required
def confirm_volunteer(request_id, volunteer_id):
    if current_user.user_type != 'user':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    request_obj = Request.query.get_or_404(request_id)
    
    # Verify this request belongs to the current user
    user_id = int(current_user.id.split('_')[1])
    if request_obj.user_id != user_id:
        flash('Access denied', 'danger')
        return redirect(url_for('user_dashboard'))
    
    # If user chose a different time slot (for different_slot scenario)
    new_time_slot = request.args.get('time_slot')
    chosen_slot = request_obj.time_slot
    if new_time_slot and new_time_slot in ['09:00-12:00', '12:00-15:00', '15:00-18:00']:
        chosen_slot = new_time_slot

    # If this is a saved search, create a NEW request for the booking and keep the saved search
    if request_obj.is_saved and request_obj.status == 'pending':
        new_request = Request(
            user_id=request_obj.user_id,
            support_type=request_obj.support_type,
            description=request_obj.description,
            preferred_date=request_obj.preferred_date,
            time_slot=chosen_slot,
            urgency=request_obj.urgency,
            volunteer_id=volunteer_id,
            status='awaiting',
            is_saved=False,
            matched_date=uk_now()
        )
        db.session.add(new_request)
        
        # Notify volunteer
        create_notification(
            recipient_id=volunteer_id,
            recipient_type='volunteer',
            title='New Request Assigned',
            message=f'{current_user.name} has selected you for a {new_request.support_type} request on {fmt_date(new_request.preferred_date)}.',
            link=None
        )
        
        db.session.commit()
        flash('Volunteer selected! Your saved search has been kept.', 'success')
        return redirect(url_for('user_dashboard', tab='awaiting'))
    
    # Normal (non-saved) request - convert directly
    if chosen_slot != request_obj.time_slot:
        request_obj.time_slot = chosen_slot
    request_obj.volunteer_id = volunteer_id
    request_obj.status = 'awaiting'
    request_obj.matched_date = uk_now()

    # Notify volunteer
    create_notification(
        recipient_id=volunteer_id,
        recipient_type='volunteer',
        title='New Request Assigned',
        message=f'{current_user.name} has selected you for a {request_obj.support_type} request on {fmt_date(request_obj.preferred_date)}.',
        link=None
    )

    db.session.commit()

    flash('Volunteer selected! Waiting for volunteer to accept.', 'success')
    return redirect(url_for('user_dashboard', tab='awaiting'))


@app.route('/accept-request/<int:request_id>')
@login_required
def accept_request(request_id):
    if current_user.user_type != 'volunteer':
        flash('Only volunteers can accept requests', 'danger')
        return redirect(url_for('index'))

    request_obj = Request.query.get_or_404(request_id)
    
    # Verify this request is assigned to this volunteer
    volunteer_id = int(current_user.id.split('_')[1])
    if request_obj.volunteer_id != volunteer_id:
        flash('Access denied', 'danger')
        return redirect(url_for('volunteer_dashboard'))
    
    if request_obj.status != 'awaiting':
        flash('This request cannot be accepted', 'warning')
        return redirect(url_for('volunteer_dashboard'))
    
    # Block accepting requests with past dates
    today = uk_now().strftime('%Y-%m-%d')
    if request_obj.preferred_date and request_obj.preferred_date < today:
        flash('This request has expired — the requested date has passed.', 'warning')
        return redirect(url_for('volunteer_dashboard'))
    
    request_obj.status = 'in_progress'

    # Notify user that volunteer accepted
    create_notification(
        recipient_id=request_obj.user_id,
        recipient_type='user',
        title='Request Accepted!',
        message=f'{current_user.name} has accepted your {request_obj.support_type} request for {fmt_date(request_obj.preferred_date)}.',
        link=None
    )

    db.session.commit()
    flash('Request accepted!', 'success')
    return redirect(url_for('volunteer_dashboard', tab='awaiting'))


@app.route('/complete-request/<int:request_id>')
@login_required
def complete_request(request_id):
    if current_user.user_type != 'volunteer':
        flash('Only volunteers can complete requests', 'danger')
        return redirect(url_for('index'))

    request_obj = Request.query.get_or_404(request_id)
    
    # Verify this request is assigned to this volunteer
    volunteer_id = int(current_user.id.split('_')[1])
    if request_obj.volunteer_id != volunteer_id:
        flash('Access denied', 'danger')
        return redirect(url_for('volunteer_dashboard'))
    
    if request_obj.status != 'in_progress':
        flash('This request cannot be completed', 'warning')
        return redirect(url_for('volunteer_dashboard'))
    
    request_obj.status = 'completed'
    request_obj.completed_date = uk_now()

    # Update volunteer stats
    volunteer = Volunteer.query.get(volunteer_id)
    volunteer.total_completed += 1

    # Notify user that request is completed
    create_notification(
        recipient_id=request_obj.user_id,
        recipient_type='user',
        title='Request Completed',
        message=f'{current_user.name} has completed your {request_obj.support_type} request. You can now leave feedback!',
        link=f'/leave-feedback/{request_id}'
    )

    db.session.commit()
    flash('Request marked as completed!', 'success')
    return redirect(url_for('volunteer_dashboard', tab='progress'))


@app.route('/admin/cancel-request/<int:request_id>', methods=['POST'])
@login_required
def admin_cancel_request(request_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    req = Request.query.get_or_404(request_id)
    # Save volunteer name before cancelling
    volunteer_name = None
    if req.volunteer:
        req.cancelled_volunteer_name = req.volunteer.name
        volunteer_name = req.volunteer.name
    req.status = 'cancelled'
    if volunteer_name:
        req.cancelled_by_name = f"{volunteer_name} (Volunteer)"
    else:
        req.cancelled_by_name = f"Admin ({current_user.name})"
    req.cancelled_date = uk_now()
    
    # Auto-reply in chat for cancellation
    cancel_chats = ChatMessage.query.filter_by(linked_request_id=request_id).all()
    if cancel_chats:
        last_chat = cancel_chats[-1]
        auto_reply = ChatMessage(
            participant_id=last_chat.participant_id,
            participant_type=last_chat.participant_type,
            sender_type='admin',
            sender_name='Admin',
            message=f'Request #{request_id} has been cancelled as requested. The service user will be notified.',
            linked_request_id=request_id
        )
        db.session.add(auto_reply)
    
    # Notify the volunteer
    if req.volunteer_id:
        re_search_link = f"/create-request?support_type={req.support_type}&description={req.description}&preferred_date={req.preferred_date}&time_slot={req.time_slot}&urgency={req.urgency}"
        create_notification(
            recipient_id=req.volunteer_id,
            recipient_type='volunteer',
            title='Request Cancelled by Admin',
            message=f'Admin has cancelled booking #{request_id} ({req.support_type}) as you requested.',
            link=None
        )
        # Notify the user - show volunteer name, not admin
        create_notification(
            recipient_id=req.user_id,
            recipient_type='user',
            title='Booking Cancelled',
            message=f'Your {req.support_type} booking for {fmt_date(req.preferred_date)} has been cancelled by {volunteer_name or "the volunteer"}.',
            link=re_search_link,
            link_expires=str(req.preferred_date)
        )
    
    db.session.commit()
    
    flash(f'Request #{request_id} cancelled successfully.', 'success')
    # Return to where admin came from
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for('admin_requests'))


# ============ NOTIFICATION SYSTEM ============

@app.route('/notifications')
@login_required
def notifications():
    actual_id = int(current_user.id.split('_')[1])
    all_notifications = Notification.query.filter_by(
        recipient_id=actual_id,
        recipient_type=current_user.user_type
    ).order_by(Notification.created_date.desc()).all()
    
    # Mark all as read when visiting the page
    for n in all_notifications:
        if not n.is_read:
            n.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', notifications=all_notifications, today=uk_now().strftime('%Y-%m-%d'))


@app.route('/notifications/<int:notif_id>/read')
@login_required
def read_notification(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    
    # Verify ownership
    actual_id = int(current_user.id.split('_')[1])
    if notif.recipient_id != actual_id or notif.recipient_type != current_user.user_type:
        flash('Access denied', 'danger')
        return redirect(url_for('notifications'))
    
    notif.is_read = True
    db.session.commit()
    
    # Redirect to the linked page if available
    if notif.link:
        return redirect(notif.link)
    return redirect(url_for('notifications'))


@app.route('/notifications/mark-all-read')
@login_required
def mark_all_notifications_read():
    actual_id = int(current_user.id.split('_')[1])
    Notification.query.filter_by(
        recipient_id=actual_id,
        recipient_type=current_user.user_type,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('notifications'))


# ============ MESSAGING SYSTEM ============


# ============ SUPPORT CHAT SYSTEM ============

@app.route('/support-chat', methods=['GET', 'POST'])
@login_required
def support_chat():
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_conversations'))
    
    my_id = int(current_user.id.split('_')[1])
    my_type = current_user.user_type
    
    if request.method == 'POST':
        message_text = request.form.get('message', '').strip()
        linked_request_id = request.form.get('linked_request_id') or None
        
        if message_text:
            new_msg = ChatMessage(
                participant_id=my_id,
                participant_type=my_type,
                sender_type=my_type,
                sender_name=current_user.name,
                message=message_text,
                linked_request_id=int(linked_request_id) if linked_request_id else None
            )
            db.session.add(new_msg)
            
            # Notify admin
            admins = Admin.query.all()
            for admin in admins:
                # If cancellation request, link directly to the request
                if linked_request_id:
                    notif_link = f'/admin/requests?request_id={linked_request_id}'
                    notif_title = f'Cancellation Request from {current_user.name}'
                    notif_msg = f'{current_user.name} is requesting cancellation of Request #{linked_request_id}. Check chat for details.'
                else:
                    notif_link = f'/admin/chat/{my_type}/{my_id}'
                    notif_title = f'New message from {current_user.name}'
                    notif_msg = f'You have a new support chat message from {current_user.name}.'
                
                create_notification(
                    recipient_id=admin.id,
                    recipient_type='admin',
                    title=notif_title,
                    message=notif_msg,
                    link=notif_link
                )
            
            db.session.commit()
        
        return redirect(url_for('support_chat'))
    
    # Pre-fill from URL params (e.g. from 48h cancellation link)
    prefill_message = ''
    prefill_request_id = request.args.get('request_id', '')
    if prefill_request_id:
        req_obj = Request.query.get(prefill_request_id)
        if req_obj:
            prefill_message = f"I need to cancel Request #{req_obj.id} ({req_obj.support_type} on {fmt_date(req_obj.preferred_date)}). Less than 48 hours remaining - please action this cancellation."
    
    # Get all chat messages for this conversation
    messages = ChatMessage.query.filter_by(
        participant_id=my_id,
        participant_type=my_type
    ).order_by(ChatMessage.created_date.asc()).all()
    
    # Mark admin messages as read
    for msg in messages:
        if msg.sender_type == 'admin' and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    return render_template('support_chat.html', 
                           messages=messages,
                           prefill_message=prefill_message,
                           prefill_request_id=prefill_request_id)


@app.route('/support-chat/clear', methods=['POST'])
@login_required
def clear_chat():
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_conversations'))
    
    my_id = int(current_user.id.split('_')[1])
    my_type = current_user.user_type
    
    ChatMessage.query.filter_by(
        participant_id=my_id,
        participant_type=my_type
    ).delete()
    db.session.commit()
    
    flash('Chat history cleared.', 'info')
    return redirect(url_for('support_chat'))


# ============ ADMIN CHAT ROUTES ============

@app.route('/admin/conversations')
@login_required
def admin_conversations():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get unique conversations (grouped by participant)
    from sqlalchemy import func
    conversations = db.session.query(
        ChatMessage.participant_id,
        ChatMessage.participant_type,
        func.max(ChatMessage.created_date).label('last_date'),
        func.count(ChatMessage.id).label('msg_count')
    ).group_by(
        ChatMessage.participant_id,
        ChatMessage.participant_type
    ).order_by(func.max(ChatMessage.created_date).desc()).all()
    
    # Build conversation list with details
    conv_list = []
    for conv in conversations:
        # Get participant name
        if conv.participant_type == 'user':
            participant = ServiceUser.query.get(conv.participant_id)
        else:
            participant = Volunteer.query.get(conv.participant_id)
        
        if not participant:
            continue
        
        # Get last message
        last_msg = ChatMessage.query.filter_by(
            participant_id=conv.participant_id,
            participant_type=conv.participant_type
        ).order_by(ChatMessage.created_date.desc()).first()
        
        # Count unread (messages from user/volunteer that admin hasn't read)
        unread = ChatMessage.query.filter_by(
            participant_id=conv.participant_id,
            participant_type=conv.participant_type,
            is_read=False
        ).filter(ChatMessage.sender_type != 'admin').count()
        
        conv_list.append({
            'participant_id': conv.participant_id,
            'participant_type': conv.participant_type,
            'participant_name': participant.name,
            'last_message': last_msg.message[:80] + '...' if len(last_msg.message) > 80 else last_msg.message,
            'last_date': last_msg.created_date,
            'last_sender': last_msg.sender_type,
            'msg_count': conv.msg_count,
            'unread': unread
        })
    
    return render_template('admin/conversations.html', conversations=conv_list)


@app.route('/admin/chat/<participant_type>/<int:participant_id>', methods=['GET', 'POST'])
@login_required
def admin_chat(participant_type, participant_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get participant info
    if participant_type == 'user':
        participant = ServiceUser.query.get_or_404(participant_id)
    else:
        participant = Volunteer.query.get_or_404(participant_id)
    
    if request.method == 'POST':
        message_text = request.form.get('message', '').strip()
        if message_text:
            new_msg = ChatMessage(
                participant_id=participant_id,
                participant_type=participant_type,
                sender_type='admin',
                sender_name=current_user.name,
                message=message_text
            )
            db.session.add(new_msg)
            
            # Notify the participant
            create_notification(
                recipient_id=participant_id,
                recipient_type=participant_type,
                title=f'New message from Admin',
                message=f'You have a new support chat message.',
                link='/support-chat'
            )
            
            db.session.commit()
        
        return redirect(url_for('admin_chat', participant_type=participant_type, participant_id=participant_id))
    
    # Get all messages in this conversation
    messages = ChatMessage.query.filter_by(
        participant_id=participant_id,
        participant_type=participant_type
    ).order_by(ChatMessage.created_date.asc()).all()
    
    # Mark messages as read
    for msg in messages:
        if msg.sender_type != 'admin' and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    return render_template('admin/chat.html', 
                           messages=messages,
                           participant=participant,
                           participant_type=participant_type)


@app.route('/admin/chat/<participant_type>/<int:participant_id>/delete', methods=['POST'])
@login_required
def admin_delete_conversation(participant_type, participant_id):
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    ChatMessage.query.filter_by(
        participant_id=participant_id,
        participant_type=participant_type
    ).delete()
    db.session.commit()
    
    flash('Conversation deleted.', 'info')
    return redirect(url_for('admin_conversations'))


@app.route('/admin/conversations/clear', methods=['POST'])
@login_required
def admin_clear_all_conversations():
    if current_user.user_type != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    ChatMessage.query.delete()
    db.session.commit()
    
    flash('All conversations cleared.', 'info')
    return redirect(url_for('admin_conversations'))


# ============ FEEDBACK SYSTEM ============

@app.route('/leave-feedback/<int:request_id>', methods=['GET', 'POST'])
@login_required
def leave_feedback(request_id):
    if current_user.user_type != 'user':
        flash('Only service users can leave feedback', 'danger')
        return redirect(url_for('index'))
    
    request_obj = Request.query.get_or_404(request_id)
    
    # Check if request is completed
    if request_obj.status != 'completed':
        flash('You can only leave feedback for completed requests', 'warning')
        return redirect(url_for('user_dashboard'))
    
    # Check if feedback already exists
    existing_feedback = Feedback.query.filter_by(request_id=request_id).first()
    if existing_feedback:
        flash('You have already left feedback for this request', 'info')
        return redirect(url_for('user_dashboard'))
    
    # Get volunteer info
    volunteer = Volunteer.query.get(request_obj.volunteer_id)
    
    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')
        
        user_id = int(current_user.id.split('_')[1])
        
        new_feedback = Feedback(
            request_id=request_id,
            user_id=user_id,
            volunteer_id=request_obj.volunteer_id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(new_feedback)
        
        # Update volunteer's average rating
        all_feedback = Feedback.query.filter_by(volunteer_id=request_obj.volunteer_id).all()
        total_ratings = sum(f.rating for f in all_feedback) + rating
        count = len(all_feedback) + 1
        volunteer.average_rating = round(total_ratings / count, 1)
        
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('user_dashboard', tab='completed'))
    
    return render_template('user/leave_feedback.html', 
                           request=request_obj,
                           volunteer=volunteer)


@app.route('/volunteer/my-reviews')
@login_required
def volunteer_reviews():
    if current_user.user_type != 'volunteer':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    volunteer_id = int(current_user.id.split('_')[1])
    volunteer = Volunteer.query.get(volunteer_id)
    reviews = Feedback.query.filter_by(volunteer_id=volunteer_id).order_by(Feedback.created_date.desc()).all()
    
    return render_template('volunteer/reviews.html',
                           volunteer=volunteer,
                           reviews=reviews)


# ============ CANCEL/DELETE REQUEST ============

@app.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    req = Request.query.get_or_404(request_id)

    def _num_id(v):
        try:
            return int(str(v).split('_')[1])
        except Exception:
            return None

    status = (req.status or '').lower()

    if current_user.user_type == 'user':
        uid = _num_id(current_user.id)
        if uid != req.user_id:
            flash('Access denied', 'danger')
            return redirect(url_for('user_dashboard'))
        
        # User can hide cancelled requests (admin still sees them)
        if status == 'cancelled':
            req.hidden_by_user = True
            db.session.commit()
            flash('Request removed!', 'success')
            return redirect(url_for('user_dashboard', tab='cancelled'))
        
        # Saved searches (pending) - just delete them, don't cancel
        if status == 'pending':
            db.session.delete(req)
            db.session.commit()
            flash('Saved search deleted!', 'success')
            return redirect(url_for('user_dashboard', tab='saved'))
        
        # Awaiting (not yet accepted) - delete, no booking exists yet
        if status == 'awaiting':
            # Notify volunteer that request was withdrawn
            if req.volunteer_id:
                create_notification(
                    recipient_id=req.volunteer_id,
                    recipient_type='volunteer',
                    title='Request Withdrawn',
                    message=f'{current_user.name} has withdrawn their {req.support_type} request for {fmt_date(req.preferred_date)}.',
                    link=None
                )
            db.session.delete(req)
            db.session.commit()
            flash('Request withdrawn!', 'success')
            return redirect(url_for('user_dashboard', tab='awaiting'))
        
        # Only in_progress can be cancelled (actual booking exists)
        if status != 'in_progress':
            flash('Cannot cancel this request', 'warning')
            return redirect(url_for('user_dashboard'))
        
        # Mark as cancelled - save who cancelled
        req.status = 'cancelled'
        req.cancelled_by_name = f"{current_user.name} (User)"
        req.cancelled_date = uk_now()
        # Save volunteer name for audit trail
        if req.volunteer:
            req.cancelled_volunteer_name = req.volunteer.name
        
        # Notify volunteer
        if req.volunteer_id:
            create_notification(
                recipient_id=req.volunteer_id,
                recipient_type='volunteer',
                title='Booking Cancelled',
                message=f'{current_user.name} has cancelled their {req.support_type} booking for {fmt_date(req.preferred_date)}.',
                link=None
            )
        
        db.session.commit()
        flash('Request cancelled successfully!', 'success')
        return redirect(url_for('user_dashboard', tab='progress'))

    if current_user.user_type == 'volunteer':
        vid = _num_id(current_user.id)
        if vid != req.volunteer_id:
            flash('Access denied', 'danger')
            return redirect(url_for('volunteer_dashboard'))
        
        # Allow volunteer to HIDE cancelled requests from their dashboard
        if status == 'cancelled':
            req.hidden_by_volunteer = True
            db.session.commit()
            flash('Request removed!', 'success')
            return redirect(url_for('volunteer_dashboard', tab='cancelled'))
        
        if status not in ['awaiting', 'in_progress']:
            flash('Cannot cancel this request', 'warning')
            return redirect(url_for('volunteer_dashboard'))
        
        # Re-search link for user notification
        re_search_link = f"/create-request?support_type={req.support_type}&description={req.description}&preferred_date={req.preferred_date}&time_slot={req.time_slot}&urgency={req.urgency}"
        
        # Awaiting (not yet accepted) - decline and delete, no booking exists
        if status == 'awaiting':
            create_notification(
                recipient_id=req.user_id,
                recipient_type='user',
                title='Volunteer Declined Your Request',
                message=f'{current_user.name} has declined your {req.support_type} request for {fmt_date(req.preferred_date)}.',
                link=re_search_link,
                link_expires=str(req.preferred_date)
            )
            db.session.delete(req)
            db.session.commit()
            flash('Request declined.', 'info')
            return redirect(url_for('volunteer_dashboard', tab='awaiting'))
        
        # For in_progress, check 48h restriction
        if not req.can_volunteer_cancel:
            flash('Cannot cancel - less than 48 hours before booking. Contact Admin.', 'danger')
            return redirect(url_for('volunteer_dashboard', tab='progress'))
        
        # Cancel in_progress booking - keep record for audit trail
        req.cancelled_by_name = f"{current_user.name} (Volunteer)"
        req.cancelled_volunteer_name = current_user.name
        req.status = 'cancelled'
        req.cancelled_date = uk_now()
        
        create_notification(
            recipient_id=req.user_id,
            recipient_type='user',
            title='Booking Cancelled by Volunteer',
            message=f'{current_user.name} has cancelled your {req.support_type} booking for {fmt_date(req.preferred_date)}.',
            link=re_search_link,
            link_expires=str(req.preferred_date)
        )
        
        db.session.commit()
        flash('Booking cancelled.', 'info')
        return redirect(url_for('volunteer_dashboard', tab='progress'))

    flash('Access denied', 'danger')
    return redirect(url_for('index'))


# ============ BULK REMOVE ROUTES ============

@app.route('/clear-cancelled', methods=['POST'])
@login_required
def clear_cancelled():
    """Remove all cancelled requests from dashboard"""
    if current_user.user_type == 'user':
        user_id = int(current_user.id.split('_')[1])
        cancelled = Request.query.filter_by(user_id=user_id, status='cancelled', hidden_by_user=False).all()
        for req in cancelled:
            req.hidden_by_user = True
        db.session.commit()
        flash(f'{len(cancelled)} cancelled request(s) removed.', 'success')
        return redirect(url_for('user_dashboard', tab='cancelled'))
    
    elif current_user.user_type == 'volunteer':
        vol_id = int(current_user.id.split('_')[1])
        cancelled = Request.query.filter_by(volunteer_id=vol_id, status='cancelled', hidden_by_volunteer=False).all()
        for req in cancelled:
            req.hidden_by_volunteer = True
        db.session.commit()
        flash(f'{len(cancelled)} cancelled request(s) removed.', 'success')
        return redirect(url_for('volunteer_dashboard', tab='cancelled'))
    
    return redirect(url_for('index'))


@app.route('/clear-completed', methods=['POST'])
@login_required
def clear_completed():
    """Remove all completed requests from volunteer dashboard"""
    if current_user.user_type != 'volunteer':
        return redirect(url_for('index'))
    
    vol_id = int(current_user.id.split('_')[1])
    completed = Request.query.filter_by(volunteer_id=vol_id, status='completed', hidden_by_volunteer=False).all()
    for req in completed:
        req.hidden_by_volunteer = True
    db.session.commit()
    flash(f'{len(completed)} completed request(s) removed.', 'success')
    return redirect(url_for('volunteer_dashboard', tab='completed'))


@app.route('/clear-notifications', methods=['POST'])
@login_required
def clear_notifications():
    """Delete all notifications for current user"""
    user_id = int(current_user.id.split('_')[1])
    user_type = current_user.user_type
    
    deleted = Notification.query.filter_by(recipient_id=user_id, recipient_type=user_type).delete()
    db.session.commit()
    flash(f'{deleted} notification(s) cleared.', 'success')
    return redirect(url_for('notifications'))


@app.route('/delete-notification/<int:notif_id>', methods=['POST'])
@login_required
def delete_notification(notif_id):
    """Delete a single notification"""
    user_id = int(current_user.id.split('_')[1])
    user_type = current_user.user_type
    
    notif = Notification.query.filter_by(id=notif_id, recipient_id=user_id, recipient_type=user_type).first()
    if notif:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('notifications'))


@app.route('/hide-completed/<int:request_id>', methods=['POST'])
@login_required
def hide_completed(request_id):
    """Hide a single completed request from volunteer dashboard"""
    if current_user.user_type != 'volunteer':
        return redirect(url_for('index'))
    
    vol_id = int(current_user.id.split('_')[1])
    req = Request.query.filter_by(id=request_id, volunteer_id=vol_id, status='completed').first()
    if req:
        req.hidden_by_volunteer = True
        db.session.commit()
    return redirect(url_for('volunteer_dashboard', tab='completed'))


@app.route('/user/hide-completed/<int:request_id>', methods=['POST'])
@login_required
def user_hide_completed(request_id):
    """Hide a single completed request from user dashboard"""
    if current_user.user_type != 'user':
        return redirect(url_for('index'))
    
    user_id = int(current_user.id.split('_')[1])
    req = Request.query.filter_by(id=request_id, user_id=user_id, status='completed').first()
    if req:
        req.hidden_by_user = True
        db.session.commit()
    return redirect(url_for('user_dashboard', tab='completed'))


@app.route('/user/clear-completed', methods=['POST'])
@login_required
def user_clear_completed():
    """Remove all completed requests from user dashboard"""
    if current_user.user_type != 'user':
        return redirect(url_for('index'))
    
    user_id = int(current_user.id.split('_')[1])
    completed = Request.query.filter_by(user_id=user_id, status='completed', hidden_by_user=False).all()
    for req in completed:
        req.hidden_by_user = True
    db.session.commit()
    flash(f'{len(completed)} completed request(s) removed.', 'success')
    return redirect(url_for('user_dashboard', tab='completed'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin if not exists
        if not Admin.query.filter_by(email='2245801@student.uwtsd.ac.uk').first():
            admin = Admin(
                name='Rita Zambito',
                email='2245801@student.uwtsd.ac.uk',
                password=generate_password_hash('Admin123!')
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin account created!")
        
        # Auto-fix: Add coordinates to users/volunteers that don't have them
        print("\nChecking for missing coordinates...")
        fixed_count = 0
        
        # Fix ServiceUsers
        users_without_coords = ServiceUser.query.filter(
            (ServiceUser.latitude == None) | (ServiceUser.longitude == None)
        ).all()
        
        for user in users_without_coords:
            if user.postcode:
                coords = get_coordinates(user.postcode)
                if coords:
                    user.latitude = coords[0]
                    user.longitude = coords[1]
                    fixed_count += 1
                    print(f"  ✓ Fixed coordinates for user: {user.name}")
        
        # Fix Volunteers
        vols_without_coords = Volunteer.query.filter(
            (Volunteer.latitude == None) | (Volunteer.longitude == None)
        ).all()
        
        for vol in vols_without_coords:
            if vol.postcode:
                coords = get_coordinates(vol.postcode)
                if coords:
                    vol.latitude = coords[0]
                    vol.longitude = coords[1]
                    fixed_count += 1
                    print(f"  ✓ Fixed coordinates for volunteer: {vol.name}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✓ Fixed {fixed_count} missing coordinates!\n")
        else:
            print("✓ All coordinates are up to date!\n")

    app.run(debug=True)
