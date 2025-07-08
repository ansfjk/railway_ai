#!/bin/bash

apt-get update && apt-get install -y chromium chromium-driver

# Jalankan Flask dengan exec supaya Railway nunggu proses ini
exec python3 api_scraper.py
