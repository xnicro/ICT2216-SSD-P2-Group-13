FROM python:3.10-slim

WORKDIR /app
# COPY app/ /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["flask", "run", "--host=0.0.0.0", "--debug"]
#CMD ["gunicorn", "-w", "4", "--reload", "-b", "0.0.0.0:5000", "app:app" ]
