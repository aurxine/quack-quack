# Use official Python image as base
FROM python:3.11-slim

# Set work directory
WORKDIR /src

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY ./src ./src
COPY .env .

# Default command
ENTRYPOINT ["fastapi", "run", "src/main.py", "--workers", "4", "--port", "3210"]
