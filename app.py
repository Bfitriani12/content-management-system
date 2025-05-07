from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import time
from flask_wtf.csrf import CSRFProtect
import uuid

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
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail(app)
csrf = CSRFProtect(app)  # Initialize CSRF protection

# Add context processor for current datetime
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

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

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), default='My CMS')
    site_description = db.Column(db.Text)
    posts_per_page = db.Column(db.Integer, default=10)
    mail_server = db.Column(db.String(100))
    mail_port = db.Column(db.Integer)
    mail_username = db.Column(db.String(100))
    mail_password = db.Column(db.String(100))
    mail_use_tls = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

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
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('admin_dashboard')
            return redirect(next_page)
        
        flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/admin/posts')
@login_required
def admin_posts():
    # Get sort parameter from query string
    sort = request.args.get('sort', 'newest')
    status = request.args.get('status', 'all')
    
    # Base query
    query = Post.query
    
    # Apply status filter
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Apply sorting
    if sort == 'newest':
        query = query.order_by(Post.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Post.created_at.asc())
    elif sort == 'title':
        query = query.order_by(Post.title.asc())
    elif sort == 'status':
        query = query.order_by(Post.status.asc())
    
    # Execute query
    posts = query.all()
    
    return render_template('admin/posts.html', posts=posts, sort=sort, status=status)

@app.route('/admin/posts/create', methods=['GET', 'POST'])
@login_required
def admin_create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        content = request.form.get('content')
        status = request.form.get('status')
        category_ids = request.form.getlist('categories')
        
        post = Post(
            title=title,
            slug=slug,
            content=content,
            status=status,
            author_id=current_user.id
        )
        
        # Add categories
        for category_id in category_ids:
            category = Category.query.get(category_id)
            if category:
                post.categories.append(category)
        
        db.session.add(post)
        db.session.commit()
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('admin_posts'))
    
    categories = Category.query.all()
    return render_template('admin/post_form.html', categories=categories)

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.slug = request.form.get('slug')
        post.content = request.form.get('content')
        post.status = request.form.get('status')
        
        # Update categories
        post.categories = []
        category_ids = request.form.getlist('categories')
        for category_id in category_ids:
            category = Category.query.get(category_id)
            if category:
                post.categories.append(category)
        
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('admin_posts'))
    
    categories = Category.query.all()
    return render_template('admin/post_form.html', post=post, categories=categories)

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/publish', methods=['POST'])
@login_required
def admin_publish_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = 'published'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/posts/<int:post_id>/unpublish', methods=['POST'])
@login_required
def admin_unpublish_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = 'draft'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/create', methods=['POST'])
@login_required
def admin_create_category():
    name = request.form.get('name')
    slug = request.form.get('slug')
    description = request.form.get('description')
    parent_id = request.form.get('parent_id') or None
    
    category = Category(
        name=name,
        slug=slug,
        description=description,
        parent_id=parent_id
    )
    
    db.session.add(category)
    db.session.commit()
    
    flash('Category created successfully!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/edit', methods=['POST'])
@login_required
def admin_edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    category.name = request.form.get('name')
    category.slug = request.form.get('slug')
    category.description = request.form.get('description')
    category.parent_id = request.form.get('parent_id') or None
    
    db.session.commit()
    flash('Category updated successfully!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/media')
@login_required
def admin_media():
    media_files = Media.query.order_by(Media.created_at.desc()).all()
    return render_template('admin/media.html', media_files=media_files)

@app.route('/admin/media/upload', methods=['POST'])
@login_required
def admin_upload_media():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_media'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_media'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to prevent duplicates
        filename = f"{int(time.time())}_{filename}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        media = Media(
            filename=filename,
            original_filename=file.filename,
            file_type=file.content_type,
            file_size=os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        )
        
        db.session.add(media)
        db.session.commit()
        
        flash('File uploaded successfully!', 'success')
    else:
        flash('File type not allowed', 'error')
    
    return redirect(url_for('admin_media'))

@app.route('/admin/media/<int:media_id>/delete', methods=['POST'])
@login_required
def admin_delete_media(media_id):
    media = Media.query.get_or_404(media_id)
    
    # Delete file from filesystem
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], media.filename))
    except OSError:
        pass  # Ignore if file doesn't exist
    
    db.session.delete(media)
    db.session.commit()
    
    flash('Media deleted successfully!', 'success')
    return redirect(url_for('admin_media'))

# Helper function for file uploads
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/users')
@login_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/create', methods=['POST'])
@login_required
def admin_create_user():
    if current_user.role != 'admin':
        flash('You do not have permission to create users.', 'danger')
        return redirect(url_for('admin_users'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    role = request.form.get('role')
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin_users'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        role=role
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    flash('User created successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('You do not have permission to edit users.', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    role = request.form.get('role')
    
    # Check if username is taken by another user
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != user.id:
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin_users'))
    
    # Check if email is taken by another user
    existing_user = User.query.filter_by(email=email).first()
    if existing_user and existing_user.id != user.id:
        flash('Email already exists.', 'danger')
        return redirect(url_for('admin_users'))
    
    user.username = username
    user.email = email
    user.full_name = full_name
    user.role = role
    
    if password:
        user.set_password(password)
    
    db.session.commit()
    
    flash('User updated successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete users.', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the last admin
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last admin user.', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/settings')
@login_required
def admin_settings():
    if current_user.role != 'admin':
        flash('You do not have permission to access settings.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Get or create settings
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/settings/update', methods=['POST'])
@login_required
def admin_update_settings():
    if current_user.role != 'admin':
        flash('You do not have permission to update settings.', 'danger')
        return redirect(url_for('admin_settings'))
    
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        # Update site settings
        settings.site_name = request.form.get('site_name')
        settings.site_description = request.form.get('site_description')
        settings.posts_per_page = int(request.form.get('posts_per_page', 10))
        
        db.session.commit()
        flash('Site settings updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/email/update', methods=['POST'])
@login_required
def admin_update_email_settings():
    if current_user.role != 'admin':
        flash('You do not have permission to update email settings.', 'danger')
        return redirect(url_for('admin_settings'))
    
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        # Update email settings
        settings.mail_server = request.form.get('mail_server')
        settings.mail_port = int(request.form.get('mail_port', 587))
        settings.mail_username = request.form.get('mail_username')
        settings.mail_use_tls = request.form.get('mail_use_tls') == 'on'
        
        # Only update password if a new one is provided
        new_password = request.form.get('mail_password')
        if new_password:
            settings.mail_password = new_password
        
        db.session.commit()
        flash('Email settings updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating email settings: {str(e)}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username')
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            # Check if username is taken by another user
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Nama pengguna sudah digunakan.', 'danger')
                return redirect(url_for('admin_profile'))

            # Check if email is taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Surel sudah digunakan.', 'danger')
                return redirect(url_for('admin_profile'))

            # Update user information
            current_user.username = username
            current_user.email = email
            current_user.full_name = full_name

            # Handle password change if requested
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('Kata sandi saat ini tidak valid.', 'danger')
                    return redirect(url_for('admin_profile'))
                
                if new_password != confirm_password:
                    flash('Kata sandi baru tidak cocok.', 'danger')
                    return redirect(url_for('admin_profile'))
                
                current_user.set_password(new_password)
                flash('Kata sandi berhasil diperbarui.', 'success')

            db.session.commit()
            flash('Profil berhasil diperbarui.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal memperbarui profil: {str(e)}', 'danger')

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

@app.route('/admin/posts/<int:post_id>/view')
@login_required
def admin_view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('admin/post_view.html', post=post)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('admin/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('admin/500.html'), 500

def populate_sample_data():
    """Populate database with sample data"""
    try:
        # Create sample categories
        categories = {
            'teknologi': Category(
                name='Teknologi',
                slug='teknologi',
                description='Artikel tentang teknologi terbaru dan perkembangan IT'
            ),
            'bisnis': Category(
                name='Bisnis',
                slug='bisnis',
                description='Artikel tentang bisnis, ekonomi, dan keuangan'
            ),
            'kesehatan': Category(
                name='Kesehatan',
                slug='kesehatan',
                description='Artikel tentang kesehatan dan gaya hidup sehat'
            ),
            'pendidikan': Category(
                name='Pendidikan',
                slug='pendidikan',
                description='Artikel tentang pendidikan dan pembelajaran'
            ),
            'lifestyle': Category(
                name='Lifestyle',
                slug='lifestyle',
                description='Artikel tentang gaya hidup dan tren terkini'
            ),
            'olahraga': Category(
                name='Olahraga',
                slug='olahraga',
                description='Artikel tentang olahraga dan kebugaran'
            )
        }
        
        # Add categories if they don't exist
        for slug, category in categories.items():
            if not Category.query.filter_by(slug=slug).first():
                db.session.add(category)
        
        db.session.commit()
        
        # Create sample users if they don't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                full_name='Administrator'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        if not User.query.filter_by(username='flower').first():
            author1 = User(
                username='flower',
                email='bungafitriani@gmail.com',
                role='author',
                full_name='Bunga Fitriani'
            )
            author1.set_password('penulis123')
            db.session.add(author1)
        
        if not User.query.filter_by(username='penulis2').first():
            author2 = User(
                username='penulis2',
                email='penulis2@example.com',
                role='author',
                full_name='Penulis Dua'
            )
            author2.set_password('penulis123')
            db.session.add(author2)
        
        db.session.commit()
        
        # Get users for post creation
        admin = User.query.filter_by(username='admin').first()
        author1 = User.query.filter_by(username='flower').first()
        author2 = User.query.filter_by(username='penulis2').first()
        
        # Get categories
        teknologi = Category.query.filter_by(slug='teknologi').first()
        bisnis = Category.query.filter_by(slug='bisnis').first()
        kesehatan = Category.query.filter_by(slug='kesehatan').first()
        pendidikan = Category.query.filter_by(slug='pendidikan').first()
        lifestyle = Category.query.filter_by(slug='lifestyle').first()
        olahraga = Category.query.filter_by(slug='olahraga').first()
        
        # Create sample posts for each category
        sample_posts = [
            # Teknologi Posts
            {
                'title': 'Perkembangan AI di Indonesia 2024',
                'slug': 'perkembangan-ai-di-indonesia-2024',
                'content': '''
                <h2>Perkembangan AI di Indonesia</h2>
                <p>Teknologi AI semakin berkembang pesat di Indonesia pada tahun 2024. Berikut perkembangannya:</p>
                <ul>
                    <li>Implementasi AI di sektor perbankan</li>
                    <li>Penggunaan AI dalam smart city</li>
                    <li>AI untuk analisis data kesehatan</li>
                </ul>
                ''',
                'status': 'published',
                'author': admin,
                'categories': [teknologi]
            },
            {
                'title': 'Tren Teknologi Blockchain 2024',
                'slug': 'tren-teknologi-blockchain-2024',
                'content': '''
                <h2>Blockchain di Era Digital</h2>
                <p>Blockchain menjadi teknologi yang semakin penting di 2024:</p>
                <ul>
                    <li>Smart contracts dalam bisnis</li>
                    <li>Cryptocurrency adoption</li>
                    <li>Blockchain dalam supply chain</li>
                </ul>
                ''',
                'status': 'published',
                'author': author1,
                'categories': [teknologi]
            },
            {
                'title': 'Metaverse dan Masa Depan Internet',
                'slug': 'metaverse-dan-masa-depan-internet',
                'content': '''
                <h2>Era Metaverse</h2>
                <p>Bagaimana metaverse akan mengubah cara kita berinteraksi di internet:</p>
                <ul>
                    <li>Virtual reality workspace</li>
                    <li>Digital economy</li>
                    <li>Social interaction</li>
                </ul>
                ''',
                'status': 'draft',
                'author': author2,
                'categories': [teknologi]
            },
            # Bisnis Posts
            {
                'title': 'Strategi Bisnis Digital 2024',
                'slug': 'strategi-bisnis-digital-2024',
                'content': '''
                <h2>Bisnis di Era Digital</h2>
                <p>Strategi bisnis yang perlu diterapkan di era digital:</p>
                <ul>
                    <li>Optimasi media sosial</li>
                    <li>E-commerce integration</li>
                    <li>Digital marketing</li>
                </ul>
                ''',
                'status': 'published',
                'author': admin,
                'categories': [bisnis]
            },
            {
                'title': 'Investasi Cryptocurrency 2024',
                'slug': 'investasi-cryptocurrency-2024',
                'content': '''
                <h2>Cryptocurrency sebagai Investasi</h2>
                <p>Panduan investasi crypto di tahun 2024:</p>
                <ul>
                    <li>Analisis market</li>
                    <li>Manajemen risiko</li>
                    <li>Diversifikasi portfolio</li>
                </ul>
                ''',
                'status': 'published',
                'author': author2,
                'categories': [bisnis]
            },
            {
                'title': 'Startup Indonesia 2024',
                'slug': 'startup-indonesia-2024',
                'content': '''
                <h2>Ekosistem Startup</h2>
                <p>Perkembangan startup di Indonesia tahun 2024:</p>
                <ul>
                    <li>Fintech innovation</li>
                    <li>Edtech growth</li>
                    <li>Healthtech solutions</li>
                </ul>
                ''',
                'status': 'draft',
                'author': author1,
                'categories': [bisnis]
            },
            # Kesehatan Posts
            {
                'title': 'Tips Hidup Sehat 2024',
                'slug': 'tips-hidup-sehat-2024',
                'content': '''
                <h2>Pola Hidup Sehat</h2>
                <p>Tips menjaga kesehatan di tahun 2024:</p>
                <ul>
                    <li>Nutrisi seimbang</li>
                    <li>Olahraga teratur</li>
                    <li>Manajemen stress</li>
                </ul>
                ''',
                'status': 'published',
                'author': author1,
                'categories': [kesehatan]
            },
            {
                'title': 'Manfaat Meditasi untuk Kesehatan',
                'slug': 'manfaat-meditasi-untuk-kesehatan',
                'content': '''
                <h2>Meditasi dan Kesehatan</h2>
                <p>Manfaat meditasi untuk kesehatan mental dan fisik:</p>
                <ul>
                    <li>Reduksi stress</li>
                    <li>Peningkatan fokus</li>
                    <li>Kesehatan jantung</li>
                </ul>
                ''',
                'status': 'published',
                'author': author2,
                'categories': [kesehatan]
            },
            {
                'title': 'Pola Makan Sehat di Era Digital',
                'slug': 'pola-makan-sehat-era-digital',
                'content': '''
                <h2>Nutrisi Digital</h2>
                <p>Mengatur pola makan sehat di era digital:</p>
                <ul>
                    <li>Meal planning apps</li>
                    <li>Nutrition tracking</li>
                    <li>Healthy food delivery</li>
                </ul>
                ''',
                'status': 'draft',
                'author': admin,
                'categories': [kesehatan]
            },
            # Pendidikan Posts
            {
                'title': 'Metode Pembelajaran Modern',
                'slug': 'metode-pembelajaran-modern',
                'content': '''
                <h2>Pendidikan Modern</h2>
                <p>Metode pembelajaran yang efektif di era modern:</p>
                <ul>
                    <li>Blended learning</li>
                    <li>Project-based learning</li>
                    <li>Gamification</li>
                </ul>
                ''',
                'status': 'published',
                'author': admin,
                'categories': [pendidikan]
            },
            {
                'title': 'Teknologi dalam Pendidikan',
                'slug': 'teknologi-dalam-pendidikan',
                'content': '''
                <h2>EdTech Revolution</h2>
                <p>Peran teknologi dalam pendidikan modern:</p>
                <ul>
                    <li>Virtual reality</li>
                    <li>AI tutoring</li>
                    <li>Online assessment</li>
                </ul>
                ''',
                'status': 'published',
                'author': author1,
                'categories': [pendidikan]
            },
            {
                'title': 'Pendidikan Karakter di Era Digital',
                'slug': 'pendidikan-karakter-era-digital',
                'content': '''
                <h2>Karakter Digital</h2>
                <p>Membangun karakter di era digital:</p>
                <ul>
                    <li>Digital citizenship</li>
                    <li>Online ethics</li>
                    <li>Digital literacy</li>
                </ul>
                ''',
                'status': 'draft',
                'author': author2,
                'categories': [pendidikan]
            },
            # Lifestyle Posts
            {
                'title': 'Tren Fashion 2024',
                'slug': 'tren-fashion-2024',
                'content': '''
                <h2>Fashion Trends</h2>
                <p>Tren fashion yang populer di 2024:</p>
                <ul>
                    <li>Sustainable fashion</li>
                    <li>Digital fashion</li>
                    <li>Minimalist style</li>
                </ul>
                ''',
                'status': 'published',
                'author': author2,
                'categories': [lifestyle]
            },
            {
                'title': 'Tips Work-Life Balance',
                'slug': 'tips-work-life-balance',
                'content': '''
                <h2>Work-Life Balance</h2>
                <p>Cara menjaga keseimbangan kerja dan kehidupan:</p>
                <ul>
                    <li>Time management</li>
                    <li>Boundary setting</li>
                    <li>Self-care routine</li>
                </ul>
                ''',
                'status': 'published',
                'author': admin,
                'categories': [lifestyle]
            },
            {
                'title': 'Minimalisme di Era Digital',
                'slug': 'minimalisme-era-digital',
                'content': '''
                <h2>Digital Minimalism</h2>
                <p>Menerapkan minimalisme di era digital:</p>
                <ul>
                    <li>Digital decluttering</li>
                    <li>Mindful technology use</li>
                    <li>Simple living</li>
                </ul>
                ''',
                'status': 'draft',
                'author': author1,
                'categories': [lifestyle]
            },
            # Olahraga Posts
            {
                'title': 'Tren Olahraga 2024',
                'slug': 'tren-olahraga-2024',
                'content': '''
                <h2>Sport Trends</h2>
                <p>Tren olahraga yang populer di 2024:</p>
                <ul>
                    <li>Virtual fitness</li>
                    <li>Home workout</li>
                    <li>Hybrid training</li>
                </ul>
                ''',
                'status': 'published',
                'author': author1,
                'categories': [olahraga]
            },
            {
                'title': 'Panduan Fitness Pemula',
                'slug': 'panduan-fitness-pemula',
                'content': '''
                <h2>Fitness untuk Pemula</h2>
                <p>Panduan memulai program fitness:</p>
                <ul>
                    <li>Basic exercises</li>
                    <li>Nutrition guide</li>
                    <li>Progress tracking</li>
                </ul>
                ''',
                'status': 'published',
                'author': author2,
                'categories': [olahraga]
            },
            {
                'title': 'Olahraga untuk Kesehatan Mental',
                'slug': 'olahraga-untuk-kesehatan-mental',
                'content': '''
                <h2>Mental Fitness</h2>
                <p>Olahraga untuk kesehatan mental:</p>
                <ul>
                    <li>Yoga dan meditasi</li>
                    <li>Mindful movement</li>
                    <li>Stress reduction</li>
                </ul>
                ''',
                'status': 'draft',
                'author': admin,
                'categories': [olahraga]
            }
        ]
        
        # Add posts if they don't exist
        for post_data in sample_posts:
            if not Post.query.filter_by(slug=post_data['slug']).first():
                post = Post(
                    title=post_data['title'],
                    slug=post_data['slug'],
                    content=post_data['content'],
                    status=post_data['status'],
                    author_id=post_data['author'].id
                )
                post.categories = post_data['categories']
                db.session.add(post)
        
        db.session.commit()
        print("Sample data has been populated successfully!")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error populating sample data: {str(e)}")
        raise

if __name__ == '__main__':
    with app.app_context():
        try:
            # Create all database tables
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
            
            # Check if we need to populate sample data
            if not Post.query.first():
                try:
                    populate_sample_data()
                    print('Sample data has been populated successfully!')
                except Exception as e:
                    print(f'Error populating sample data: {str(e)}')
                    db.session.rollback()
        except Exception as e:
            print(f'Error initializing database: {str(e)}')
            db.session.rollback()
    
    app.run(debug=True) 