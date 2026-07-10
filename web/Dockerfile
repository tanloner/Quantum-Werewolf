# Quantum Werewolf Web Application
# Build from project root: docker build -f web/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY web/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the quantum werewolf backend
COPY quantumwerewolf/ ./quantumwerewolf/

# Copy web application code
COPY web/server/ ./server/
COPY web/static/ ./static/

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
WORKDIR /app/server
CMD ["python", "main.py"]
