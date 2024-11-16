from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, login_user, logout_user
from models import db, Admin, Subscriber, Joke, Category
from email_service import send_welcome_email
from sqlalchemy import func, case, extract
from datetime import datetime, timedelta
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
    delivery_time = request.form.get('delivery_time')
    
    if not email:
        flash('Email is required!', 'error')
        return redirect(url_for('main.index'))
    
    try:
        delivery_time = datetime.strptime(delivery_time, '%H:%M').time()
    except ValueError:
        flash('Invalid delivery time format!', 'error')
        return redirect(url_for('main.index'))
    
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            flash('You are already subscribed!', 'info')
        else:
            existing.is_active = True
            existing.preferences = {'categories': categories}
            existing.delivery_time = delivery_time
            db.session.commit()
            flash('Welcome back! Your subscription has been reactivated.', 'success')
        return redirect(url_for('main.index'))
    
    subscriber = Subscriber(
        email=email,
        preferences={'categories': categories or ['general']},
        delivery_time=delivery_time
    )
    db.session.add(subscriber)
    db.session.commit()
    
    send_welcome_email(email)
    flash('Successfully subscribed!', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/rate/<int:joke_id>/<int:rating>')
def rate_joke(joke_id, rating):
    if not 1 <= rating <= 5:
        flash('Invalid rating value!', 'error')
        return render_template('rate.html', success=False)
    
    joke = Joke.query.get_or_404(joke_id)
    if joke.times_sent == 0:
        joke.rating = float(rating)
    else:
        joke.rating = (joke.rating * joke.times_sent + rating) / (joke.times_sent + 1)
    joke.times_sent += 1
    db.session.commit()
    
    return render_template('rate.html', success=True)

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
    jokes = Joke.query.order_by(Joke.created_at.desc()).all()
    subscribers = Subscriber.query.filter_by(is_active=True).all()
    categories = Category.query.all()
    return render_template('admin.html', section='dashboard', 
                         jokes=jokes, subscribers=subscribers, 
                         categories=categories)

@main_bp.route('/admin/analytics')
@login_required
def admin_analytics():
    # Get basic stats
    total_subscribers = Subscriber.query.count()
    active_subscribers = Subscriber.query.filter_by(is_active=True).count()
    average_rating = db.session.query(func.avg(Joke.rating)).scalar() or 0

    # Get subscriber growth data (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    growth_query = db.session.query(
        func.date(Subscriber.subscribed_at).label('date'),
        func.count().label('count')
    ).filter(
        Subscriber.subscribed_at >= thirty_days_ago
    ).group_by(
        func.date(Subscriber.subscribed_at)
    ).order_by(
        func.date(Subscriber.subscribed_at)
    ).all()

    dates = [(thirty_days_ago + timedelta(days=x)).strftime('%Y-%m-%d') 
             for x in range(31)]
    growth_data = [0] * 31
    for date, count in growth_query:
        day_index = (date - thirty_days_ago.date()).days
        growth_data[day_index] = count

    # Get category preferences
    category_preferences = {}
    subscribers = Subscriber.query.filter_by(is_active=True).all()
    for subscriber in subscribers:
        for category in subscriber.preferences.get('categories', []):
            category_preferences[category] = category_preferences.get(category, 0) + 1

    category_names = list(category_preferences.keys())
    category_counts = [category_preferences[name] for name in category_names]

    # Get ratings distribution
    ratings_distribution = []
    for rating in range(1, 6):
        count = Joke.query.filter(
            Joke.rating >= rating - 0.5,
            Joke.rating < rating + 0.5
        ).count()
        ratings_distribution.append(count)

    return render_template('analytics.html',
                         total_subscribers=total_subscribers,
                         active_subscribers=active_subscribers,
                         average_rating=average_rating,
                         dates=dates,
                         growth_data=growth_data,
                         category_names=category_names,
                         category_counts=category_counts,
                         ratings_distribution=ratings_distribution)

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