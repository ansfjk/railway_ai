import os
import tempfile, io
from flask import Flask, request, jsonify, render_template_string, send_file, send_from_directory
import pandas as pd
import shutil
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import optimasi_theread
import threading

# Ganti ID sesuai file kamu
GDRIVE_FILE_ID = "1wgLHVpbkBjLN9mD_tBrfTv5_ne62Us-L7mbMkC4Dn2M"
SHEET_ID = "1wgLHVpbkBjLN9mD_tBrfTv5_ne62Us-L7mbMkC4Dn2M"  # ← ID dari Google Sheets kamu

# GDRIVE_DIRECT_LINK = f"https://drive.google.com/uc?export=download&id={GDRIVE_FILE_ID}"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

app = Flask(__name__)

scrape_thread = None
latest_scrape_path = None
scrape_lock = threading.Lock()

def get_gdrive_csv():
    CSV_UR = "https://docs.google.com/spreadsheets/d/1wgLHVpbkBjLN9mD_tBrfTv5_ne62Us-L7mbMkC4Dn2M/export?format=csv"
    """Ambil CSV dari Google Drive dan kembalikan DataFrame."""
    r = requests.get(CSV_UR)
    if r.status_code != 200:
        raise Exception("Gagal download CSV dari Google Drive.")
    
    df = pd.read_csv(io.StringIO(r.text))
    
    if "LINK" not in df.columns:
        raise ValueError("CSV harus punya kolom 'LINK'")
    
    # Normalisasi URL
    df["LINK"] = df["LINK"].apply(lambda x: x.replace("https:/", "https://") if isinstance(x, str) else x)
    return df

def scrape_link(url):
    """Scrape konten judul dari URL."""
    try:
        if not isinstance(url, str) or not url.startswith("http"):
            return "Invalid URL"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
        return title
    except Exception as e:
        return f"Error: {str(e)}"

def real_scrape(df: pd.DataFrame, name="hasil_scrape"):
    """Scrape konten halaman dari setiap LINK dan simpan hasil ke CSV."""
    df_out = df.copy()
    df_out["HASIL"] = df_out["LINK"].apply(scrape_link)

    tmpdir = tempfile.mkdtemp()
    out_path = os.path.join(tmpdir, f"{name}.csv")
    df_out.to_csv(out_path, index=False)
    return out_path

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

        # Buat folder static jika belum ada
        os.makedirs("static", exist_ok=True)
        static_path = os.path.join("static", f"{name}.csv")
        shutil.copy(hasil_path, static_path)

        if not os.path.exists(hasil_path):
            return jsonify({"status": "error", "message": "File tidak ditemukan."}), 404


        # Kirim langsung file CSV untuk didownload browser
        return send_file(
            hasil_path,
            as_attachment=True,
            download_name=f"{name}.csv",
            mimetype="text/csv"
        )


    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("static", filename, as_attachment=True)

@app.route("/download-latest")
def download_latest():
    global latest_scrape_path
    if latest_scrape_path and os.path.exists(latest_scrape_path):
        return send_file(
            latest_scrape_path,
            as_attachment=True,
            download_name=os.path.basename(latest_scrape_path),
            mimetype="text/csv"
        )
    return jsonify({"status": "error", "message": "Belum ada file scrape yang tersedia."}), 404


@app.route("/run", methods=["GET"])
def run_info():
    return jsonify({
        "status": "Gunakan metode POST untuk memicu scraper.",
        "cara": "Kirim form ke endpoint /run dengan parameter 'name'"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
