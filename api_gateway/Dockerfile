# We use Python slim to minimize image size and provide a standard Debian runtime
FROM python:3.11-slim

# Set environment variables to prevent python from writing pyc files to disc
# and to prevent python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install native dependencies required for sentence-transformers and aiokafka C Extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies mapped rigidly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during the docker build.
# This ensures the container starts immediately on boot rather than pausing to download weights across the network.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application code architecture
COPY . .

# Explicitly expose port
EXPOSE 8000

# Start Uvicorn bound securely without localhost constraints
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
