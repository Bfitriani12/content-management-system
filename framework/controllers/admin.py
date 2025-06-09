from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from framework.models.user import User
from framework.models.post import Post
from framework.models.category import Category
from framework.models.tag import Tag
from framework.models.comment import Comment
from framework.core.app import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def index():
    posts_count = Post.query.count()
    users_count = User.query.count()
    comments_count = Comment.query.count()
    categories_count = Category.query.count()
    
    return render_template('admin/index.html',
                         posts_count=posts_count,
                         users_count=users_count,
                         comments_count=comments_count,
                         categories_count=categories_count)

@admin_bp.route('/posts')
@login_required
@admin_required
def posts():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/posts.html', posts=posts)

@admin_bp.route('/posts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        slug = request.form.get('slug')
        category_id = request.form.get('category_id')
        tags = request.form.getlist('tags')
        published = bool(request.form.get('published'))
        
        # Handle image upload
        image = request.files.get('image')
        image_filename = None
        if image:
            filename = secure_filename(image.filename)
            image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename))
        
        post = Post(
            title=title,
            content=content,
            slug=slug,
            user_id=current_user.id,
            category_id=category_id,
            image=image_filename,
            published=published
        )
        
        # Add tags
        for tag_id in tags:
            tag = Tag.query.get(tag_id)
            if tag:
                post.tags.append(tag)
        
        db.session.add(post)
        db.session.commit()
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('admin.posts'))
    
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('admin/new_post.html', categories=categories, tags=tags)

@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/comments')
@login_required
@admin_required
def comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('admin/comments.html', comments=comments) 