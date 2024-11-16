from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, login_user, logout_user
from models import db, Admin, Subscriber, Joke, Category
from email_service import send_welcome_email
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('index.html', categories=categories)

@main_bp.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    categories = request.form.getlist('categories')
    
    if not email:
        flash('Email is required!', 'error')
        return redirect(url_for('main.index'))
    
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            flash('You are already subscribed!', 'info')
        else:
            existing.is_active = True
            existing.preferences = {'categories': categories}
            db.session.commit()
            flash('Welcome back! Your subscription has been reactivated.', 'success')
        return redirect(url_for('main.index'))
    
    subscriber = Subscriber(
        email=email,
        preferences={'categories': categories or ['general']}
    )
    db.session.add(subscriber)
    db.session.commit()
    
    send_welcome_email(email)
    flash('Successfully subscribed!', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/unsubscribe/<email>')
def unsubscribe(email):
    subscriber = Subscriber.query.filter_by(email=email).first()
    if subscriber:
        subscriber.is_active = False
        db.session.commit()
        flash('Successfully unsubscribed!', 'success')
    return render_template('unsubscribe.html')

@main_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for('main.admin_dashboard'))
        flash('Invalid credentials', 'error')
    
    return render_template('admin.html', section='login')

@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    jokes = Joke.query.all()
    subscribers = Subscriber.query.filter_by(is_active=True).all()
    categories = Category.query.all()
    return render_template('admin.html', section='dashboard', 
                         jokes=jokes, subscribers=subscribers, 
                         categories=categories)

@main_bp.route('/admin/jokes', methods=['POST'])
@login_required
def admin_jokes():
    content = request.form.get('content')
    category_id = request.form.get('category_id')
    
    if content and category_id:
        joke = Joke(content=content, category_id=category_id)
        db.session.add(joke)
        db.session.commit()
        flash('Joke added successfully!', 'success')
    
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if name:
            category = Category(name=name, description=description)
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully!', 'success')
        
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/categories/<int:id>', methods=['POST'])
@login_required
def toggle_category(id):
    category = Category.query.get_or_404(id)
    category.is_active = not category.is_active
    db.session.commit()
    return jsonify({'status': 'success', 'is_active': category.is_active})
