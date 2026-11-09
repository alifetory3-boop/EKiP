import sqlite3
import os

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

    # جدول الأرشيف والمستندات المرفوعة (دعم ملفات Word و Excel)
    conn.execute('''CREATE TABLE IF NOT EXISTS uploaded_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by INTEGER)''')

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

    # إدخال الأصناف الـ 86 الرسمية تلقائياً إذا كان الجدول فارغاً لضمان عدم اختفاء أي صنف
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items")
    if cursor.fetchone()[0] == 0:
        official_items = [
            # أدوات
            ('TL-01', 'مفتاح ربط', 'حبة', 5, 'أدوات'),
            ('TL-02', 'مطرقة', 'حبة', 5, 'أدوات'),
            ('TL-03', 'منشار', 'حبة', 5, 'أدوات'),
            ('TL-04', 'قفازات عمل', 'زوج', 5, 'أدوات'),
            ('TL-05', 'خوذة سلامة', 'حبة', 5, 'أدوات'),
            
            # المطبخ
            ('KH-01', 'بصل حويل', 'كيلو', 10, 'المطبخ'),
            ('KH-02', 'ثوم', 'كيلو', 5, 'المطبخ'),
            ('KH-03', 'بطاطا', 'كيلو', 20, 'المطبخ'),
            ('KH-04', 'طماطم', 'كيلو', 20, 'المطبخ'),
            ('KH-05', 'كوسة', 'كيلو', 10, 'المطبخ'),
            ('KH-06', 'باذنجان', 'كيلو', 10, 'المطبخ'),
            ('KH-07', 'بامية', 'كيلو', 10, 'المطبخ'),
            ('KH-08', 'ليمون', 'كيلو', 5, 'المطبخ'),
            ('KH-09', 'كزبرة', 'حزمة', 10, 'المطبخ'),
            ('KH-10', 'معدنوس', 'حزمة', 10, 'المطبخ'),
            ('KH-11', 'نعناع', 'حزمة', 10, 'المطبخ'),
            ('TM-01', 'سكر', 'كيس', 10, 'المطبخ'),
            ('TM-02', 'شاي أخضر', 'علبة', 5, 'المطبخ'),
            ('TM-03', 'شاي أحمر', 'علبة', 5, 'المطبخ'),
            ('TM-04', 'رز حبة قصيرة', 'كيس', 15, 'المطبخ'),
            ('TM-05', 'رز طويلة', 'كيس', 15, 'المطبخ'),
            ('TM-06', 'مكرونة سبقا', 'كرتون', 10, 'المطبخ'),
            ('TM-07', 'مكرونة حراجيم', 'كرتون', 10, 'المطبخ'),
            ('TM-08', 'مكرونة بينه', 'كرتون', 10, 'المطبخ'),
            ('TM-09', 'زيت عباد الشمس', 'تنكة', 10, 'المطبخ'),
            ('TM-10', 'زيت زيتون', 'تنكة', 5, 'المطبخ'),
            ('TM-11', 'معجون طماطم', 'علبة', 20, 'المطبخ'),
            ('TM-12', 'خبزة مطحونة', 'كيس', 10, 'المطبخ'),
            ('TM-13', 'زبدة', 'علبة', 10, 'المطبخ'),
            ('TM-14', 'تن (تونة)', 'علبة', 20, 'المطبخ'),
            ('TM-15', 'جبنة', 'علبة', 15, 'المطبخ'),
            ('TM-16', 'فاصولياء', 'كيس', 10, 'المطبخ'),
            ('TM-17', 'عدس', 'كيس', 10, 'المطبخ'),
            ('TM-18', 'حمص', 'كيس', 10, 'المطبخ'),
            ('TM-19', 'بهارات مشكلة', 'علبة', 5, 'المطبخ'),
            ('TM-20', 'لحم بقري قطع', 'كيلو', 20, 'المطبخ'),
            ('TM-21', 'لحم بقري مفروم', 'كيلو', 20, 'المطبخ'),
            ('TM-22', 'دجاج (دجاجة)', 'حبة', 30, 'المطبخ'),
            ('TM-23', 'صدور الدجاج', 'كيلو', 20, 'المطبخ'),
            ('TM-24', 'حليب باكو', 'كرتون', 15, 'المطبخ'),
            ('TM-25', 'حليب سنتوب', 'كرتون', 15, 'المطبخ'),
            ('TM-26', 'دقيق', 'كيس', 20, 'المطبخ'),
            ('TM-27', 'سميد', 'كيس', 10, 'المطبخ'),
            ('TM-28', 'برغل ناعم', 'كيس', 10, 'المطبخ'),
            ('TM-29', 'برغل خشن', 'كيس', 10, 'المطبخ'),
            ('TM-30', 'لسان عصفور', 'كيس', 10, 'المطبخ'),
            ('TM-31', 'ملح طعام', 'كيس', 10, 'المطبخ'),
            ('TM-32', 'جلجلان / سمسم', 'كيس', 5, 'المطبخ'),
            ('TM-33', 'طحينية', 'علبة', 5, 'المطبخ'),

            # سباكة
            ('PL-01', 'ماسورة PVC', 'قطعة', 10, 'سباكة'),
            ('PL-02', 'ماسورة PPR', 'قطعة', 10, 'سباكة'),
            ('PL-03', 'كوع ماسورة', 'حبة', 20, 'سباكة'),
            ('PL-04', 'محبس مياه', 'حبة', 5, 'سباكة'),
            ('PL-05', 'خلاط مياه', 'حبة', 5, 'سباكة'),

            # سلامة
            ('SF-01', 'طفاية حريق', 'حبة', 5, 'سلامة'),
            ('SF-02', 'حزام أمان', 'حبة', 5, 'سلامة'),
            ('SF-03', 'نظارات واقية', 'حبة', 10, 'سلامة'),
            ('SF-04', 'لافتة إرشادية', 'حبة', 5, 'سلامة'),

            # قطع غيار
            ('SP-01', 'زيت محرك', 'تنكة', 5, 'قطع غيار'),
            ('SP-02', 'فلتر زيت', 'حبة', 5, 'قطع غيار'),
            ('SP-03', 'فلتر هواء', 'حبة', 5, 'قطع غيار'),
            ('SP-04', 'إطار سيارة', 'حبة', 4, 'قطع غيار'),
            ('SP-05', 'بطارية سيارة', 'حبة', 3, 'قطع غيار'),
            ('SP-06', 'شمعات احتراق', 'طقم', 5, 'قطع غيار'),

            # كهرباء
            ('EL-01', 'سلك كهرباء 1.5مم', 'لفة', 5, 'كهرباء'),
            ('EL-02', 'سلك كهرباء 2.5مم', 'لفة', 5, 'كهرباء'),
            ('EL-03', 'لمبة LED', 'حبة', 20, 'كهرباء'),
            ('EL-04', 'مفتاح كهرباء', 'حبة', 15, 'كهرباء'),
            ('EL-05', 'مقبس كهرباء', 'حبة', 15, 'كهرباء'),
            ('EL-06', 'قاطع كهربائي', 'حبة', 5, 'كهرباء'),

         # مكتبية
            ('OF-01', 'ورق طباعة A4', 'رزمة', 10, 'مكتبية'),
            ('OF-02', 'أقلام جاف', 'علبة', 5, 'مكتبية'),
            ('OF-03', 'ملفات بلاستيك', 'حبة', 20, 'مكتبية'),
            ('OF-04', 'حبر طابعة', 'خرطوشة', 3, 'مكتبية'),

            # مواد بناء
            ('BL-01', 'أسمنت', 'كيس', 50, 'مواد بناء'),
            ('BL-02', 'حديد تسليح 12مم', 'طن', 5, 'مواد بناء'),
            ('BL-03', 'حديد تسليح 16مم', 'طن', 5, 'مواد بناء'),
            ('BL-04', 'رمل', 'متر مكعب', 20, 'مواد بناء'),
            ('BL-05', 'حصى', 'متر مكعب', 20, 'مواد بناء'),
            ('BL-06', 'طوب', 'ألف حبة', 10, 'مواد بناء'),
            ('BL-07', 'بلاط', 'متر مربع', 50, 'مواد بناء'),
            ('BL-08', 'دهان بلاستيك', 'برميل', 10, 'مواد بناء'),
            ('BL-09', 'دهان زيتي', 'برميل', 10, 'مواد بناء'),
            ('BL-10', 'أسلاك كهرباء', 'لفة', 5, 'مواد بناء'),
            ('BL-11', 'مواسير مياه', 'قطعة', 10, 'مواد بناء'),
            ('BL-12', 'خشب', 'لوح', 20, 'مواد بناء')
        ]
        cursor.executemany("INSERT OR IGNORE INTO items (code, name, unit, min_qty, category) VALUES (?, ?, ?, ?, ?)", official_items)
        conn.commit()

    conn.commit()
    conn.close()
