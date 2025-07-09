import os
import tempfile, io
from flask import Flask, request, jsonify, render_template_string, send_file
import pandas as pd
import shutil
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import optimasi_theread
import threading

CSV_URL = "https://docs.google.com/spreadsheets/d/1wgLHVpbkBjLN9mD_tBrfTv5_ne62Us-L7mbMkC4Dn2M/export?format=csv"

app = Flask(__name__)

scrape_thread = None
latest_scrape_path = None
scrape_lock = threading.Lock()

def get_gdrive_csv():
    r = requests.get(CSV_URL)
    if r.status_code != 200:
        raise Exception("Gagal download CSV dari Google Drive.")
    
    df = pd.read_csv(io.StringIO(r.text))
    if "LINK" not in df.columns:
        raise ValueError("CSV harus punya kolom 'LINK'")
    df["LINK"] = df["LINK"].apply(lambda x: x.replace("https:/", "https://") if isinstance(x, str) else x)
    return df

@app.route("/")
def home():
    return render_template_string("""
        <h2>🚀 Jalankan Scraper</h2>
        <form method="post" action="/run">
            <label>Nama File Output (tanpa .csv):</label><br>
            <input type="text" name="name" placeholder="contoh: hasil_scrape_1"><br><br>
            <button type="submit">🟢 Jalankan Scraper</button>
        </form>
        <br>
        <a href="/debug-csv" target="_blank">🔍 Debug CSV dari Google Drive</a>
    """)

@app.route("/debug-csv")
def debug_csv():
    try:
        df = get_gdrive_csv()
        if df.empty:
            return jsonify({"status": "empty", "message": "CSV kosong atau gagal dibaca."})
        preview = df.head().to_dict(orient="records")
        return jsonify({"status": "ok", "preview": preview})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/run", methods=["POST"])
def trigger_scraper():
    try:
        name = request.form.get("name") or "hasil_scrape"
        df = get_gdrive_csv()
        if df.empty:
            return jsonify({"status": "error", "message": "CSV kosong."}), 400

        list_link = df["LINK"].dropna().tolist()
        from optimasi_theread import run_custom
        hasil_path = os.path.abspath(run_custom(list_link, nama_file_csv=name))

        # ⬇️ Download ZIP hasil scraping (gambar)
        return send_file(
            hasil_path,
            as_attachment=True,
            download_name=os.path.basename(hasil_path),
            mimetype="application/zip"
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/run", methods=["GET"])
def run_info():
    return jsonify({
        "status": "Gunakan metode POST untuk memicu scraper.",
        "cara": "Kirim form ke endpoint /run dengan parameter 'name'"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
