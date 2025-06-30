FROM python:3.10-slim

WORKDIR /app

# Copy requirements first (for better caching)
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory
COPY app/ /app

# For production, use gunicorn instead of flask run
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

# For development, you can use:
# CMD ["flask", "run", "--host=0.0.0.0", "--debug"]