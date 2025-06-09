from datetime import datetime
from framework.core.app import db

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='category', lazy='dynamic')
    
    def __init__(self, name, slug, description=None):
        self.name = name
        self.slug = slug
        self.description = description
    
    def __repr__(self):
        return f'<Category {self.name}>' 