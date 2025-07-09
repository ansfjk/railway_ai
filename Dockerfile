FROM python:3.10-slim

# ----------------------------------------
# 1. Install system dependencies & Chrome
# ----------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip curl gnupg jq \
    fonts-liberation libappindicator3-1 \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libgdk-pixbuf2.0-0 libnspr4 libnss3 libxcomposite1 libxdamage1 \
    libxrandr2 xdg-utils libu2f-udev libvulkan1 libxss1 libxcb1 libx11-xcb1 \
    ca-certificates gnupg2 libglib2.0-0 libgtk-3-0 libgbm1 \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt install -y ./google-chrome-stable_current_amd64.deb \
    && rm -f google-chrome-stable_current_amd64.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ----------------------------------------
# 2. Install ChromeDriver (ver. 138.0.7204.92)
# ----------------------------------------
RUN wget -qO /tmp/chromedriver.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.92/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/chromedriver && \
    mv /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver*

# ----------------------------------------
# 3. Env fix untuk headless Chrome
# ----------------------------------------
ENV DISPLAY=:99
RUN chmod 1777 /tmp

# ----------------------------------------
# 4. Install Python dependencies
# ----------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------
# 5. Copy project & set workdir
# ----------------------------------------
COPY . /app
WORKDIR /app

# ----------------------------------------
# 6. Run main script
# ----------------------------------------
CMD ["python", "api_scraper.py"]
