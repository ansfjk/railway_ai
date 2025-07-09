# Gunakan image Python ringan
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Salin dependensi dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file project ke image
COPY . .

# Railway akan jalankan perintah ini secara default
CMD ["python", "api.py"]
