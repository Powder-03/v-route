# We use Python slim to minimize image size and provide a standard Debian runtime
FROM python:3.11-slim

# Set environment variables to prevent python from writing pyc files to disc
# and to prevent python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

WORKDIR /app

# Install python dependencies mapped rigidly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code architecture
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Pre-download and cache FlashRank model during build phase to prevent cold-start latency
RUN python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-TinyBERT-L-2-v2', cache_dir='/app/.flashrank_cache')"

# Explicitly expose port
EXPOSE 8000

# Start Gunicorn wrapped around Uvicorn bound securely without localhost constraints
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4"]
