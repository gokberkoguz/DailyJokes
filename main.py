from app import create_app, scheduler

app = create_app()

if __name__ == "__main__":
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
