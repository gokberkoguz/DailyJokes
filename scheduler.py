from app import db
from models import Subscriber, Joke, Category, JokeHistory
from flask_apscheduler import APScheduler
from email_service import send_daily_joke
from datetime import datetime, timedelta
from sqlalchemy import or_, extract
from app import create_app

# Create the Flask app instance
app = create_app()
# Create and configure the scheduler
scheduler = APScheduler()


def send_jokes_for_time(current_hour, current_minute):
    """Send jokes to subscribers who want delivery at the specified hour"""
    with scheduler.app.app_context():
        # Get subscribers who want delivery at this time
        subscribers = Subscriber.query.filter(
            Subscriber.is_active == True,
            extract('hour', Subscriber.delivery_time) == current_hour,
            extract('minute', Subscriber.delivery_time) == current_minute
        ).all()

        for subscriber in subscribers:
            categories = subscriber.preferences.get('categories', [])
            if not categories:
                continue

            # Collect jokes for each category
            jokes_to_send = []
            for category_name in categories:
                category = Category.query.filter_by(name=category_name, is_active=True).first()
                if not category:
                    continue

                # Get a joke for the category that hasn't been sent recently
                joke = Joke.query.filter(
                    Joke.category_id == category.id,
                    or_(
                        Joke.last_sent == None,
                        Joke.last_sent <= datetime.utcnow() - timedelta(days=7)
                    )
                ).order_by(Joke.last_sent.nulls_first()).first()

                if joke:
                    jokes_to_send.append(joke)

            if jokes_to_send:
                # Send jokes to the subscriber
                send_daily_joke(subscriber, jokes_to_send)

                # Log each joke sent and update `last_sent`
                for joke in jokes_to_send:
                    joke.last_sent = datetime.utcnow()
                    log = JokeHistory(joke_id=joke.id, user=subscriber.id, sent_at=datetime.utcnow())
                    db.session.add(log)

                db.session.commit()


# Run every minute to check for subscribers who want delivery at that time
@scheduler.task('cron', id='send_minutely_jokes', minute='*')
def send_minutely_jokes():
    current_minute = datetime.utcnow().minute
    current_hour = datetime.utcnow().hour
    send_jokes_for_time(current_hour, current_minute)
    return "success"


if __name__ == "__main__":
    scheduler.init_app(app)
    with app.app_context():
        print("Starting scheduler...")
        scheduler.start()
        # Keep the process alive
        import time
        while True:
            time.sleep(1)
