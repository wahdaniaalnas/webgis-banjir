# WebGIS Dinamis – Praktikum KBD
## Multi-Layer Supabase + Flask + Geopandas + Leaflet

---

## Perbedaan dengan versi asli dosen

| Aspek | Versi Lama (dummy) | Versi Ini (dinamis) |
|---|---|---|
| Penyimpanan | `if_exists="replace"` → selalu timpa | `INSERT` baris baru setiap upload |
| Tabel | 1 tabel = 1 peta | 1 tabel = banyak peta |
| Filter | Tidak ada | Filter by tema & wilayah |
| Multi-layer | Tidak bisa | Bisa tampilkan 5+ layer sekaligus |
| Atribut DBF | Tidak disimpan | Disimpan sebagai JSON |
| Warna layer | Satu warna | Tiap peta warna sendiri |
| Hapus peta | Tidak ada | Ada tombol hapus per peta |

---

## Cara Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Isi DATABASE_URL di app.py
```python
# Baris 19 di app.py
DATABASE_URL = "postgresql://postgres.XXXXX:PASSWORD@aws-0-...pooler.supabase.com:5432/postgres"
```
Ambil dari: Supabase Dashboard → Project Settings → Database → Connection String (URI mode)

### 3. Buat Tabel di Supabase (sekali saja)
Buka Supabase → SQL Editor → jalankan:
```sql
CREATE TABLE IF NOT EXISTS peta_koleksi (
  id            TEXT PRIMARY KEY,
  nama_peta     TEXT NOT NULL,
  jenis_peta    TEXT DEFAULT 'polygon',
  wilayah       TEXT,
  tema          TEXT DEFAULT 'umum',
  deskripsi     TEXT,
  warna         TEXT DEFAULT '#3388ff',
  geojson       TEXT,
  atribut_kol   TEXT,
  jumlah_fitur  INTEGER,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```
> Atau biarkan `init_db()` di app.py yang membuatnya otomatis saat server start.

### 4. Jalankan Server
```bash
python app.py
```
Buka browser: http://127.0.0.1:5001

---

## Cara Menggunakan

1. **Tab Upload** → pilih file ZIP shapefile → isi nama, jenis, wilayah, tema, warna → klik "Simpan ke Supabase"
2. **Tab Layer DB** → lihat semua peta tersimpan → klik "Tampilkan" untuk load ke peta
3. Bisa aktifkan **banyak layer sekaligus** — tiap layer warnanya berbeda
4. Klik fitur di peta untuk melihat **atribut lengkap dari DBF**

---

## Struktur Proyek
```
webgis/
├── app.py              ← Flask backend
├── requirements.txt    ← Dependencies
├── uploads/            ← Folder sementara (auto-created)
└── templates/
    └── index.html      ← Frontend (Leaflet + Tailwind)
```

---

## API Endpoints

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/` | Halaman utama |
| POST | `/api/upload` | Upload ZIP SHP → konversi → simpan |
| POST | `/api/simpan_meta` | Simpan GeoJSON + metadata (dari browser) |
| GET | `/api/peta` | Daftar semua peta (filter opsional) |
| GET | `/api/peta/<id>` | Detail + GeoJSON 1 peta |
| DELETE | `/api/peta/<id>` | Hapus 1 peta |
| GET | `/api/statistik` | Jumlah total peta, fitur, wilayah |
