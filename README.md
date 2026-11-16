# EcoTrack – Smart Waste Management System

BCA final-year project. A responsive web platform for citizens to report waste-related
problems, administrators to manage complaints and assign collection tasks, and collection
staff to update task progress.

**Academic prototype.** Not integrated with any live municipal authority or waste
collection service. AI waste classification, IoT bins, vehicle GPS tracking, reward
systems, and mobile applications are future scope.

## Technology Stack

- Python 3, Flask (application factory + Blueprints)
- MySQL 8, Flask-SQLAlchemy, Flask-Migrate
- Flask-Login (session auth), Flask-WTF/CSRF
- HTML5, CSS3, JavaScript, Bootstrap 5
- Chart.js, Leaflet.js, OpenStreetMap
- Pytest

## Project Structure

```
EcoTrack/
├── app/
│   ├── __init__.py        # application factory
│   ├── extensions.py      # db, migrate, login_manager, csrf
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py        # User, Role, status constants
│   │   ├── staff.py
│   │   ├── waste_category.py
│   │   ├── location.py
│   │   ├── report.py
│   │   ├── collection_task.py
│   │   ├── task_update.py
│   │   └── awareness_article.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py        # landing page + health check
│   │   └── auth.py        # login, logout, register, profile, change password
│   ├── services/
│   ├── utils/
│   │   └── decorators.py  # role-based access
│   ├── static/
│   │   ├── css/style.css
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── auth/          # login, register, profile, change_password
│       └── errors/        # 403, 404, 500
├── migrations/            # Flask-Migrate
├── tests/
│   ├── conftest.py
│   └── test_auth.py
├── docs/
├── reference/
├── instance/
├── config.py              # application configuration (root)
├── run.py                 # entry point
├── requirements.txt
├── .env.example           # copy to .env and fill in secrets
├── .gitignore
└── README.md
```

## Database Models

| Table | Key Fields |
|-------|------------|
| users | id, full_name, email (unique), password_hash, role, phone, created_at |
| staff | id, user_id (FK), availability, service_area |
| waste_categories | id, category_name (unique), description |
| locations | id, address_text, latitude, longitude |
| reports | id, user_id (FK), category_id (FK), location_id (FK), description, image_path, status, reference, created_at |
| collection_tasks | id, report_id (FK), staff_id (FK), assigned_by (FK), due_date, task_status, instructions, completed_at |
| task_updates | id, task_id (FK), updated_by (FK), status, remarks, created_at |
| awareness_articles | id, title, content, topic, is_published, published_at |

Roles: Citizen, Administrator, Staff.

## Setup

### 1. Clone / extract the project
```bash
cd EcoTrack
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your MySQL credentials and secret key:
```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/macOS
```
Edit `.env`:
```
SECRET_KEY=<a strong random key>
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ecotrack
DB_USER=ecotrack_user
DB_PASSWORD=<your db password>
```

### 5. Create the MySQL database
```sql
CREATE DATABASE ecotrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ecotrack_user'@'localhost' IDENTIFIED BY '<your db password>';
GRANT ALL PRIVILEGES ON ecotrack.* TO 'ecotrack_user'@'localhost';
FLUSH PRIVILEGES;
```

### 6. Initialize the database (migrations)
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 7. Run the application
```bash
flask run
# or
python run.py
```
Open http://127.0.0.1:5000

## Running Tests

```bash
pytest
```
Tests use an in-memory SQLite database (TestingConfig) and CSRF is disabled for tests.

## Security

- Passwords stored as salted hashes (werkzeug).
- Role-based server-side authorization on every protected route.
- CSRF protection on all forms (Flask-WTF).
- Secrets and DB credentials in environment variables (never hardcoded).
- Session cookies: HttpOnly, SameSite=Lax.
- Image uploads restricted by type/size with safe generated filenames (implemented in file-upload phase).

## License

Academic project – Uttaranchal University, BCA (2024-2027).
