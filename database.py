import sqlite3

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    # جدول المستخدمين وصلاحيات النظام
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL)''')
    
    # جدول الأصناف والمخزون
    conn.execute('''CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    min_qty REAL DEFAULT 0,
                    category TEXT NOT NULL)''')
    
    # جدول حركة المخزون (صادر ووارد)
    conn.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    move_type TEXT NOT NULL,
                    qty REAL NOT NULL,
                    move_date TEXT NOT NULL,
                    ref_type TEXT,
                    ref_id INTEGER,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # جدول أذونات الشراء وتوريد المواد
    conn.execute('''CREATE TABLE IF NOT EXISTS purchase_vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_no TEXT UNIQUE NOT NULL,
                    voucher_date TEXT NOT NULL,
                    supplier TEXT,
                    invoice_no TEXT,
                    receiver_name TEXT,
                    created_by INTEGER)''')

    # جدول بنود الشراء التفصيلية
    conn.execute('''CREATE TABLE IF NOT EXISTS purchase_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_id INTEGER,
                    item_id INTEGER,
                    qty REAL,
                    price REAL)''')

    # جدول أذونات صرف المواد من المخزن
    conn.execute('''CREATE TABLE IF NOT EXISTS issue_vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_no TEXT UNIQUE NOT NULL,
                    voucher_date TEXT NOT NULL,
                    department TEXT,
                    created_by INTEGER)''')

    # جدول بنود الصرف التفصيلية
    conn.execute('''CREATE TABLE IF NOT EXISTS issue_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_id INTEGER,
                    item_id INTEGER,
                    qty REAL)''')

    # جدول الحركات المالية والخزينة (إيرادات، مصروفات، عهد، ورواتب)
    conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    expense_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    payment_method TEXT,
                    created_by INTEGER)''')

    # جدول العهد (تسليم واستلام المعدات والأدوات)
    conn.execute('''CREATE TABLE IF NOT EXISTS equipment_vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_no TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    worker_name TEXT NOT NULL,
                    voucher_date TEXT NOT NULL,
                    notes TEXT,
                    created_by INTEGER)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS equipment_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_id INTEGER,
                    item_id INTEGER,
                    qty REAL,
                    condition TEXT)''')

    # جدول الموظفين (الأسماء والمرتب الأساسي)
    conn.execute('''CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    default_salary REAL NOT NULL)''')

    # جدول سجل سداد الرواتب
    conn.execute('''CREATE TABLE IF NOT EXISTS salary_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    employee_name TEXT NOT NULL,
                    month TEXT NOT NULL,
                    amount REAL NOT NULL,
                    pay_date TEXT NOT NULL,
                    created_by INTEGER)''')

    # التأكد من إضافة الأعمدة الجديدة (الحالة والخصومات) إذا لم تكن موجودة مسبقاً في الجدول القديم
    try:
        conn.execute("ALTER TABLE salary_payments ADD COLUMN status TEXT DEFAULT 'منتظم'")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE salary_payments ADD COLUMN deduction REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE salary_payments ADD COLUMN deduction_reason TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()