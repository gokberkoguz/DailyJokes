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

def send_daily_joke(subscriber, joke):
    msg = Message(
        'Your Daily Joke is Here! 😂',
        recipients=[subscriber.email]
    )
    msg.html = render_template('email/daily_joke.html',
                             content=joke.content,
                             is_welcome=False,
                             email=subscriber.email)
    mail.send(msg)
