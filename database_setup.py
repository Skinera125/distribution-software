import sqlite3

# Database se connection banayein
conn = sqlite3.connect('distribution.db')
cursor = conn.cursor()

print("✅ Database ban gaya: distribution.db")

# ===== 1. USERS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'cashier',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Users table")

# ===== 2. CUSTOMERS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    area TEXT,
    credit_limit REAL DEFAULT 0,
    opening_balance REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Customers table")

# ===== 3. SUPPLIERS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    company TEXT,
    opening_balance REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Suppliers table")

# ===== 4. PRODUCTS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT DEFAULT 'piece',
    purchase_price REAL DEFAULT 0,
    sale_price REAL DEFAULT 0,
    stock_qty REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Products table")

# ===== 5. PURCHASES TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    invoice_no TEXT,
    date TEXT,
    total_amount REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
)
''')
print("✅ Purchases table")

# ===== 6. PURCHASE_ITEMS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER,
    product_id INTEGER,
    qty REAL,
    price REAL,
    total REAL,
    FOREIGN KEY (purchase_id) REFERENCES purchases(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
)
''')
print("✅ Purchase_items table")

# ===== 7. SALES TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    invoice_no TEXT,
    date TEXT,
    subtotal REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
)
''')
print("✅ Sales table")

# ===== 8. SALE_ITEMS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    product_id INTEGER,
    qty REAL,
    price REAL,
    total REAL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
)
''')
print("✅ Sale_items table")

# ===== 9. PAYMENTS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_type TEXT,
    party_id INTEGER,
    amount REAL,
    type TEXT,
    method TEXT DEFAULT 'cash',
    date TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
print("✅ Payments table")

# ===== 10. STOCK_MOVEMENTS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    type TEXT,
    qty REAL,
    reference TEXT,
    date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
''')
print("✅ Stock_movements table")

# ===== 11. SETTINGS TABLE =====
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,
    value TEXT
)
''')
print("✅ Settings table")

# ===== DEFAULT ADMIN USER =====
cursor.execute('''
INSERT OR IGNORE INTO users (username, password, full_name, role)
VALUES ('admin', 'admin123', 'Administrator', 'admin')
''')
print("✅ Admin user (username: admin, password: admin123)")

# ===== DEFAULT SETTINGS =====
cursor.execute('''
INSERT OR IGNORE INTO settings (key, value) VALUES ('company_name', 'Meri Distribution Company')
''')
cursor.execute('''
INSERT OR IGNORE INTO settings (key, value) VALUES ('currency', 'Rs')
''')
print("✅ Default settings")

# ===== SAVE =====
conn.commit()
conn.close()

print("\n🎉 MUBARAK HO! Poora database tayyar hai.")
print("📁 File: distribution.db")