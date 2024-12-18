from flask import render_template
from app import mail
from flask_mail import Message

def send_welcome_email(email):
    msg = Message(
        'Welcome to Daily Jokes!',
        recipients=[email]
    )
    msg.html = render_template('email/daily_joke.html', 
                             content="Why did we sign you up? Because laughter is the best medicine! 😄",
                             is_welcome=True,
                             email=email)
    mail.send(msg)


def send_daily_joke(subscriber, jokes):
    """
    Sends a daily joke email with multiple jokes to a subscriber.

    Args:
        subscriber: The Subscriber object.
        jokes: A list of Joke objects, one from each subscribed category.
    """
    msg = Message(
        'Your Daily Dose of Laughter! 😂',
        recipients=[subscriber.email]
    )

    # Render the email template with multiple jokes
    msg.html = render_template(
        'email/daily_joke.html',
        jokes=jokes,
        is_welcome=False,
        email=subscriber.email
    )

    # Send the email
    mail.send(msg)
