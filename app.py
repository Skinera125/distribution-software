import os
import json
import datetime
import csv
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, Response
from db import get_db

app = Flask(__name__)
app.secret_key = 'distribution-software-secret-key-2026'

# ===== DATABASE INITIALIZATION (INTERNET KE LIYE) =====
def init_db():
    """Agar database file nahi hai toh naya bana kar tables create karein"""
    conn = sqlite3.connect('distribution.db')
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT)''')
    cursor.execute('''INSERT OR IGNORE INTO users (username, password, full_name, role) VALUES ('admin', 'admin123', 'Administrator', 'admin')''')
    
    # Customers Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, opening_balance REAL DEFAULT 0)''')
    
    # Products Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, purchase_price REAL, sale_price REAL, stock_qty REAL, batch_no TEXT, expiry_date TEXT)''')
    
    # Sales Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, date TEXT, total_amount REAL, paid_amount REAL, status TEXT)''')
    
    # Sale Items Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS sale_items (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, product_id INTEGER, qty REAL, price REAL, total REAL, bonus_qty REAL DEFAULT 0)''')
    
    # Payments Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, party_type TEXT, party_id INTEGER, amount REAL, type TEXT, method TEXT, date TEXT, note TEXT)''')
    
    conn.commit()
    conn.close()

# Server start hone se pehle database check karein
init_db()

# ===== HOME / LOGIN =====
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # 1. Today's Total Sale
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_sale_data = conn.execute("SELECT SUM(total_amount) FROM sales WHERE date = ?", (today,)).fetchone()
    today_sale = today_sale_data[0] if today_sale_data[0] else 0
    
    # 2. Total Customers
    total_customers = conn.execute("SELECT COUNT(id) FROM customers").fetchone()[0]
    
    # 3. Total Products
    total_products = conn.execute("SELECT COUNT(id) FROM products").fetchone()[0]
    
    # 4. Total Receivables (Udhar)
    total_udhar_data = conn.execute("SELECT SUM(opening_balance) FROM customers").fetchone()
    total_udhar = total_udhar_data[0] if total_udhar_data[0] else 0
    
    conn.close()
    
    return render_template('dashboard.html', 
                           username=session['username'],
                           today_sale=today_sale,
                           total_customers=total_customers,
                           total_products=total_products,
                           total_udhar=total_udhar)

# ===== CUSTOMERS MODULE (With Search) =====
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        balance = request.form.get('balance', 0)
        if not balance: 
            balance = 0
            
        conn.execute('INSERT INTO customers (name, phone, address, opening_balance) VALUES (?, ?, ?, ?)', (name, phone, address, balance))
        conn.commit()
        return redirect(url_for('customers'))
        
    search_query = request.args.get('search', '')
    if search_query:
        customers_list = conn.execute('SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC', 
                                      ('%' + search_query + '%', '%' + search_query + '%')).fetchall()
    else:
        customers_list = conn.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
        
    conn.close()
    return render_template('customers.html', customers=customers_list, search_query=search_query, username=session['username'])

@app.route('/delete_customer/<int:id>')
def delete_customer(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM customers WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('customers'))

# ===== CUSTOMER LEDGER (KHATA) =====
@app.route('/customer_ledger/<int:customer_id>')
def customer_ledger(customer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if not customer:
        return "Customer not found!"
        
    sales_history = conn.execute('''
        SELECT id, date, total_amount, paid_amount, (total_amount - paid_amount) as due_amount 
        FROM sales 
        WHERE customer_id = ? 
        ORDER BY id DESC
    ''', (customer_id,)).fetchall()
    
    conn.close()
    
    return render_template('customer_ledger.html', customer=customer, sales_history=sales_history, username=session['username'])

# ===== PAYMENT (RECEIVE CASH) MODULE =====
@app.route('/receive_payment/<int:customer_id>', methods=['GET', 'POST'])
def receive_payment(customer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if not customer:
        return "Customer not found!"
        
    if request.method == 'POST':
        amount = float(request.form['amount'])
        note = request.form['note']
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        conn.execute('INSERT INTO payments (party_type, party_id, amount, type, method, date, note) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     ('customer', customer_id, amount, 'jama', 'cash', today, note))
        
        conn.execute('UPDATE customers SET opening_balance = opening_balance - ? WHERE id = ?', (amount, customer_id))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('customer_ledger', customer_id=customer_id))
        
    conn.close()
    return render_template('receive_payment.html', customer=customer, username=session['username'])

# ===== PRODUCTS MODULE =====
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        purchase_price = request.form['purchase_price']
        sale_price = request.form['sale_price']
        stock_qty = request.form['stock_qty']
        batch_no = request.form.get('batch_no', '')
        expiry_date = request.form.get('expiry_date', '')
        
        conn.execute('INSERT INTO products (name, category, purchase_price, sale_price, stock_qty, batch_no, expiry_date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                     (name, category, purchase_price, sale_price, stock_qty, batch_no, expiry_date))
        conn.commit()
        return redirect(url_for('products'))
        
    products_list = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('products.html', products=products_list, username=session['username'])

# ===== PURCHASE (ADD STOCK) MODULE =====
@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        qty = float(request.form['qty'])
        purchase_price = float(request.form['purchase_price'])
        
        conn.execute('UPDATE products SET stock_qty = stock_qty + ?, purchase_price = ? WHERE id = ?', 
                     (qty, purchase_price, product_id))
        conn.commit()
        return redirect(url_for('purchase'))
        
    products_list = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    
    return render_template('purchase.html', products=products_list, username=session['username'])

# ===== SALES LIST (With Search) =====
@app.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    search_query = request.args.get('search', '')
    if search_query:
        sales_list = conn.execute('''
            SELECT sales.id, customers.name as customer_name, sales.total_amount, sales.paid_amount, sales.date 
            FROM sales JOIN customers ON sales.customer_id = customers.id
            WHERE customers.name LIKE ? OR sales.id LIKE ?
            ORDER BY sales.id DESC
        ''', ('%' + search_query + '%', '%' + search_query + '%')).fetchall()
    else:
        sales_list = conn.execute('''
            SELECT sales.id, customers.name as customer_name, sales.total_amount, sales.paid_amount, sales.date 
            FROM sales JOIN customers ON sales.customer_id = customers.id
            ORDER BY sales.id DESC
        ''').fetchall()
        
    conn.close()
    
    return render_template('sales.html', sales=sales_list, search_query=search_query, username=session['username'])

# ===== NEW SALE (Search & Multiple Items) =====
@app.route('/new_sale')
def new_sale():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    customers_list = conn.execute('SELECT * FROM customers').fetchall()
    products_list = conn.execute('SELECT * FROM products WHERE stock_qty > 0').fetchall()
    conn.close()
    
    return render_template('new_sale.html', customers=customers_list, products=products_list, username=session['username'])

@app.route('/save_new_sale', methods=['POST'])
def save_new_sale():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    customer_id = request.form['customer_id']
    total_amount = float(request.form['total_amount'])
    paid_amount = float(request.form['paid_amount'])
    items_json = request.form['items_json']
    
    if not customer_id:
        return "Please select a customer first!"

    items = json.loads(items_json)
    conn = get_db()
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    status = 'completed' if paid_amount >= total_amount else 'pending'
    
    cursor = conn.execute('INSERT INTO sales (customer_id, date, total_amount, paid_amount, status) VALUES (?, ?, ?, ?, ?)',
                          (customer_id, today, total_amount, paid_amount, status))
    sale_id = cursor.lastrowid
    
    for item in items:
        p_id = item['productId']
        qty = float(item['qty'])
        bonus = float(item['bonus'])
        price = float(item['price'])
        net_amount = float(item['netAmount'])
        
        conn.execute('INSERT INTO sale_items (sale_id, product_id, qty, price, total, bonus_qty) VALUES (?, ?, ?, ?, ?, ?)',
                     (sale_id, p_id, qty, price, net_amount, bonus))
        
        total_out = qty + bonus
        conn.execute('UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?', (total_out, p_id))
        
    balance_due = total_amount - paid_amount
    if balance_due > 0:
        conn.execute('UPDATE customers SET opening_balance = opening_balance + ? WHERE id = ?', (balance_due, customer_id))
        
    conn.commit()
    conn.close()
    
    return redirect(url_for('invoice', sale_id=sale_id))

# ===== INVOICE PRINT =====
@app.route('/invoice/<int:sale_id>')
def invoice(sale_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    sale = conn.execute('''
        SELECT sales.id, sales.date, sales.total_amount, sales.paid_amount, 
               customers.id as customer_id, customers.name as customer_name, customers.address as customer_address
        FROM sales 
        JOIN customers ON sales.customer_id = customers.id 
        WHERE sales.id = ?
    ''', (sale_id,)).fetchone()
    
    items = conn.execute('''
        SELECT products.name as product_name, products.batch_no, products.expiry_date, 
               sale_items.qty, sale_items.price, sale_items.total, sale_items.bonus_qty 
        FROM sale_items 
        JOIN products ON sale_items.product_id = products.id 
        WHERE sale_items.sale_id = ?
    ''', (sale_id,)).fetchall()
    
    conn.close()
    
    if not sale:
        return "Sale not found!"
        
    return render_template('invoice.html', 
                           sale_id=sale['id'], 
                           customer_id=sale['customer_id'],
                           customer_name=sale['customer_name'],
                           customer_address=sale['customer_address'],
                           date=sale['date'],
                           total_amount=sale['total_amount'], 
                           paid_amount=sale['paid_amount'],
                           items=items)

# ===== REPORTS MODULE =====
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    total_sales_data = conn.execute("SELECT SUM(total_amount) FROM sales").fetchone()
    total_sales = total_sales_data[0] if total_sales_data[0] else 0
    
    profit_data = conn.execute('''
        SELECT SUM((sale_items.price - products.purchase_price) * sale_items.qty) 
        FROM sale_items 
        JOIN products ON sale_items.product_id = products.id
    ''').fetchone()
    total_profit = profit_data[0] if profit_data[0] else 0
    
    stock_data = conn.execute("SELECT SUM(stock_qty * purchase_price) FROM products").fetchone()
    stock_value = stock_data[0] if stock_data[0] else 0
    
    receivables_data = conn.execute("SELECT SUM(opening_balance) FROM customers").fetchone()
    total_receivables = receivables_data[0] if receivables_data[0] else 0
    
    conn.close()
    
    return render_template('reports.html', 
                           total_sales=total_sales, 
                           total_profit=total_profit, 
                           stock_value=stock_value, 
                           total_receivables=total_receivables,
                           username=session['username'])

# ===== STAFF / USER MANAGEMENT =====
@app.route('/users', methods=['GET', 'POST'])
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') != 'admin':
        return "Access Denied! Only Admin can add users."
    
    conn = get_db()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        
        try:
            conn.execute('INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)',
                         (username, password, full_name, role))
            conn.commit()
        except:
            return "Username already exists!"
            
        return redirect(url_for('users'))
        
    users_list = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    
    return render_template('users.html', users=users_list, username=session['username'])

# ===== BACKUP MODULE (CSV EXPORT) =====
@app.route('/backup')
def backup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    customers = conn.execute('SELECT * FROM customers').fetchall()
    products = conn.execute('SELECT * FROM products').fetchall()
    sales = conn.execute('SELECT * FROM sales').fetchall()
    
    conn.close()
    
    def generate():
        yield '--- CUSTOMERS DATA ---\n'
        yield 'ID,Name,Phone,Address,Balance\n'
        for c in customers:
            yield f"{c['id']},{c['name']},{c['phone']},{c['address']},{c['opening_balance']}\n"
            
        yield '\n--- PRODUCTS DATA ---\n'
        yield 'ID,Name,Category,Purchase Price,Sale Price,Stock\n'
        for p in products:
            yield f"{p['id']},{p['name']},{p['category']},{p['purchase_price']},{p['sale_price']},{p['stock_qty']}\n"

        yield '\n--- SALES DATA ---\n'
        yield 'Sale ID,Customer ID,Date,Total Amount,Paid Amount\n'
        for s in sales:
            yield f"{s['id']},{s['customer_id']},{s['date']},{s['total_amount']},{s['paid_amount']}\n"

    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=distribution_backup.csv'})

if __name__ == '__main__':
    print("🚀 Server running at: http://127.0.0.1:5000")
    app.run(debug=True)