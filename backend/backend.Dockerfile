FROM python:3.11-slim

WORKDIR .

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Copy shared base library
# COPY ../base-library /app/base-library

EXPOSE 8000

CMD ["python", "main.py"]