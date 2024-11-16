from app import scheduler, db
from models import Subscriber, Joke
from email_service import send_daily_joke
from datetime import datetime, timedelta
from sqlalchemy import or_

def send_jokes_for_time(current_hour):
    """Send jokes to subscribers who want delivery at the specified hour"""
    with scheduler.app.app_context():
        # Get subscribers who want delivery at this hour
        subscribers = Subscriber.query.filter(
            Subscriber.is_active == True,
            extract('hour', Subscriber.delivery_time) == current_hour
        ).all()
        
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

# Run every hour to check for subscribers who want delivery at that time
@scheduler.task('cron', id='send_hourly_jokes', hour='*')
def send_hourly_jokes():
    current_hour = datetime.utcnow().hour
    send_jokes_for_time(current_hour)
