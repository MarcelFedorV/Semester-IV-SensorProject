FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy shared base library
# COPY ../base-library /app/base-library

EXPOSE 8000

CMD ["python", "main.py"]