from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from functools import wraps
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "secret-key-123"

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

init_db()

# إنشاء الجداول الأساسية وضمان جاهزيتها
conn = get_db()
conn.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    min_qty REAL DEFAULT 0,
    category TEXT DEFAULT 'عام'
);

CREATE TABLE IF NOT EXISTS purchase_vouchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_no TEXT UNIQUE NOT NULL,
    voucher_date TEXT NOT NULL,
    supplier TEXT NOT NULL,
    invoice_no TEXT,
    receiver_name TEXT,
    created_by INTEGER
);

CREATE TABLE IF NOT EXISTS purchase_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id INTEGER,
    item_id INTEGER,
    qty REAL NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    move_type TEXT,
    qty REAL,
    move_date TEXT,
    ref_type TEXT,
    ref_id INTEGER,
    created_by INTEGER
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    amount REAL,
    expense_date TEXT,
    category TEXT,
    payment_method TEXT,
    created_by INTEGER
);

CREATE TABLE IF NOT EXISTS user_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    user_fullname TEXT,
    action TEXT,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS advanced_salaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_name TEXT NOT NULL,
    basic_salary REAL DEFAULT 0.0,
    deductions REAL DEFAULT 0.0,
    bonuses REAL DEFAULT 0.0,
    advance REAL DEFAULT 0.0,
    bonus_receipt_type TEXT DEFAULT 'separate',
    month_year TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    default_salary REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS system_counters (
    prefix_key TEXT PRIMARY KEY,
    next_val INTEGER DEFAULT 2
);
""")
conn.commit()

# إدراج مستخدم مدير افتراضي إذا لم يكن موجوداً
if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    conn.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)", 
                 ('admin', generate_password_hash('admin123'), 'مدير النظام', 'admin'))
    conn.commit()

# إدراج أصناف افتراضية تلقائياً لضمان عدم ظهور القوائم فارغة أبداً
if conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
    default_items = [
        ("BL-01", "حديد تسليح 12 مم", "طن", 5, "مواد بناء"),
        ("BL-02", "أسمنت بورتلاندي", "كيس", 20, "مواد بناء"),
        ("EL-01", "سلك كهرباء 3 ملي", "لفة", 10, "كهرباء"),
        ("PL-01", "بوري بلاستيك 4 بوصة", "قطعة", 15, "سباكة"),
        ("SF-01", "خوذة سلامة ووقاية", "قطعة", 5, "سلامة"),
        ("TL-01", "مطرقة بناء", "قطعة", 2, "أدوات")
    ]
    for code, name, unit, min_qty, cat in default_items:
        conn.execute("INSERT OR IGNORE INTO items (code, name, unit, min_qty, category) VALUES (?, ?, ?, ?, ?)", 
                     (code, name, unit, min_qty, cat))
    conn.commit()

conn.close()

def get_next_sequence(prefix):
    db = get_db()
    row = db.execute("SELECT next_val FROM system_counters WHERE prefix_key = ?", (prefix,)).fetchone()
    if not row:
        db.execute("INSERT INTO system_counters (prefix_key, next_val) VALUES (?, 3)", (prefix,))
        db.commit()
        return 2
    else:
        val = row['next_val']
        db.execute("UPDATE system_counters SET next_val = next_val + 1 WHERE prefix_key = ?", (prefix,))
        db.commit()
        return val

def log_activity(action, details=""):
    try:
        user_id = session.get('user_id')
        username = session.get('username', 'مجهول')
        full_name = session.get('full_name', 'مجهول')
        db = get_db()
        db.execute(
            "INSERT INTO user_activity_log (user_id, username, user_fullname, action, details) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, action, details)
        )
        db.commit()
    except Exception as e:
        print("خطأ في تسجيل الحركة:", e)

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            user_role = session.get('role', 'user')
            if roles and user_role not in roles and user_role != 'admin':
                flash("عفواً، لا تملك الصلاحية للوصول لهذا القسم", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (request.form['username'],)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], request.form['password']):
            session.update({'user_id': user['id'], 'username': user['username'], 'full_name': user['full_name'], 'role': user['role']})
            log_activity("تسجيل دخول", f"قام المستخدم {user['full_name']} بتسجيل الدخول")
            return redirect(url_for('dashboard'))
        flash("خطأ في بيانات الدخول", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    log_activity("تسجيل خروج", f"قام المستخدم {session.get('full_name')} بتسجيل الخروج")
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    conn = get_db()
    items_count = conn.execute("SELECT COUNT(*) c FROM items").fetchone()['c']
    balances = conn.execute("SELECT i.code, i.name, i.unit, i.min_qty, i.category, COALESCE(SUM(CASE WHEN m.move_type='in' THEN m.qty ELSE -m.qty END),0) AS balance FROM items i LEFT JOIN stock_movements m ON m.item_id = i.id GROUP BY i.id").fetchall()
    conn.close()
    return render_template('dashboard.html', items_count=items_count, balances=balances, low_stock=[b for b in balances if b['balance'] < b['min_qty']])

@app.route('/issue')
@login_required()
def issue():
    return redirect(url_for('items'))

@app.route('/equipment_out')
@login_required()
def equipment_out():
    return redirect(url_for('issue'))

@app.route('/archive')
@login_required()
def archive():
    return redirect(url_for('dashboard'))

@app.route('/users_management', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def users_management():
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_user':
            username = request.form.get('username')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            role = request.form.get('role')
            p_hash = generate_password_hash(password)
            try:
                conn.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)", 
                             (username, p_hash, full_name, role))
                conn.commit()
                log_activity("إضافة مستخدم", f"تم إنشاء حساب: {full_name}")
                flash("تمت إضافة المستخدم بنجاح", "success")
            except Exception as e:
                flash(f"حدث خطأ: {e}", "danger")
        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            conn.execute("DELETE FROM users WHERE id=? AND username != 'admin'", (user_id,))
            conn.commit()
            log_activity("حذف مستخدم", f"تم حذف المستخدم رقم {user_id}")
            flash("تم حذف المستخدم", "success")
            
        return redirect(url_for('users_management'))
    
    users_list = conn.execute("SELECT id, username, full_name, role FROM users ORDER BY id").fetchall()
    logs = conn.execute("SELECT * FROM user_activity_log ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return render_template('users.html', users=users_list, logs=logs)

@app.route('/salaries', methods=['GET', 'POST'], endpoint='salaries')
@login_required(roles=['accountant'])
def salaries():
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add_employee':
                name = request.form.get('name')
                default_salary = float(request.form.get('default_salary', 0))
                conn.execute("INSERT INTO employees (name, default_salary) VALUES (?, ?)", (name, default_salary))
                conn.commit()
                log_activity("إضافة موظف", f"إضافة الموظف: {name}")
                flash("تم إضافة الموظف بنجاح", "success")
                conn.close()
                return redirect(url_for('salaries'))

            elif action == 'update_employee':
                emp_id = request.form.get('emp_id')
                name = request.form.get('name')
                default_salary = float(request.form.get('default_salary', 0))
                conn.execute("UPDATE employees SET name=?, default_salary=? WHERE id=?", (name, default_salary, emp_id))
                conn.commit()
                log_activity("تعديل موظف", f"تعديل الموظف رقم {emp_id}")
                flash("تم تعديل بيانات الموظف بنجاح", "success")
                conn.close()
                return redirect(url_for('salaries'))

            elif action == 'delete_employee':
                emp_id = request.form.get('emp_id')
                conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                conn.commit()
                log_activity("حذف موظف", f"حذف الموظف رقم {emp_id}")
                flash("تم حذف الموظف بنجاح", "success")
                conn.close()
                return redirect(url_for('salaries'))

            else:
                employee_id = request.form.get('employee_id')
                emp_record = conn.execute("SELECT name FROM employees WHERE id=?", (employee_id,)).fetchone()
                employee_name = emp_record['name'] if emp_record else request.form.get('employee_name', 'مجهول')
                
                basic_salary = float(request.form.get('basic_salary', 0))
                deductions = float(request.form.get('deductions', 0))
                bonuses = float(request.form.get('bonuses', 0))
                advance = float(request.form.get('advance', 0))
                bonus_receipt_type = request.form.get('bonus_receipt_type', 'separate')
                month_year = request.form.get('month_year') or date.today().strftime('%Y-%m-%d')

                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO advanced_salaries (employee_name, basic_salary, deductions, bonuses, advance, bonus_receipt_type, month_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (employee_name, basic_salary, deductions, bonuses, advance, bonus_receipt_type, month_year)
                )
                conn.commit()
                new_salary_id = cur.lastrowid
                
                log_activity("رصد راتب ومستحقات", f"تم تسجيل مستحقات الموظف: {employee_name} عن تاريخ {month_year}")
                conn.close()

                if bonus_receipt_type == 'bonus':
                    return redirect(url_for('print_bonus_receipt', id=new_salary_id))
                elif bonus_receipt_type == 'advance':
                    return redirect(url_for('print_advance_receipt', id=new_salary_id))
                else:
                    return redirect(url_for('print_salary_receipt', id=new_salary_id))

        except Exception as e:
            conn.close()
            flash(f"حدث خطأ: {e}", "danger")
            return redirect(url_for('salaries'))
    
    employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    salaries_list = conn.execute("SELECT * FROM advanced_salaries ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('salaries.html', employees=employees, salaries=salaries_list)

@app.route('/salaries/print/work_letter/<int:id>')
@login_required(roles=['accountant'])
def print_work_letter(id):
    conn = get_db()
    emp = conn.execute("SELECT * FROM employees WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('print_work_letter.html', emp=emp)

@app.route('/salaries/edit/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['accountant'])
def edit_salary(id):
    conn = get_db()
    if request.method == 'POST':
        employee_name = request.form.get('employee_name')
        basic_salary = float(request.form.get('basic_salary', 0))
        deductions = float(request.form.get('deductions', 0))
        bonuses = float(request.form.get('bonuses', 0))
        advance = float(request.form.get('advance', 0))
        bonus_receipt_type = request.form.get('bonus_receipt_type', 'separate')
        month_year = request.form.get('month_year')

        conn.execute(
            "UPDATE advanced_salaries SET employee_name=?, basic_salary=?, deductions=?, bonuses=?, advance=?, bonus_receipt_type=?, month_year=? WHERE id=?",
            (employee_name, basic_salary, deductions, bonuses, advance, bonus_receipt_type, month_year, id)
        )
        conn.commit()
        log_activity("تعديل مستحقات", f"تم تعديل السجل المالي رقم {id}")
        flash("تم تعديل السجل بنجاح", "success")
        conn.close()
        return redirect(url_for('salaries'))
    
    salary = conn.execute("SELECT * FROM advanced_salaries WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('edit_salary.html', salary=salary)

@app.route('/salaries/delete/<int:id>')
@login_required(roles=['accountant'])
def delete_salary(id):
    conn = get_db()
    conn.execute("DELETE FROM advanced_salaries WHERE id=?", (id,))
    conn.commit()
    log_activity("حذف مستحقات", f"تم حذف السجل المالي رقم {id}")
    flash("تم حذف السجل بنجاح", "success")
    conn.close()
    return redirect(url_for('salaries'))

@app.route('/salaries/print/salary/<int:id>')
@login_required(roles=['accountant'])
def print_salary_receipt(id):
    conn = get_db()
    salary = conn.execute("SELECT * FROM advanced_salaries WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('print_salary.html', salary=salary)

@app.route('/salaries/print/bonus/<int:id>')
@login_required(roles=['accountant'])
def print_bonus_receipt(id):
    conn = get_db()
    salary = conn.execute("SELECT * FROM advanced_salaries WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('print_bonus.html', salary=salary)

@app.route('/salaries/print/advance/<int:id>')
@login_required(roles=['accountant'])
def print_advance_receipt(id):
    conn = get_db()
    salary = conn.execute("SELECT * FROM advanced_salaries WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('print_advance.html', salary=salary)

@app.route('/salaries/print/employees_list')
@login_required(roles=['accountant'])
def print_employees_list():
    conn = get_db()
    employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    conn.close()
    return render_template('print_employees_list.html', employees=employees)

@app.route('/finance', methods=['GET', 'POST'])
@login_required(roles=['accountant'])
def finance():
    conn = get_db()
    if request.method == 'POST':
        try:
            trans_type = request.form.get('trans_type', 'out')
            amount = float(request.form['amount'])
            main_desc = request.form.get('description', '')
            notes = request.form.get('notes', '')
            description = f"{main_desc} - {notes}".strip(" -")
            expense_date = request.form['expense_date']
            person = request.form['person']
            
            category = 'إيراد' if trans_type == 'in' else ('عهدة' if trans_type == 'custody' else ('رواتب' if trans_type == 'salary' else 'مصروفات'))
            
            conn.execute("INSERT INTO expenses (description, amount, expense_date, category, payment_method, created_by) VALUES (?, ?, ?, ?, ?, ?)", 
                         (description, amount, expense_date, category, person, session['user_id']))
            conn.commit()
            log_activity("حركة مالية", f"تسجيل {category} بقيمة {amount} د.ل")
            flash("تم تسجيل الحركة المالية بنجاح", "success")
        except Exception as e:
            flash(f"حدث خطأ: {e}", "danger")
        return redirect(url_for('finance'))
    
    expenses = conn.execute("SELECT * FROM expenses ORDER BY id DESC").fetchall()
    total_in = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE category = 'إيراد'").fetchone()[0]
    total_out = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE category IN ('مصروفات', 'عهدة', 'رواتب', 'مواد بناء')").fetchone()[0]
    balance = total_in - total_out
    conn.close()
    return render_template('finance.html', expenses=expenses, total_in=total_in, total_out=total_out, balance=balance, today=date.today().isoformat())

@app.route('/delete_expense/<int:id>')
@login_required(roles=['accountant'])
def delete_expense(id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    log_activity("حذف حركة مالية", f"حذف السجل المالي رقم {id}")
    flash("تم الحذف بنجاح", "success")
    conn.close()
    return redirect(url_for('finance'))

@app.route('/items', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def items():
    conn = get_db()
    if request.method == 'POST':
        try:
            category = request.form.get('category', 'عام')
            prefix_map = {'المطبخ': 'KH', 'مواد بناء': 'BL', 'قطع غيار': 'SP', 'أدوات': 'TL', 'كهرباء': 'EL', 'سباكة': 'PL', 'سلامة': 'SF', 'مكتبية': 'OF', 'عام': 'GEN'}
            prefix = prefix_map.get(category, 'GEN')
            last_item = conn.execute("SELECT code FROM items WHERE code LIKE ? ORDER BY id DESC LIMIT 1", (prefix + '-%',)).fetchone()
            new_code = f"{prefix}-{int(last_item['code'].split('-')[1]) + 1:02d}" if last_item else f"{prefix}-01"
            conn.execute("INSERT INTO items (code, name, unit, min_qty, category) VALUES (?, ?, ?, ?, ?)", (new_code, request.form['name'], request.form['unit'], request.form.get('min_qty', 0), category))
            conn.commit()
            log_activity("إضافة مادة", f"إضافة صنف: {request.form['name']}")
            flash(f"تمت الإضافة بكود: {new_code}", "success")
        except Exception as e: flash(f"حدث خطأ: {e}", "danger")
        return redirect(url_for('items'))
    search_query = request.args.get('search', '')
    all_items = conn.execute("SELECT * FROM items WHERE name LIKE ? OR code LIKE ? ORDER BY category, code", ('%'+search_query+'%', '%'+search_query+'%')).fetchall() if search_query else conn.execute("SELECT * FROM items ORDER BY category, code").fetchall()
    conn.close()
    return render_template('items.html', items=all_items, search=search_query)

@app.route('/edit_item/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def edit_item(id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute("UPDATE items SET code=?, name=?, unit=?, min_qty=?, category=? WHERE id=?", (request.form['code'], request.form['name'], request.form['unit'], request.form['min_qty'], request.form['category'], id))
        conn.commit()
        log_activity("تعديل مادة", f"تعديل صنف رقم {id}")
        flash("تم التعديل بنجاح", "success")
        return redirect(url_for('items'))
    item = conn.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('edit_item.html', item=item)

@app.route('/delete_item/<int:id>')
@login_required(roles=['storekeeper'])
def delete_item(id):
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=?", (id,))
    conn.commit()
    log_activity("حذف مادة", f"حذف صنف رقم {id}")
    flash("تم الحذف بنجاح", "success")
    conn.close()
    return redirect(url_for('items'))

@app.route('/print_items')
@login_required(roles=['storekeeper'])
def print_items():
    category = request.args.get('category', 'الكل')
    conn = get_db()
    items = conn.execute("SELECT * FROM items ORDER BY category, code").fetchall() if category == 'الكل' else conn.execute("SELECT * FROM items WHERE category=? ORDER BY code", (category,)).fetchall()
    conn.close()
    return render_template('print_items.html', items=items, category=category)

@app.route('/purchase', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def purchase():
    conn = get_db()
    if request.method == 'POST':
        invoice_no = request.form.get('invoice_no', '').strip()
        num_val = get_next_sequence('PUR')
        voucher_no = f"EKIP-TK-{num_val:03d}"
        cur = conn.cursor()
        cur.execute("INSERT INTO purchase_vouchers (voucher_no, voucher_date, supplier, invoice_no, receiver_name, created_by) VALUES (?,?,?,?,?,?)", (voucher_no, request.form['voucher_date'], request.form['supplier'], invoice_no, request.form.get('receiver_name', ''), session['user_id']))
        vid = cur.lastrowid
        item_ids, qtys, prices = request.form.getlist('item_id[]'), request.form.getlist('qty[]'), request.form.getlist('price[]')
        total_amount = 0
        for i in range(len(item_ids)):
            if item_ids[i] and float(qtys[i]) > 0:
                cur.execute("INSERT INTO purchase_lines (voucher_id, item_id, qty, price) VALUES (?,?,?,?)", (vid, item_ids[i], qtys[i], prices[i]))
                cur.execute("INSERT INTO stock_movements (item_id, move_type, qty, move_date, ref_type, ref_id, created_by) VALUES (?, 'in', ?, ?, 'purchase', ?, ?)", (item_ids[i], qtys[i], request.form['voucher_date'], vid, session['user_id']))
                total_amount += float(qtys[i]) * float(prices[i])
        if total_amount > 0:
            cur.execute("INSERT INTO expenses (description, amount, expense_date, category, payment_method, created_by) VALUES (?, ?, ?, ?, ?, ?)", (f"شراء - {voucher_no}", total_amount, request.form['voucher_date'], 'مصروفات', request.form.get('payment_method', 'كاش'), session['user_id']))
        conn.commit()
        log_activity("إذن توريد", f"تسجيل إذن شراء رقم {voucher_no}")
        flash(f"تم التسجيل بنجاح. رقم الإذن: {voucher_no}", "success")
        return redirect(url_for('purchase'))
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    vouchers = conn.execute("SELECT * FROM purchase_vouchers ORDER BY id DESC LIMIT 10").fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM items").fetchall()
    conn.close()
    return render_template('purchase.html', items=items_list, vouchers=vouchers, today=date.today().isoformat(), categories=categories)

@app.route('/transfer_purchase_to_issue/<int:voucher_id>')
@login_required(roles=['storekeeper'])
def transfer_purchase_to_issue(voucher_id):
    conn = get_db()
    voucher = conn.execute("SELECT * FROM purchase_vouchers WHERE id=?", (voucher_id,)).fetchone()
    lines = conn.execute("SELECT i.name, pl.qty, pl.price FROM purchase_lines pl JOIN items i ON pl.item_id = i.id WHERE pl.voucher_id=?", (voucher_id,)).fetchall()
    conn.close()
    carried_items_list = [{'name': line['name'], 'qty': str(line['qty']), 'price': str(line['price'])} for line in lines]
    session['carried_items'] = {'items': carried_items_list, 'supplier': voucher['supplier'] or ''}
    flash(f"تم نقل البيانات إلى إذن الصرف", "success")
    return redirect(url_for('issue_order'))

@app.route('/delete_purchase/<int:voucher_id>')
@login_required(roles=['storekeeper'])
def delete_purchase(voucher_id):
    conn = get_db()
    conn.execute("DELETE FROM stock_movements WHERE ref_type='purchase' AND ref_id=?", (voucher_id,))
    conn.execute("DELETE FROM purchase_lines WHERE voucher_id=?", (voucher_id,))
    conn.execute("DELETE FROM purchase_vouchers WHERE id=?", (voucher_id,))
    conn.commit()
    log_activity("حذف إذن شراء", f"حذف إذن شراء رقم {voucher_id}")
    conn.close()
    flash("تم حذف الطلب بنجاح", "success")
    return redirect(url_for('purchase'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
