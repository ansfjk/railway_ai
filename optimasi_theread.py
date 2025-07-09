import os
import time
import logging
import requests
import pandas as pd
from io import BytesIO
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
from selenium_stealth import stealth
from concurrent.futures import ThreadPoolExecutor
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor, Future
import multiprocessing
import shutil

# Optional rembg
try:
    from rembg import remove
except ImportError:
    def remove(img_bytes):
        logging.warning("⚠️ rembg not available, skipping background removal.")
        return img_bytes

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# multiprocessing.set_start_method("fork", force=True)

RAW_SPEC_COLUMNS = [
    "Spec_Tipe", "Spec_Warna Produk", "Spec_Select_Transmisi", "Spec_Kapasitas Tangki Bensin",
    "Spec_Jumlah Silinder", "Spec_Kapasitas Silinder (CC)", "Spec_Daya Maksimum", "Spec_Torsi Maksimum",
    "Spec_Bahan Bakar", "Spec_Sistem Bahan Bakar", "Spec_Sistem Penggerak Roda", "Spec_Ukuran Ban",
    "Spec_Ukuran Velg", "Spec_Tipe Rem Depan dan Belakang", "Spec_Tipe Suspensi Depan dan Belakang",
    "Spec_Kapasitas Penumpang", "Spec_Tahun Pembuatan",
    "Spec_Spesifikasi Produk Spec_Nomor SUT (Sertifikat Uji Tipe) / Nomor SRUT (Sertifikat Registrasi Uji Kendaraan)",
    "Spec_Garansi", "Spec_Satuan Barang", "Spec_Berat per Produk", "Spec_Dimensi per Produk",
]

COLUMNS = [
    "NO", "LINK", "TKDN", "Link TKDN", "No Sertifikat TKDN", "NAMA PRODUK", "HARGA",
    "Merek", "Nama Pemilik SNI", "SNI", "Nomor SKU", "Kode KBKI", "Jenis Produk"
] + [col.replace("Spec_", "").replace("Select_", "").replace("Add_", "").strip() for col in RAW_SPEC_COLUMNS]

def close_driver(driver):
    try:
        driver.quit()
        time.sleep(1)  # ← 
    finally:
        if hasattr(driver, "_user_data_dir"):
            shutil.rmtree(driver._user_data_dir, ignore_errors=True)

def init_driver():
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")


    # user_data_dir = tempfile.mkdtemp(prefix="selenium_user_")
    # options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = webdriver.Chrome(options=options)
    # driver._user_data_dir = user_data_dir
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True
    )
    return driver

def normalize_label(text):
    return text.lower().strip().replace("produk", "").replace(":", "").replace(".", "").replace(",", "").strip()

def download_image(driver, src, path):
    try:
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(src, headers=headers, cookies=cookies, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        logging.warning(f"Gagal unduh gambar: {e}")
    return False

def remove_bg_and_save(input_path, output_path):
    try:
        with open(input_path, "rb") as inp:
            result = remove(inp.read())
        with open(output_path, "wb") as out:
            out.write(result)
        return str(output_path)
    except Exception as e:
        logging.warning(f"Gagal hapus background: {e}")
        return ""

def ambil_tkdn_data(link_tkdn):
    data = {}
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0")

        driver = webdriver.Chrome(options=options)
        driver.get(link_tkdn)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        try:
            label = driver.find_element(By.XPATH, "//div[contains(text(), 'No. Sertifikat')]")
            data["No Sertifikat TKDN"] = label.find_element(By.XPATH, "./following-sibling::div").text.strip()
        except:
            data["No Sertifikat TKDN"] = ""
        driver.quit()
    except Exception as e:
        logging.warning(f"Thread TKDN error: {e}")
        data["No Sertifikat TKDN"] = ""
    return data


def scrape_data(driver, link, idx, img_folder, rembg_folder, executor):
    data = {k: "" for k in COLUMNS}
    data["NO"] = idx
    data["LINK"] = link
    future_tkdn: Future = None

    print(f"🔗 Scrape {idx}: {link}")
    # try:
    #     with init_driver() as driver:
    #         driver.get(link)
    #         WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    #         time.sleep(1)

    #         try:
    #             label_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'Nilai TKDN')]")
    #             value_elem = label_elem.find_element(By.XPATH, "./following-sibling::div//a")
    #             data["TKDN"] = value_elem.text.strip()
    #             data["Link TKDN"] = value_elem.get_attribute("href")
    #             future_tkdn = executor.submit(ambil_tkdn_data, data["Link TKDN"])
    #         except: pass

    #         try:
    #             data["NAMA PRODUK"] = driver.find_element(By.TAG_NAME, "h1").text.strip()
    #             logging.info(f"✅ Data disimpan: {data['NAMA PRODUK']}")
    #         except: pass

    #         try:
    #             harga_elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "text-2xl")))
    #             data["HARGA"] = harga_elem.text.replace("Rp", "").replace(".", "").strip()
    #         except: pass

    #         try:
    #             deskripsi = driver.find_element(By.XPATH, "//div[h2[contains(text(),'Deskripsi Produk')]]/following-sibling::div")
    #             data["Deskripsi Produk"] = deskripsi.text.strip()
    #         except: pass

    #         blocks = driver.find_elements(By.CSS_SELECTOR, "div.grid.grid-cols-1")
    #         for block in blocks:
    #             try:
    #                 children = block.find_elements(By.XPATH, "./div")
    #                 if len(children) >= 2:
    #                     label, value = children[0].text.strip(), children[1].text.strip()
    #                     for col in COLUMNS:
    #                         if normalize_label(label) == normalize_label(col):
    #                             data[col] = value
    #                             break
    #             except: continue

    #         try:
    #             img_elem = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, '//img[contains(@class, "h-[350px] w-[350px]")]')))
    #             src = img_elem.get_attribute("src")
    #             if src.startswith("http"):
    #                 img_path = img_folder / f"{idx}.jpg"
    #                 nobg_path = rembg_folder / f"{idx}.png"
    #                 if download_image(driver, src, img_path):
    #                     saved = remove_bg_and_save(img_path, nobg_path)
    #                     data["Image_Path_1"] = saved
    #         except: pass
    try:
        driver.get(link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        try:
            label_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Nilai TKDN')]"))
            )
            value_elem = label_elem.find_element(By.XPATH, "./following-sibling::div//a")
            data["TKDN"] = value_elem.text.strip()
            data["Link TKDN"] = value_elem.get_attribute("href")

            # Langsung buka tab baru untuk scrape TKDN
            try:
                current_url = driver.current_url  # simpan URL halaman utama

                driver.get(data["Link TKDN"])  # langsung buka halaman TKDN di tab aktif
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                try:
                    label = driver.find_element(By.XPATH, "//div[contains(text(), 'No. Sertifikat')]")
                    data["No Sertifikat TKDN"] = label.find_element(By.XPATH, "./following-sibling::div").text.strip()
                except:
                    data["No Sertifikat TKDN"] = ""

                driver.get(current_url)  # kembali ke halaman utama produk

            except Exception as e:
                logging.warning(f"Gagal ambil detail TKDN dari {data['Link TKDN']}: {e}")
                data["No Sertifikat TKDN"] = ""

        except Exception as e:
            logging.warning(f"Gagal ambil TKDN dari {link}: {e}")

        try:
            data["NAMA PRODUK"] = driver.find_element(By.TAG_NAME, "h1").text.strip()
            logging.debug(f"Nm dari {data.get('NAMA PRODUK')}")
        except: pass

        try:
            harga_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "text-2xl"))
            )
            raw = harga_elem.text.strip()
            data["HARGA"] = raw.replace("Rp", "").replace(".", "").replace("\u00a0", "").strip()
        except: pass

        try:
            deskripsi = driver.find_element(By.XPATH, "//div[h2[contains(text(),'Deskripsi Produk')]]/following-sibling::div")
            data["Deskripsi Produk"] = deskripsi.text.strip()
        except: pass

        blocks = driver.find_elements(By.CSS_SELECTOR, "div.grid.grid-cols-1")
        for block in blocks:
            try:
                children = block.find_elements(By.XPATH, "./div")
                if len(children) >= 2:
                    label = children[0].text.strip()
                    value = children[1].text.strip()
                    for col in COLUMNS:
                        if normalize_label(label) == normalize_label(col):
                            data[col] = value
                            break
            except:
                continue

        try:
            img_xpath = '//img[contains(@class, "h-[350px] w-[350px]")]'
            img_elem = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, img_xpath)))
            src = img_elem.get_attribute("src")
            if src.startswith("http"):
                img_path = img_folder / f"{idx}.jpg"
                nobg_path = rembg_folder / f"{idx}.png"
                if download_image(driver, src, img_path):
                    data["Image_Path_1"] = remove_bg_and_save(img_path, nobg_path)
        except:
            pass

        if future_tkdn:
            try:
                tkdn_data = future_tkdn.result(timeout=10)
                data.update(tkdn_data)
            except Exception as e:
                logging.warning(f"Gagal ambil hasil future TKDN: {e}")

    except Exception as e:
        print(f"❌ Error scrape {link}: {e}")

    if future_tkdn:
        try:
            data.update(future_tkdn.result(timeout=10))
        except: pass

    return data

def run_custom(list_link, nama_file_csv="hasil_scrape", output_dir="CSV Sumber"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hasil_csv_path = output_dir / f"{nama_file_csv}.csv"
    folder_gambar_asli = output_dir / f"gambar_{nama_file_csv}"
    folder_gambar_nobg = output_dir / f"rembg_dari_{nama_file_csv}"
    folder_gambar_asli.mkdir(exist_ok=True)
    folder_gambar_nobg.mkdir(exist_ok=True)

    hasil_scrape = []
    scraped_links = set()
    start_idx = 1

    driver = init_driver()
    executor = ThreadPoolExecutor(max_workers=2)

    if hasil_csv_path.exists():
        df_existing = pd.read_csv(hasil_csv_path).fillna("")
        scraped_links = set(df_existing["LINK"].dropna())
        hasil_scrape.extend(df_existing.to_dict(orient="records"))
        if not df_existing.empty and "NO" in df_existing.columns:
            start_idx = int(df_existing["NO"].max()) + 1

    try:
        for idx, link in enumerate(list_link, start=start_idx):
            if link in scraped_links:
                logging.info(f"{idx}/{len(list_link)}: ⏩ Lewati (sudah di-scrape)")
                continue
            start = time.time()
            data = scrape_data(driver, link, idx, folder_gambar_asli, folder_gambar_nobg, executor)
            hasil_scrape.append(data)
            logging.info(f"{idx}: Done in {time.time() - start:.2f}s")
    finally:
        close_driver(driver)
        executor.shutdown(wait=True)

    pd.DataFrame(hasil_scrape)[COLUMNS].to_csv(hasil_csv_path, index=False, encoding="utf-8")
    logging.info(f"✅ Data disimpan: {hasil_csv_path}")
    return str(hasil_csv_path)