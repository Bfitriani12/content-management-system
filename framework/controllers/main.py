from flask import Blueprint, render_template, request
from framework.models.post import Post
from framework.models.category import Category
from framework.models.tag import Tag
from framework.models.comment import Comment
from framework.core.app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(published=True).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('main/index.html', posts=posts, categories=categories, tags=tags)

@main_bp.route('/post/<slug>')
def post(slug):
    post = Post.query.filter_by(slug=slug, published=True).first_or_404()
    comments = Comment.query.filter_by(post_id=post.id, approved=True).order_by(Comment.created_at.desc()).all()
    return render_template('main/post.html', post=post, comments=comments)

@main_bp.route('/category/<slug>')
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(category_id=category.id, published=True).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('main/category.html', category=category, posts=posts)

@main_bp.route('/tag/<slug>')
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = tag.posts.filter_by(published=True).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('main/tag.html', tag=tag, posts=posts)

@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if query:
        posts = Post.query.filter(
            Post.published == True,
            (Post.title.ilike(f'%{query}%') | Post.content.ilike(f'%{query}%'))
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    else:
        posts = Post.query.filter_by(published=True).order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('main/search.html', posts=posts, query=query)

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html') 