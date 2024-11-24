# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for PostgreSQL client and other essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add Poetry to the PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy only the project dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with Poetry
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# Copy the rest of the application files
COPY . .

# Expose the Flask application's port
EXPOSE 8000

# Set the default command to run the Flask app
RUN poetry add gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--preload", "main:app"]
