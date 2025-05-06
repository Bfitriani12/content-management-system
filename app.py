from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='author')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)
    reset_token = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text)
    excerpt = db.Column(db.Text)
    featured_image = db.Column(db.String(200))
    status = db.Column(db.String(20), default='draft')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    categories = db.relationship('Category', secondary='post_categories')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', secondary='post_categories')

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Association table for posts and categories
post_categories = db.Table('post_categories',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        stats = {
            'posts': Post.query.count(),
            'categories': Category.query.count(),
            'users': User.query.count(),
            'media': Media.query.count()
        }
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        return render_template('admin/dashboard.html', stats=stats, recent_posts=recent_posts, recent_users=recent_users)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('admin_dashboard'))
            
            flash('Invalid username or password', 'danger')
        except Exception as e:
            flash(f'Error during login: {str(e)}', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('You have been logged out successfully.', 'success')
    except Exception as e:
        flash(f'Error during logout: {str(e)}', 'danger')
    return redirect(url_for('login'))

@app.route('/admin/posts')
@login_required
def admin_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/posts.html', posts=posts)

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/media')
@login_required
def admin_media():
    media_files = Media.query.order_by(Media.created_at.desc()).all()
    return render_template('admin/media.html', media_files=media_files)

@app.route('/admin/users')
@login_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/settings')
@login_required
def admin_settings():
    return render_template('admin/settings.html')

@app.route('/admin/profile')
@login_required
def admin_profile():
    return render_template('admin/profile.html')

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Generate password reset token
                token = generate_password_hash(email + str(datetime.utcnow()))
                user.reset_token = token
                db.session.commit()
                
                # Send password reset email
                reset_url = url_for('reset_password', token=token, _external=True)
                msg = Message('Password Reset Request',
                            recipients=[user.email])
                msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request then simply ignore this email.
'''
                mail.send(msg)
                
                flash('Password reset instructions have been sent to your email.', 'success')
                return redirect(url_for('login'))
            
            flash('Email address not found.', 'danger')
        except Exception as e:
            flash(f'Error processing request: {str(e)}', 'danger')
    
    return render_template('admin/forgot_password.html')

@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    try:
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            flash('Invalid or expired password reset link.', 'danger')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('admin/reset_password.html')
            
            user.set_password(password)
            user.reset_token = None
            db.session.commit()
            
            flash('Your password has been reset successfully.', 'success')
            return redirect(url_for('login'))
        
        return render_template('admin/reset_password.html')
    except Exception as e:
        flash(f'Error processing request: {str(e)}', 'danger')
        return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('admin/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('admin/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            # Create admin user if it doesn't exist
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    full_name='Administrator',
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print('Admin user created successfully!')
        except Exception as e:
            print(f'Error initializing database: {str(e)}')
    app.run(debug=True) 