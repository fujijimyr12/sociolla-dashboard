from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "sociolla_secret_key"

# Trick untuk menghilangkan halaman warning bawaan Ngrok jika diakses lewat jalur tunnel
@app.after_request
def add_header(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

def get_db_connection():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'sociolla.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# PAGE 1: HOME (FULL COLUMNS & ANTI-LAG)
# ==========================================
@app.route("/")
def home():
    conn = get_db_connection()
    
    # 1. Kotak Live Statistik Ringkasan di Atas
    count_brand = conn.execute("SELECT COUNT(*) FROM Brand;").fetchone()[0]
    count_category = conn.execute("SELECT COUNT(*) FROM Category;").fetchone()[0]
    count_product = conn.execute("SELECT COUNT(*) FROM Product;").fetchone()[0]
    count_rating = conn.execute("SELECT COUNT(*) FROM Rating;").fetchone()[0]
    count_engagement = conn.execute("SELECT COUNT(*) FROM Engagement;").fetchone()[0]

    # 🔍 2. Fitur Ambil ID dari Kolom Search
    search_id = request.args.get('search_id', '').strip()
    search_result = None
    
    if search_id and search_id.isdigit():
        query_search = """
            SELECT p.*, b.brand_name, c.category_default, r.*, e.*
            FROM Product p
            JOIN Brand b ON p.brand_id = b.brand_id
            JOIN Category c ON p.category_id = c.category_id
            LEFT JOIN Rating r ON p.product_id = r.product_id
            LEFT JOIN Engagement e ON p.product_id = e.product_id
            WHERE p.product_id = ?;
        """
        search_result = conn.execute(query_search, (int(search_id),)).fetchone()

    # 3. Tabel Data Lengkap 
    brands = conn.execute("SELECT * FROM Brand ORDER BY brand_id ASC;").fetchall()
    categories = conn.execute("SELECT * FROM Category ORDER BY category_id ASC;").fetchall()
    products = conn.execute("SELECT * FROM Product ORDER BY product_id ASC LIMIT 100;").fetchall()
    ratings = conn.execute("SELECT * FROM Rating ORDER BY product_id ASC LIMIT 100;").fetchall()
    engagements = conn.execute("SELECT * FROM Engagement ORDER BY product_id ASC LIMIT 100;").fetchall()
    
    # 📊 4. Data Grafik Ringkasan Kategori & Brand
    query_top_cat = "SELECT c.category_default, COUNT(p.product_id) as total_prod FROM Category c JOIN Product p ON c.category_id = p.category_id GROUP BY c.category_id ORDER BY total_prod DESC LIMIT 5;"
    res_cat = conn.execute(query_top_cat).fetchall()
    home_cat_labels = [row['category_default'] for row in res_cat]
    home_cat_data = [row['total_prod'] for row in res_cat]

    query_top_brand = "SELECT b.brand_name, COUNT(p.product_id) as total_prod FROM Brand b JOIN Product p ON b.brand_id = p.brand_id GROUP BY b.brand_id ORDER BY total_prod DESC LIMIT 5;"
    res_brand = conn.execute(query_top_brand).fetchall()
    home_brand_labels = [row['brand_name'] for row in res_brand]
    home_brand_data = [row['total_prod'] for row in res_brand]

    conn.close()
    return render_template(
        "home.html",
        count_brand=count_brand, count_category=count_category, count_product=count_product,
        count_rating=count_rating, count_engagement=count_engagement,
        brands=brands, categories=categories, products=products, ratings=ratings, engagements=engagements,
        home_cat_labels=home_cat_labels, home_cat_data=home_cat_data,
        home_brand_labels=home_brand_labels, home_brand_data=home_brand_data,
        search_result=search_result, search_id=search_id
    )

# ==========================================
# PAGE 2: ANALYSIS (QUERY RESULTS & DYNAMIC VISUALIZATION)
# ==========================================
@app.route("/analysis", methods=["GET", "POST"])
def analysis():
    selected_query = request.form.get("query_type") if request.method == "POST" else "join1_detail"
    
    conn = get_db_connection()
    data = []
    headers = []
    title = ""
    description = ""

    # --- 1. LOGIKA 13 QUERY RELASIONAL ---
    if selected_query == "join1_detail":
        title = "JOIN-1: Detail Ringkasan Produk & Pasar"
        description = "Menggabungkan tabel Product, Brand, Category, dan Engagement untuk melihat gambaran umum ulasan produk."
        query_sql = "SELECT p.product_id, b.brand_name, c.category_default, p.product_name, p.min_price, p.max_price, p.average_rating, e.total_reviews, e.total_in_wishlist FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Engagement e ON p.product_id = e.product_id ORDER BY p.product_id ASC LIMIT 15;"
        headers = ["ID Produk", "Brand", "Kategori", "Nama Produk", "Harga Min", "Harga Max", "Avg Rating", "Total Ulasan", "Total Wishlist"]
    elif selected_query == "join2_rating":
        title = "JOIN-2: Eksplorasi Aspek Rating Detil"
        description = "Menampilkan hubungan antara rata-rata rating dengan kepuasan aspek spesifik."
        query_sql = "SELECT p.product_id, p.product_name, b.brand_name, c.category_default, p.average_rating, r.rating_packaging, r.rating_texture, r.rating_effectiveness, r.rating_value_for_money, r.rating_long_wear, r.rating_scent FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Rating r ON p.product_id = r.product_id WHERE r.rating_effectiveness IS NOT NULL ORDER BY p.average_rating DESC LIMIT 15;"
        headers = ["ID Produk", "Nama Produk", "Brand", "Kategori", "Avg Rating", "Kemasan", "Tekstur", "Efektivitas", "Value Money", "Long Wear", "Aroma"]
    elif selected_query == "join3_profil":
        title = "JOIN-3: Profil Integrasi Lengkap 5 Tabel"
        description = "Query komprehensif yang menyatukan seluruh entitas."
        query_sql = "SELECT p.product_id, b.brand_name, c.category_default, p.product_name, p.min_price, p.max_price, p.average_rating, r.rating_effectiveness, r.rating_value_for_money, r.rating_texture, e.total_reviews, e.total_recommend_count, e.total_repurchase_yes, e.total_in_wishlist FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Rating r ON p.product_id = r.product_id JOIN Engagement e ON p.product_id = e.product_id WHERE e.total_reviews > 0 ORDER BY e.total_reviews DESC LIMIT 15;"
        headers = ["ID", "Brand", "Kategori", "Nama Produk", "Harga Min", "Harga Max", "Avg Rating", "Efektivitas", "Value Money", "Tekstur", "Total Ulasan", "Rekomendasi", "Repurchase (Yes)", "Total Wishlist"]
    elif selected_query == "agg1_brand":
        title = "AGG-1: Performa per Brand"
        description = "Agregasi jumlah produk, rata-rata rating, dan akumulasi wishlist per brand."
        query_sql = "SELECT b.brand_name, COUNT(p.product_id) AS total_produk, ROUND(AVG(CAST(p.average_rating AS FLOAT)), 2) AS avg_rating, ROUND(AVG(CAST(e.total_reviews AS INT)), 1) AS avg_ulasan, SUM(CAST(e.total_in_wishlist AS INT)) AS total_wishlist FROM Brand b JOIN Product p ON b.brand_id = p.brand_id JOIN Engagement e ON p.product_id = e.product_id WHERE p.average_rating IS NOT NULL GROUP BY b.brand_id, b.brand_name HAVING COUNT(p.product_id) >= 5 ORDER BY avg_rating DESC LIMIT 15;"
        headers = ["Nama Brand", "Total Produk", "Rata-rata Rating", "Rata-rata Ulasan", "Total Wishlist"]
    elif selected_query == "agg2_kategori":
        title = "AGG-2: Popularitas per Kategori"
        description = "Melihat kategori mana yang paling memikat minat pasar berdasarkan akumulasi wishlist pengguna."
        query_sql = "SELECT c.category_default, COUNT(p.product_id) AS total_produk, SUM(CAST(e.total_in_wishlist AS INT)) AS total_wishlist, SUM(CAST(e.total_reviews AS INT)) AS total_ulasan, SUM(CAST(e.total_recommend_count AS INT)) AS total_rekomendasi, ROUND(AVG(CAST(p.average_rating AS FLOAT)), 2) AS avg_rating FROM Category c JOIN Product p ON c.category_id = p.category_id JOIN Engagement e ON p.product_id = e.product_id GROUP BY c.category_id, c.category_default ORDER BY total_wishlist DESC LIMIT 15;"
        headers = ["Kategori Produk", "Total Produk", "Total Wishlist", "Total Ulasan", "Total Rekomendasi", "Rata-rata Rating"]
    elif selected_query == "agg3_aspek":
        title = "AGG-3: Rata-rata Aspek Rating per Kategori"
        description = "Analisis nilai kepuasan ulasan spesifik konsumen per kategori produk."
        query_sql = "SELECT c.category_default, COUNT(p.product_id) AS total_produk, ROUND(AVG(CAST(r.rating_packaging AS FLOAT)), 2) AS avg_packaging, ROUND(AVG(CAST(r.rating_texture AS FLOAT)), 2) AS avg_texture, ROUND(AVG(CAST(r.rating_effectiveness AS FLOAT)), 2) AS avg_effectiveness FROM Category c JOIN Product p ON c.category_id = p.category_id JOIN Rating r ON p.product_id = r.product_id WHERE r.rating_effectiveness IS NOT NULL GROUP BY c.category_id, c.category_default HAVING COUNT(p.product_id) >= 10 ORDER BY avg_effectiveness DESC LIMIT 15;"
        headers = ["Kategori Produk", "Total Produk", "Skor Kemasan", "Skor Tekstur", "Skor Efektivitas"]
    elif selected_query == "agg4_repurchase":
        title = "AGG-4: Distribusi Repurchase per Kategori"
        description = "Menghitung persentase loyalitas konsumen yang menjawab YES untuk membeli kembali."
        query_sql = "SELECT c.category_default, SUM(CAST(e.total_repurchase_yes AS INT)) AS repurchase_yes, SUM(CAST(e.total_repurchase_no AS INT)) AS repurchase_no, SUM(CAST(e.total_repurchase_yes AS INT) + CAST(e.total_repurchase_no AS INT) + CAST(e.total_repurchase_maybe AS INT)) AS total_responden, ROUND(SUM(CAST(e.total_repurchase_yes AS INT)) * 100.0 / NULLIF(SUM(CAST(e.total_repurchase_yes AS INT) + CAST(e.total_repurchase_no AS INT) + CAST(e.total_repurchase_maybe AS INT)), 0), 2) AS pct_repurchase_yes FROM Category c JOIN Product p ON c.category_id = p.category_id JOIN Engagement e ON p.product_id = e.product_id GROUP BY c.category_id, c.category_default HAVING total_responden > 100 ORDER BY pct_repurchase_yes DESC LIMIT 15;"
        headers = ["Kategori Produk", "Repurchase (Yes)", "Repurchase (No)", "Total Responden", "Persentase Yes (%)"]
    elif selected_query == "agg5_rentang":
        title = "AGG-5: Rentang Rating dan Harga per Brand"
        description = "Analisis variasi sebaran batas harga termurah-termahal serta rating atas-bawah untuk setiap brand."
        query_sql = "SELECT b.brand_name, COUNT(p.product_id) AS total_produk, MAX(CAST(p.average_rating AS FLOAT)) AS rating_tertinggi, MIN(CAST(p.average_rating AS FLOAT)) AS rating_terendah, ROUND(AVG(CAST(p.average_rating AS FLOAT)), 2) AS avg_rating, MAX(CAST(p.max_price AS INT)) AS harga_tertinggi, MIN(CAST(p.min_price AS INT)) AS harga_terendah FROM Brand b JOIN Product p ON b.brand_id = p.brand_id WHERE p.average_rating IS NOT NULL GROUP BY b.brand_id, b.brand_name HAVING COUNT(p.product_id) >= 5 ORDER BY avg_rating DESC LIMIT 15;"
        headers = ["Nama Brand", "Total Produk", "Rating Atas", "Rating Bawah", "Rata-rata Rating", "Harga Termahal", "Harga Termurah"]
    elif selected_query == "rank1_ulasan":
        title = "RANK-1: Top 10 Produk Ulasan Terbanyak"
        description = "Menampilkan 10 produk dengan interaksi kuantitas ulasan paling masif."
        query_sql = "SELECT p.product_name, b.brand_name, c.category_default, p.average_rating, e.total_reviews FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Engagement e ON p.product_id = e.product_id ORDER BY CAST(e.total_reviews AS INT) DESC LIMIT 10;"
        headers = ["Nama Produk", "Brand", "Kategori", "Avg Rating", "Total Ulasan"]
    elif selected_query == "rank2_rating":
        title = "RANK-2: Top 10 Produk Rating Tertinggi"
        description = "Menampilkan produk-produk dengan skor rating teratas (Syarat minimal 10 ulasan)."
        query_sql = "SELECT p.product_name, b.brand_name, c.category_default, p.average_rating, e.total_reviews FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Engagement e ON p.product_id = e.product_id WHERE CAST(e.total_reviews AS INT) >= 10 AND p.average_rating IS NOT NULL ORDER BY CAST(p.average_rating AS FLOAT) DESC LIMIT 10;"
        headers = ["Nama Produk", "Brand", "Kategori", "Avg Rating", "Total Ulasan"]
    elif selected_query == "rank3_wishlist":
        title = "RANK-3: Top 10 Produk Wishlist Terbanyak"
        description = "Daftar produk paling populer yang paling banyak disimpan ke wishlist."
        query_sql = "SELECT p.product_name, b.brand_name, c.category_default, p.min_price, e.total_in_wishlist FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Engagement e ON p.product_id = e.product_id ORDER BY CAST(e.total_in_wishlist AS INT) DESC LIMIT 10;"
        headers = ["Nama Produk", "Brand", "Kategori", "Harga Terendah", "Total Wishlist"]
    elif selected_query == "rank4_rekomendasi":
        title = "RANK-4: Top 10 Produk Rasio Rekomendasi Tertinggi"
        description = "Menampilkan produk teratas berdasarkan rasio rekomendasi dibanding total review (Minimal 50 ulasan)."
        query_sql = "SELECT p.product_name, b.brand_name, c.category_default, p.average_rating, e.total_reviews, e.total_recommend_count, ROUND(CAST(e.total_recommend_count AS FLOAT) * 100.0 / NULLIF(CAST(e.total_reviews AS INT), 0), 1) AS pct_rekomendasi FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id JOIN Engagement e ON p.product_id = e.product_id WHERE CAST(e.total_reviews AS INT) >= 50 ORDER BY pct_rekomendasi DESC LIMIT 10;"
        headers = ["Nama Produk", "Brand", "Kategori", "Avg Rating", "Total Ulasan", "Total Rekomendasi", "Rasio (%)"]
    elif selected_query == "rank5_termahal":
        title = "RANK-5: Top 10 Produk Termahal dengan Rating >= 4.0"
        description = "Menampilkan jajaran produk kelas premium/sultan dengan patokan batas minimal rating 4.0."
        query_sql = "SELECT p.product_name, b.brand_name, c.category_default, p.max_price, p.average_rating FROM Product p JOIN Brand b ON p.brand_id = b.brand_id JOIN Category c ON p.category_id = c.category_id WHERE CAST(p.average_rating AS FLOAT) >= 4.0 ORDER BY CAST(p.max_price AS INT) DESC LIMIT 10;"
        headers = ["Nama Produk", "Brand", "Kategori", "Harga Maksimal (Rp)", "Avg Rating"]

    try:
        cursor = conn.cursor()
        cursor.execute(query_sql)
        raw_rows = cursor.fetchall()
        data = [list(row) for row in raw_rows]
    except Exception as e:
        print(f"Error SQL: {e}")
        raw_rows = []
        data = []

# --- 2. LOGIKA GRAFIK DINAMIS: SESUAIKAN GRAFIK BERDASARKAN QUERY AKTIF ---
    chart_labels = []
    chart_values1 = []
    chart_values2 = []
    chart_title = "Visualisasi Distribusi Data"
    chart_type = "bar" 
    label_dataset1 = "Nilai"
    label_dataset2 = ""

    sample_data = raw_rows[:5]

    if "join" in selected_query:
        chart_title = "Top 5 Produk: Perbandingan Average Rating"
        chart_type = "bar"
        label_dataset1 = "Rata-rata Rating"
        for row in sample_data:
            chart_labels.append(row[3][:15] + "..." if len(row[3]) > 15 else row[3])
            chart_values1.append(float(row[6]) if row[6] else 0.0)

    elif selected_query == "agg1_brand":
        chart_title = "Top 5 Brand: Perbandingan Rata-rata Rating (AGG-1)"
        chart_type = "line"
        label_dataset1 = "Avg Rating"
        for row in sample_data:
            chart_labels.append(row[0])
            chart_values1.append(float(row[2]) if row[2] else 0.0)

    elif selected_query == "agg2_kategori":
        chart_title = "Top 5 Kategori: Akumulasi Jumlah Wishlist Pasar (AGG-2)"
        chart_type = "bar"
        label_dataset1 = "Total Wishlist"
        for row in sample_data:
            chart_labels.append(row[0])
            chart_values1.append(int(row[2]) if row[2] else 0)

    elif selected_query == "agg3_aspek":
        chart_title = "Top Kategori: Komparasi Kepuasan Kemasan vs Efektivitas (AGG-3)"
        chart_type = "bar"
        label_dataset1 = "Skor Kemasan"
        label_dataset2 = "Skor Efektivitas"
        for row in sample_data:
            chart_labels.append(row[0])
            chart_values1.append(float(row[2]) if row[2] else 0.0)
            chart_values2.append(float(row[4]) if row[4] else 0.0)

    elif selected_query == "agg4_repurchase":
        chart_title = "Top Kategori: Tingkat Loyalitas Repurchase Konsumen (%) (AGG-4)"
        chart_type = "bar"  # Diubah dari 'pie' menjadi 'bar'
        label_dataset1 = "Persentase Beli Kembali (Yes %)"
        for row in sample_data:
            chart_labels.append(row[0])  # Kolom 0 = Category Default
            chart_values1.append(float(row[4]) if row[4] else 0.0)  # Kolom 4 = pct_repurchase_yes (Sudah terurut DESC dari SQL)

    # 💰 GRAFIK HARGA 1: Membandingkan Harga Termahal antar Brand (AGG-5)
    elif selected_query == "agg5_rentang":
        chart_title = "Top Brand: Analisis Batas Harga Maksimal Produk (Rp) (AGG-5)"
        chart_type = "bar"
        label_dataset1 = "Harga Termahal"
        for row in sample_data:
            chart_labels.append(row[0])
            chart_values1.append(int(row[5]) if row[5] else 0) # Menarik kolom harga_tertinggi

    elif selected_query == "rank1_ulasan":
        chart_title = "Top 5 Produk: Kuantitas Ulasan Terbanyak (RANK-1)"
        chart_type = "bar"
        label_dataset1 = "Total Ulasan"
        for row in sample_data:
            chart_labels.append(row[0][:15] + "..." if len(row[0]) > 15 else row[0])
            chart_values1.append(int(row[4]) if row[4] else 0)

    elif selected_query == "rank2_rating":
        chart_title = "Top 5 Produk: Urutan Rating Tertinggi (RANK-2)"
        chart_type = "bar"
        label_dataset1 = "Skor Rating"
        for row in sample_data:
            chart_labels.append(row[0][:15] + "..." if len(row[0]) > 15 else row[0])
            chart_values1.append(float(row[3]) if row[3] else 0.0)

    # 💰 GRAFIK HARGA 2: Membandingkan Harga Terendah Produk Populer (RANK-3)
    elif selected_query == "rank3_wishlist":
        chart_title = "Top 5 Wishlist: Perbandingan Harga Minimum Produk Terpopuler (Rp) (RANK-3)"
        chart_type = "bar"
        label_dataset1 = "Harga Minimum (Rp)"
        for row in sample_data:
            chart_labels.append(row[0][:15] + "..." if len(row[0]) > 15 else row[0])
            chart_values1.append(int(row[3]) if row[3] else 0) # Menarik kolom min_price

    elif selected_query == "rank4_rekomendasi":
        chart_title = "Top 5 Produk: Rasio Rekomendasi Tertinggi (%) (RANK-4)"
        chart_type = "bar"
        label_dataset1 = "Rasio Rekomendasi"
        for row in sample_data:
            chart_labels.append(row[0][:15] + "..." if len(row[0]) > 15 else row[0])
            chart_values1.append(float(row[6]) if row[6] else 0.0)

    # 💰 GRAFIK HARGA 3: Mengurutkan Jajaran Produk Kelas Sultan Premium (RANK-5)
    elif selected_query == "rank5_termahal":
        chart_title = "Top Sultan Premium: Urutan Produk Kosmetik Termahal (Rp) (RANK-5)"
        chart_type = "bar"
        label_dataset1 = "Harga Maksimal (Rp)"
        for row in sample_data:
            chart_labels.append(row[0][:15] + "..." if len(row[0]) > 15 else row[0])
            chart_values1.append(int(row[3]) if row[3] else 0) # Menarik kolom max_price

    conn.close()
    return render_template(
        "analysis.html", 
        data=data, headers=headers, title=title, description=description, selected_query=selected_query,
        chart_labels=chart_labels, chart_values1=chart_values1, chart_values2=chart_values2,
        chart_title=chart_title, chart_type=chart_type, label_dataset1=label_dataset1, label_dataset2=label_dataset2
    )

# ==========================================
# PAGE 3: INPUT MANAGEMENT (SEARCH, INSERT, DELETE)
# ==========================================
@app.route("/input")
def input_page():
    conn = get_db_connection()
    brands = conn.execute("SELECT * FROM Brand ORDER BY brand_name ASC;").fetchall()
    categories = conn.execute("SELECT * FROM Category ORDER BY category_default ASC;").fetchall()
    
    # Tangkap kata kunci pencarian jika ada
    keyword = request.args.get('search_keyword', '').strip()
    
    if keyword:
        # Jika user mencari sesuatu (bisa berupa potongan nama produk atau angka ID langsung)
        query = "SELECT * FROM Product WHERE product_name LIKE ? OR product_id = ? ORDER BY product_id DESC;"
        products = conn.execute(query, (f"%{keyword}%", keyword if keyword.isdigit() else -1)).fetchall()
    else:
        # Jika normal, tampilkan 100 baris terbaru
        products = conn.execute("SELECT * FROM Product ORDER BY product_id DESC LIMIT 100;").fetchall()
        
    conn.close()
    return render_template("input.html", brands=brands, categories=categories, products=products)

@app.route("/add_product", methods=["POST"])
def add_product():
    # 1. Informasi Utama (Wajib diisi)
    product_name = request.form.get("product_name")
    brand_id = request.form.get("brand_id")
    category_id = request.form.get("category_id")
    min_price = request.form.get("min_price")
    max_price = request.form.get("max_price")
    beauty_point = request.form.get("beauty_point")
    average_rating = request.form.get("average_rating")

    # 2. Skor Kualitas Aspek (Boleh Kosong - Diberi proteksi default 0.0 jika kosong)
    rating_packaging = request.form.get("rating_packaging") or 0.0
    rating_texture = request.form.get("rating_texture") or 0.0
    rating_effectiveness = request.form.get("rating_effectiveness") or 0.0
    rating_value_for_money = request.form.get("rating_value_for_money") or 0.0
    rating_long_wear = request.form.get("rating_long_wear") or 0.0
    rating_scent = request.form.get("rating_scent") or 0.0

    # 3. Statistik Engagement Pasar (Boleh Kosong - Diberi proteksi default 0 jika kosong)
    total_reviews = request.form.get("total_reviews") or 0
    total_recommend_count = request.form.get("total_recommend_count") or 0
    total_in_wishlist = request.form.get("total_in_wishlist") or 0
    total_repurchase_yes = request.form.get("total_repurchase_yes") or 0
    total_repurchase_no = request.form.get("total_repurchase_no") or 0
    total_repurchase_maybe = request.form.get("total_repurchase_maybe") or 0

    conn = get_db_connection()
    try:
        # --- EKSEKUSI INSERT KE TABEL PRODUCT ---
        # (Sesuaikan susunan kolom SQL Insert kelompokmu di bawah ini)
        conn.execute("""
            INSERT INTO Product (product_name, brand_id, category_id, min_price, max_price, beauty_point_earned, average_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (product_name, brand_id, category_id, min_price, max_price, beauty_point, average_rating))
        
        # Ambil ID produk yang barusan otomatis terbit dari database autoincrement
        new_product_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]

        # --- EKSEKUSI INSERT KE TABEL RATING ASPEK ---
        conn.execute("""
            INSERT INTO Rating (product_id, rating_packaging, rating_texture, rating_effectiveness, rating_value_for_money, rating_long_wear, rating_scent)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (new_product_id, rating_packaging, rating_texture, rating_effectiveness, rating_value_for_money, rating_long_wear, rating_scent))

        # --- EKSEKUSI INSERT KE TABEL ENGAGEMENT ---
        conn.execute("""
            INSERT INTO Engagement (product_id, total_reviews, total_recommend_count, total_in_wishlist, total_repurchase_yes, total_repurchase_no, total_repurchase_maybe)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (new_product_id, total_reviews, total_recommend_count, total_in_wishlist, total_repurchase_yes, total_repurchase_no, total_repurchase_maybe))

        conn.commit()
        flash("Sukses! Produk baru beserta seluruh aspek relasionalnya berhasil disimpan.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Gagal menyimpan ke database! Eror: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect("/input")

# PASTIKAN ada 'GET' di dalam list methods-nya, atau hapus saja parameter methods-nya!
@app.route('/delete_product/<int:product_id>', methods=['GET', 'POST'])
def delete_product(product_id):
    conn = get_db_connection()
    try:
        # Hapus dulu di tabel relasi anak (Rating & Engagement) agar tidak melanggar Foreign Key Constraint
        conn.execute("DELETE FROM Rating WHERE product_id = ?;", (product_id,))
        conn.execute("DELETE FROM Engagement WHERE product_id = ?;", (product_id,))
        
        # Baru hapus di tabel utama (Product)
        conn.execute("DELETE FROM Product WHERE product_id = ?;", (product_id,))
        
        conn.commit()
        flash(f"Sukses! Data produk ID #{product_id} berhasil dihapus dari database.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Gagal menghapus data! Eror: {str(e)}", "danger")
    finally:
        conn.close()
        
    return redirect('/input')

# --- PROSES PERBARUI DATA (FITUR UPDATE RECORD) ---
# --- PROSES PERBARUI DATA (ANTI-OVERWRITE JIKA INPUT DIKOSONGKAN) ---
@app.route("/update_product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    conn = get_db_connection()
    
    # 🔍 LANGKAH 1: Ambil data lama yang saat ini ada di database sebagai cadangan
    old_p = conn.execute("SELECT * FROM Product WHERE product_id = ?;", (product_id,)).fetchone()
    old_r = conn.execute("SELECT * FROM Rating WHERE product_id = ?;", (product_id,)).fetchone()
    old_e = conn.execute("SELECT * FROM Engagement WHERE product_id = ?;", (product_id,)).fetchone()

    # 🔍 LANGKAH 2: Tangkap data dari form. Jika kosong/"" atau tidak diisi, gunakan data lama!
    product_name = request.form.get("product_name") or old_p["product_name"]
    brand_id = request.form.get("brand_id") or old_p["brand_id"]
    category_id = request.form.get("category_id") or old_p["category_id"]
    
    # Untuk angka, kita pastikan jika formnya kosong, pakai nilai lama
    min_price = request.form.get("min_price")
    min_price = int(min_price) if min_price else old_p["min_price"]
    
    max_price = request.form.get("max_price")
    max_price = int(max_price) if max_price else old_p["max_price"]
    
    average_rating = request.form.get("average_rating")
    average_rating = float(average_rating) if average_rating else old_p["average_rating"]
    
    beauty_point = request.form.get("beauty_point")
    beauty_point = int(beauty_point) if beauty_point else old_p["beauty_point_earned"]

    # --- Bagian Tabel Rating (Aspek Fisik) ---
    r_pkg = request.form.get("rating_packaging")
    r_pkg = float(r_pkg) if r_pkg else old_r["rating_packaging"]
    
    r_txt = request.form.get("rating_texture")
    r_txt = float(r_txt) if r_txt else old_r["rating_texture"]
    
    r_eff = request.form.get("rating_effectiveness")
    r_eff = float(r_eff) if r_eff else old_r["rating_effectiveness"]
    
    r_val = request.form.get("rating_value_for_money")
    r_val = float(r_val) if r_val else old_r["rating_value_for_money"]
    
    r_lng = request.form.get("rating_long_wear")
    r_lng = float(r_lng) if r_lng else old_r["rating_long_wear"]
    
    r_snt = request.form.get("rating_scent")
    r_snt = float(r_snt) if r_snt else old_r["rating_scent"]

    # --- Bagian Tabel Engagement (Aktivitas Pasar) ---
    t_rev = request.form.get("total_reviews")
    t_rev = int(t_rev) if t_rev else old_e["total_reviews"]
    
    t_rec = request.form.get("total_recommend_count")
    t_rec = int(t_rec) if t_rec else old_e["total_recommend_count"]
    
    t_wsh = request.form.get("total_in_wishlist")
    t_wsh = int(t_wsh) if t_wsh else old_e["total_in_wishlist"]
    
    r_yes = request.form.get("total_repurchase_yes")
    r_yes = int(r_yes) if r_yes else old_e["total_repurchase_yes"]
    
    r_no = request.form.get("total_repurchase_no")
    r_no = int(r_no) if r_no else old_e["total_repurchase_no"]
    
    r_may = request.form.get("total_repurchase_maybe")
    r_may = int(r_may) if r_may else old_e["total_repurchase_maybe"]

    try:
        # Eksekusi SQL UPDATE dengan nilai yang sudah divalidasi aman
        conn.execute("""
            UPDATE Product 
            SET brand_id = ?, category_id = ?, product_name = ?, min_price = ?, max_price = ?, beauty_point_earned = ?, average_rating = ?
            WHERE product_id = ?;
        """, (brand_id, category_id, product_name, min_price, max_price, beauty_point, average_rating, product_id))

        conn.execute("""
            UPDATE Rating 
            SET rating_packaging = ?, rating_texture = ?, rating_effectiveness = ?, rating_value_for_money = ?, rating_long_wear = ?, rating_scent = ?
            WHERE product_id = ?;
        """, (r_pkg, r_txt, r_eff, r_val, r_lng, r_snt, product_id))

        conn.execute("""
            UPDATE Engagement 
            SET total_reviews = ?, total_recommend_count = ?, total_in_wishlist = ?, total_repurchase_yes = ?, total_repurchase_no = ?, total_repurchase_maybe = ?
            WHERE product_id = ?;
        """, (t_rev, t_rec, t_wsh, r_yes, r_no, r_may, product_id))

        conn.commit()
        flash(f"Sukses! Perubahan data produk ID {product_id} berhasil disimpan.", "success")
    except Exception as e:
        flash(f"Gagal memperbarui data: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("input_management"))

if __name__ == "__main__":
    app.run(debug=True)
