from flask import Flask, request, jsonify
from scraper_engine import run_custom
import threading

app = Flask(__name__)

@app.route("/api/scrape", methods=["POST"])
def run_scrape():
    data = request.get_json()
    links = data.get("links", [])
    name = data.get("name", "hasil_scrape")

    if not links:
        return jsonify({"error": "No links provided"}), 400

    def scrape_thread():
        run_custom(links, nama_file_csv=name)

    threading.Thread(target=scrape_thread).start()
    return jsonify({"status": "running", "message": f"Scraping {len(links)} link(s)"}), 200

if __name__ == "__main__":
    app.run(port=5000)