from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, login_user, logout_user
from models import db, Admin, Subscriber, Joke, Category
from email_service import send_welcome_email
from sqlalchemy import func, case, extract
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from utils.ai_utils import generate_bulk_jokes
from openai import OpenAIError, RateLimitError, APIError, APIConnectionError
import logging
import json
from scheduler import send_minutely_jokes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    try:
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
        
    except IntegrityError:
        db.session.rollback()
        flash('An error occurred while processing your subscription. Please try again.', 'error')
    except Exception as e:
        db.session.rollback()
        flash('An unexpected error occurred. Please try again later.', 'error')
    
    return redirect(url_for('main.index'))

@main_bp.route('/rate/<int:joke_id>/<int:rating>')
def rate_joke(joke_id, rating):
    if not 1 <= rating <= 5:
        flash('Invalid rating value!', 'error')
        return render_template('rate.html', success=False)
    
    try:
        joke = Joke.query.get_or_404(joke_id)
        if joke.times_sent == 0:
            joke.rating = float(rating)
        else:
            joke.rating = (joke.rating * joke.times_sent + rating) / (joke.times_sent + 1)
        joke.times_sent += 1
        db.session.commit()
        return render_template('rate.html', success=True)
    except Exception:
        db.session.rollback()
        return render_template('rate.html', success=False)

@main_bp.route('/unsubscribe/<email>')
def unsubscribe(email):
    try:
        subscriber = Subscriber.query.filter_by(email=email).first()
        if subscriber:
            subscriber.is_active = False
            db.session.commit()
            flash('Successfully unsubscribed!', 'success')
    except Exception:
        db.session.rollback()
        flash('An error occurred while unsubscribing.', 'error')
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
    try:
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        
        if content and category_id:
            joke = Joke(content=content, category_id=category_id)
            db.session.add(joke)
            db.session.commit()
            flash('Joke added successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('An error occurred while adding the joke.', 'error')
    
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/generate-joke', methods=['POST'])
@login_required
def generate_ai_joke():
    """
    Generate a joke using OpenAI API and save it to the database
    """
    try:
        category_id = request.form.get('category_id')
        if not category_id:
            flash('Category ID is required.', 'error')
            return redirect(url_for('main.admin_dashboard'))

        category = Category.query.get_or_404(category_id)
        logger.info(f"Attempting to generate joke for category: {category.name}")
        
        # Generate joke using OpenAI
        generated_content = generate_bulk_jokes(category.name, category.description)
        
        if generated_content:
            # Save the generated joke
            for content in generated_content:
                joke = Joke(
                    content=content,
                    category_id=category_id
                )
                db.session.add(joke)
                db.session.commit()
            
            logger.info(f"Successfully generated and saved joke for category: {category.name}")
            flash('AI joke generated and added successfully!', 'success')
        else:
            logger.error("Failed to generate joke content")
            flash('Failed to generate joke. The AI service might be temporarily unavailable.', 'error')
            
    except RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        flash('Rate limit exceeded. Please try again in a few minutes.', 'error')
        db.session.rollback()
    
    except APIConnectionError:
        logger.error("Failed to connect to OpenAI API")
        flash('Unable to connect to the AI service. Please check your internet connection.', 'error')
        db.session.rollback()
    
    except APIError:
        logger.error("OpenAI API error occurred")
        flash('An error occurred with the AI service. Please try again later.', 'error')
        db.session.rollback()
    
    except OpenAIError as e:
        logger.error(f"OpenAI error: {str(e)}")
        flash('An error occurred while generating the joke. Please try again.', 'error')
        db.session.rollback()
    
    except IntegrityError:
        logger.error("Database integrity error")
        flash('Failed to save the generated joke due to a database error.', 'error')
        db.session.rollback()
    
    except Exception as e:
        logger.error(f"Unexpected error in generate_ai_joke: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        db.session.rollback()
    
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            
            if name:
                category = Category(name=name, description=description)
                db.session.add(category)
                db.session.commit()
                flash('Category added successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A category with this name already exists.', 'error')
        except Exception:
            db.session.rollback()
            flash('An error occurred while adding the category.', 'error')
        
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/categories/<int:id>', methods=['POST'])
@login_required
def toggle_category(id):
    try:
        category = Category.query.get_or_404(id)
        category.is_active = not category.is_active
        db.session.commit()
        return jsonify({'status': 'success', 'is_active': category.is_active})
    except Exception:
        db.session.rollback()
        return jsonify({'status': 'error'}), 500


@main_bp.route('/test', methods=['GET'])
def trigger_task():
    """Endpoint to manually trigger the task."""
    try:
        send_minutely_jokes()
        return jsonify({"status": "Task executed successfully"})
    except Exception as e:
        return jsonify({"status": "Task execution failed", "error": str(e)}), 500