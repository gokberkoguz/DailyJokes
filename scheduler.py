from app import scheduler, db
from models import Subscriber, Joke
from email_service import send_daily_joke
from datetime import datetime, timedelta
from sqlalchemy import or_

@scheduler.task('cron', id='send_daily_jokes', hour=9)
def send_daily_jokes():
    with scheduler.app.app_context():
        subscribers = Subscriber.query.filter_by(is_active=True).all()
        
        for subscriber in subscribers:
            categories = subscriber.preferences.get('categories', ['general'])
            
            # Get a joke that hasn't been sent recently
            joke = Joke.query.filter(
                Joke.category.in_(categories),
                or_(
                    Joke.last_sent == None,
                    Joke.last_sent <= datetime.utcnow() - timedelta(days=7)
                )
            ).order_by(Joke.last_sent.nulls_first()).first()
            
            if joke:
                send_daily_joke(subscriber, joke)
                joke.last_sent = datetime.utcnow()
                db.session.commit()
