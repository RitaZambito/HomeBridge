# 🏠 HomeBridge

**A Smart Volunteer Matching Platform for Domestic Support**

HomeBridge is a web-based platform that automates the process of connecting vulnerable individuals — including older adults, people with disabilities, and those affected by hoarding disorder — with local volunteers who can provide domestic cleaning and household assistance.

Developed as an Individual Project (Dissertation) for BSc Applied Computing at the University of Wales Trinity Saint David (UWTSD).

---

## ✨ Key Features

- **Weighted Multi-Factor Matching Algorithm** — Scores volunteers out of 100 points based on geographical proximity, availability alignment, skill match, and user rating, with coordinate caching for instantaneous results.
- **Three User Roles** — Service users, volunteers, and administrators, each with a dedicated dashboard ("My Space").
- **48-Hour Cancellation Protection** — Prevents volunteers from cancelling bookings within 48 hours of the scheduled date, safeguarding vulnerable users from last-minute disruption.
- **Contextual Notification System** — Action-linked notifications with automatic link expiry for passed dates.
- **Admin Support Chat** — WhatsApp-style messaging between administrators and users/volunteers, linked to specific booking requests.
- **Full Booking Lifecycle** — From search to completion or cancellation, with comprehensive audit trails.
- **UK-Wide Geocoding** — Postcodes.io API integration with coordinate caching for fast distance calculations.
- **Accessibility First** — WCAG 2.2 compliant design with skip-to-content links, ARIA labels, visible focus indicators, and reduced-motion support.
- **Responsive Design** — Fully responsive across desktop, tablet, and mobile with three CSS breakpoint layers.

---

## 🛠️ Technologies Used

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF |
| Database     | SQLite                              |
| Frontend     | Bootstrap 5, Custom CSS, JavaScript |
| Geocoding    | Postcodes.io API, geopy             |
| Security     | Werkzeug password hashing, CSRF protection, session management |

---

## 📁 Project Structure

```
HomeBridge/
├── static/
│   └── images/
│       └── logo.png
├── templates/
│   ├── admin/
│   │   ├── chat.html
│   │   ├── conversations.html
│   │   ├── dashboard.html
│   │   ├── messages.html
│   │   ├── requests.html
│   │   ├── users.html
│   │   ├── view_message.html
│   │   └── volunteers.html
│   ├── user/
│   │   ├── create_request.html
│   │   ├── dashboard.html
│   │   ├── edit_profile.html
│   │   ├── leave_feedback.html
│   │   ├── profile.html
│   │   └── select_volunteer.html
│   ├── volunteer/
│   │   ├── dashboard.html
│   │   ├── edit_profile.html
│   │   ├── profile.html
│   │   └── reviews.html
│   ├── base.html
│   ├── contact_admin.html
│   ├── index.html
│   ├── login.html
│   ├── my_messages.html
│   ├── notifications.html
│   ├── register.html
│   ├── support_chat.html
│   └── view_my_message.html
├── app.py                     # Main Flask application (routes, models, logic)
└── populate_database.py       # Seed script for 50 simulated test users
```

---

## ⚙️ Installation and Setup

### Prerequisites
- Python 3.12+
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/RitaZambito/HomeBridge.git
   cd HomeBridge
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## 👥 Test Accounts

The application includes simulated data with 25 service users and 25 volunteers across five UK cities (Birmingham, London, Edinburgh, Bristol, and Swansea).

| Role           | Email                          | Password     |
|----------------|--------------------------------|--------------|
| Service User   | margaret.thompson@email.com    | Admin123!    |
| Volunteer      | alex.turner@email.com          | Admin123!    |
| Administrator  | 2245801@student.uwtsd.ac.uk    | Admin123!    |

> All test accounts share the same password: `Admin123!`

---

## 🔍 Matching Algorithm

The matching engine scores each volunteer out of **100 points** across four dimensions:

| Factor        | Max Points | Description |
|---------------|-----------|-------------|
| Availability  | 40        | Weekly schedule alignment with requested day and time slot |
| Distance      | 40        | Exponential decay function on cached coordinates |
| Skills        | 15        | Match between requested service category and volunteer skills |
| Rating        | 5         | Based on average feedback rating from completed bookings |

---

## 📊 Database Schema

The SQLite database comprises **7 interrelated tables**: ServiceUser, Volunteer, Admin, Request, Feedback, Notification, and ChatMessage.

---

## 🔒 Security Features

- Password hashing with Werkzeug (OWASP compliant)
- CSRF protection via Flask-WTF on all forms
- Session expiry on browser close for shared-device protection
- Ownership verification on all destructive actions
- JavaScript confirmation dialogs on cancel/delete operations
- UK timezone handling (Europe/London) for accurate BST/GMT transitions

---

## ♿ Accessibility

- WCAG 2.2 guidelines compliance
- Skip-to-content link for keyboard navigation
- ARIA labels on interactive elements
- Visible focus indicators (`:focus-visible`)
- `prefers-reduced-motion` media query support
- Semantic HTML with `<main>`, `<nav>`, and `<footer>` roles
- `lang="en"` declaration for screen readers

---

## 📌 Limitations and Future Work

- Prototype using simulated data — not tested with real vulnerable users
- SQLite would need to be replaced with PostgreSQL for production scalability
- Future enhancements: email/SMS notifications, real-time messaging (WebSockets), file attachments, DBS check tracking, mobile app, and integration with external social care systems

---

## 👩‍💻 Author

**Rita Zambito** — BSc Applied Computing, UWTSD (IICL Birmingham)

**Supervisor:** Md Shantanu Islam

---

## 📄 License

This project was developed as an academic dissertation and is submitted in partial fulfilment of the requirements for the BSc (Hons) Applied Computing degree at the University of Wales Trinity Saint David.
