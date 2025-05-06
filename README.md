# Flask CMS

A simple Content Management System built with Python Flask.

## Features

- User Authentication
- Post Management
- Category Management
- Media Library
- User Management
- Settings Management

## Requirements

- Python 3.8+
- Flask 2.3.3
- SQLite (or any other database supported by SQLAlchemy)

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file with your configuration:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///cms.db
   ```
6. Initialize the database:
   ```python
   from app import app, db
   with app.app_context():
       db.create_all()
   ```
7. Create an admin user:
   ```python
   from app import app, db, User
   with app.app_context():
       admin = User(
           username='admin',
           email='admin@example.com',
           full_name='Administrator',
           role='admin'
       )
       admin.set_password('admin123')
       db.session.add(admin)
       db.session.commit()
   ```

## Running the Application

```bash
flask run
```

The application will be available at `http://localhost:5000`

## Default Login

- Username: admin
- Password: admin123

*Please change the default password after first login*

## Project Structure

```
cms/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── .env               # Environment configuration
├── static/            # Static files
│   ├── css/          # CSS styles
│   ├── js/           # JavaScript files
│   └── uploads/      # Uploaded media files
└── templates/         # HTML templates
    ├── base.html     # Base template
    └── admin/        # Admin templates
``` 