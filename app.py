"""
WebGIS Banjir Indonesia - Versi Final UAS
Wahda Alnas - 2025
"""
from flask import Flask, request, jsonify, render_template
from sqlalchemy import create_engine, text
import os, uuid, json, zipfile, io, tempfile

app = Flask(__name__, template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.cyyxmnlwcclcvbefmrfo:Nadhilaalnas@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"
)

def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db():
    with get_engine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS peta_layers (
                id            TEXT PRIMARY KEY,
                nama_layer    TEXT NOT NULL,
                tipe_wilayah  TEXT DEFAULT 'kecamatan',
                deskripsi     TEXT DEFAULT '',
                warna         TEXT DEFAULT '#2196f3',
                geojson_data  JSONB NOT NULL,
                atribut_fields TEXT[],
                jumlah_fitur  INT DEFAULT 0,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.commit()
    print("[OK] Database siap.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/layers', methods=['GET'])
def list_layers():
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(text(
                "SELECT * FROM peta_layers ORDER BY created_at DESC"
            )).mappings().all()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/layers/<layer_id>', methods=['GET'])
def get_layer(layer_id):
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text(
                "SELECT * FROM peta_layers WHERE id=:id"
            ), {"id": layer_id}).mappings().first()
        if not row:
            return jsonify({"error": "Layer tidak ditemukan"}), 404
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/layers/<layer_id>', methods=['DELETE'])
def delete_layer(layer_id):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("DELETE FROM peta_layers WHERE id=:id"), {"id": layer_id})
            conn.commit()
        return jsonify({"sukses": True, "pesan": "Layer dihapus"})
    except Exception as e:
        return jsonify({"sukses": False, "pesan": str(e)}), 500

@app.route('/api/reset_layers', methods=['DELETE'])
def reset_layers():
    """Hapus semua layer dari database"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("DELETE FROM peta_layers"))
            conn.commit()
        return jsonify({"sukses": True, "pesan": "Semua layer dihapus"})
    except Exception as e:
        return jsonify({"sukses": False, "pesan": str(e)}), 500

@app.route('/api/upload_shp', methods=['POST'])
def upload_shp():
    if 'file' not in request.files:
        return jsonify({"sukses": False, "pesan": "Tidak ada file"}), 400

    file  = request.files['file']
    nama  = request.form.get('nama_layer', 'Layer Baru')
    tipe  = request.form.get('tipe_wilayah', 'kecamatan')
    warna = request.form.get('warna', '#2196f3')
    desc  = request.form.get('deskripsi', '')
    fname = file.filename.lower()

    try:
        if fname.endswith('.geojson') or fname.endswith('.json'):
            content = file.read().decode('utf-8')
            geojson = json.loads(content)
        elif fname.endswith('.zip'):
            geojson = shp_zip_to_geojson(file)
        else:
            return jsonify({"sukses": False, "pesan": "Format tidak didukung. Gunakan .zip atau .geojson"}), 400

        features = geojson.get('features', [])
        jumlah   = len(features)
        fields   = list((features[0].get('properties') or {}).keys()) if features else []

        def escape_pg(s):
            return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

        fields_pg = '{' + ','.join(escape_pg(f) for f in fields) + '}'
        layer_id  = str(uuid.uuid4())

        with get_engine().connect() as conn:
            conn.execute(text("""
                INSERT INTO peta_layers
                    (id, nama_layer, tipe_wilayah, deskripsi, warna,
                     geojson_data, atribut_fields, jumlah_fitur)
                VALUES
                    (:id, :nama, :tipe, :desc, :warna,
                     CAST(:geojson AS jsonb), CAST(:fields AS text[]), :jml)
            """), {
                "id": layer_id, "nama": nama, "tipe": tipe,
                "desc": desc, "warna": warna,
                "geojson": json.dumps(geojson),
                "fields": fields_pg, "jml": jumlah,
            })
            conn.commit()

        return jsonify({
            "sukses": True, "layer_id": layer_id,
            "nama_layer": nama, "jumlah_fitur": jumlah,
            "atribut_fields": fields,
            "pesan": f"Layer '{nama}' berhasil disimpan ({jumlah} fitur)"
        })

    except Exception as e:
        return jsonify({"sukses": False, "pesan": str(e)}), 500

def shp_zip_to_geojson(zip_file_obj):
    try:
        import shapefile
    except ImportError:
        raise ImportError("Install pyshp: pip install pyshp")

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(zip_file_obj.read())) as zf:
            zf.extractall(tmpdir)

        shp_path = None
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith('.shp'):
                    shp_path = os.path.join(root, f)
                    break

        if not shp_path:
            raise ValueError("File .shp tidak ditemukan dalam ZIP")

        try:
            sf = shapefile.Reader(shp_path, encoding='utf-8')
        except Exception:
            sf = shapefile.Reader(shp_path, encoding='latin-1')

        fields   = [f[0] for f in sf.fields[1:]]
        features = []

        for shape_rec in sf.shapeRecords():
            try:
                geom = shape_rec.shape.__geo_interface__
            except Exception:
                continue
            props = dict(zip(fields, shape_rec.record))
            clean = {}
            for k, v in props.items():
                if isinstance(v, bytes): v = v.decode('utf-8', 'replace')
                elif hasattr(v, 'item'): v = v.item()
                clean[k] = v
            features.append({"type": "Feature", "properties": clean, "geometry": geom})

        sf.close()

    return {"type": "FeatureCollection", "features": features}

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv("PORT", 5002)))
