from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from functools import wraps
from datetime import date, datetime
import random

app = Flask(__name__)
app.secret_key = "secret-key-123"

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

init_db()

conn = get_db()
conn.execute("""
CREATE TABLE IF NOT EXISTS user_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    user_fullname TEXT,
    action TEXT,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

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

if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    conn.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)", 
                 ('admin', generate_password_hash('admin123'), 'مدير النظام', 'admin'))
    conn.commit()

if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
    initial_employees = [
        ("ابراهيم محمد ابراهيم", 1500), ("احمد صلاح موسي", 3000), ("اسماعيل يونس محمد ادم", 2500),
        ("اسماعيل ادم هارون", 4500), ("اشرف عبد العالي الشلماني", 3000), ("السيد خالد عبدالستار", 3340),
        ("السيد فتحي سيد محمد", 2000), ("الهادي حسين محمد", 1500), ("برعي ابوبكر داوود", 1500),
        ("بشر محمد بشرساكن", 4785), ("جاد كريم عبد الوهاب", 4000), ("جلال احمد المسمار", 3000),
        ("جميل محمد ابراهيم", 2000), ("حسان محمد حسان", 1500), ("حسن حسان محمد", 1500),
        ("حمدي محمد سعيد", 4500), ("حمزة محمد العرفي", 1500), ("حنين عبد المنعم خالد", 2500),
        ("خالد آدم آدم", 4500), ("رجب محمد حسين", 4500), ("سليمان لازم جير الله", 2645),
        ("سيف الاسلام المبروك براهيم", 1935), ("ضيمن فيصل السيد", 4500), ("عادل ابوبكر آدم", 2000),
        ("عادل صلاح السيد", 5500), ("عامر سالم محمد ابوبكر", 4000), ("عبد الحليم عيسي", 4500),
        ("عبد العزيز القوارشة", 6775), ("عبد الكريم شيخ الدين محمد", 3500), ("عبد المنعم خميس ابوبكر", 1500),
        ("عطية صالح عطية الحمر", 2000), ("علاء الدين هارون", 2500), ("علاء السيد دياب", 3340),
        ("علي امبارك علي", 3000), ("علي محمد حسين موسي", 3000), ("عمر ابراهيم محمد", 2500),
        ("فتح الله ضو عبد الله", 3500), ("فرج المنصور فرج", 3000), ("محمد ابراهيم حسن", 2500),
        ("محمد ابراهیم آدم", 2000), ("محمد احمد جودات", 1500), ("محمد البركي", 1935),
        ("محمد خضر طافور", 4500), ("محمد عبدالله الحاج", 4500), ("محمد عثمان بخيث", 1500),
        ("محمد عمر حمدي", 2670), ("محمود محمد عبد الحميد", 4000), ("مصطفي عمر البوسيفي", 5645),
        ("مندر ابراهيم", 3970), ("مهند اسماعيل محمد", 1500)
    ]
    for emp in initial_employees:
        conn.execute("INSERT INTO employees (name, default_salary) VALUES (?, ?)", emp)
    conn.commit()

conn.close()

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

@app.route('/salaries', methods=['GET', 'POST'])
@login_required(roles=['accountant'])
def salaries():
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_employee':
            name = request.form.get('name')
            sal_str = request.form.get('default_salary', '0')
            salary = float(sal_str) if sal_str else 0.0
            conn.execute("INSERT INTO employees (name, default_salary) VALUES (?, ?)", (name, salary))
            conn.commit()
            log_activity("إضافة موظف", f"إضافة الموظف: {name}")
            flash("تم إضافة الموظف بنجاح", "success")
        elif action == 'update_employee':
            emp_id = request.form.get('emp_id')
            name = request.form.get('name')
            sal_str = request.form.get('default_salary', '0')
            salary = float(sal_str) if sal_str else 0.0
            conn.execute("UPDATE employees SET name=?, default_salary=? WHERE id=?", (name, salary, emp_id))
            conn.commit()
            log_activity("تعديل موظف", f"تعديل الموظف رقم {emp_id}")
            flash("تم تعديل بيانات الموظف بنجاح", "success")
        elif action == 'delete_employee':
            emp_id = request.form.get('emp_id')
            conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            conn.commit()
            log_activity("حذف موظف", f"حذف الموظف رقم {emp_id}")
            flash("تم حذف الموظف بنجاح", "success")
        elif action == 'pay_salary':
            emp_id = request.form.get('emp_id')
            month = request.form.get('salary_month')
            base_amount = float(request.form.get('amount') or 0)
            status = request.form.get('status', 'منتظم')
            deduction = float(request.form.get('deduction') or 0)
            deduction_reason = request.form.get('deduction_reason', '')
            pay_date = request.form.get('pay_date')
            final_amount = max(0, base_amount - deduction)
            
            emp = conn.execute("SELECT name FROM employees WHERE id=?", (emp_id,)).fetchone()
            if emp:
                emp_name = emp['name']
                cur = conn.cursor()
                cur.execute("INSERT INTO salary_payments (employee_id, employee_name, month, amount, status, deduction, deduction_reason, pay_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (emp_id, emp_name, month, final_amount, status, deduction, deduction_reason, pay_date, session['user_id']))
                pay_id = cur.lastrowid
                
                desc_text = f"صرف راتب شهر {month} للموظف: {emp_name}"
                if deduction > 0:
                    desc_text += f" - خصم: {int(deduction)} ({deduction_reason})"
                    
                conn.execute("INSERT INTO expenses (description, amount, expense_date, category, payment_method, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                             (desc_text, final_amount, pay_date, 'رواتب', emp_name, session['user_id']))
                conn.commit()
                log_activity("صرف راتب", f"صرف راتب شهر {month} للموظف {emp_name}")
                flash(f"تم صرف راتب الموظف {emp_name} بنجاح", "success")
                conn.close()
                return redirect(url_for('print_salary_voucher', payment_id=pay_id))

        return redirect(url_for('salaries'))
    
    employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    payments = conn.execute("SELECT * FROM salary_payments ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('salaries.html', employees=employees, payments=payments, today=date.today().isoformat())

@app.route('/delete_salary_payment/<int:id>')
@login_required(roles=['accountant'])
def delete_salary_payment(id):
    conn = get_db()
    conn.execute("DELETE FROM salary_payments WHERE id=?", (id,))
    conn.commit()
    log_activity("حذف إيصال راتب", f"حذف سجل الراتب رقم {id}")
    flash("تم حذف سجل الراتب بنجاح", "success")
    conn.close()
    return redirect(url_for('salaries'))

@app.route('/print_salary_voucher/<int:payment_id>')
@login_required(roles=['accountant'])
def print_salary_voucher(payment_id):
    conn = get_db()
    payment = conn.execute("SELECT * FROM salary_payments WHERE id=?", (payment_id,)).fetchone()
    conn.close()
    return render_template('print_salary.html', payment=payment)

@app.route('/print_all_employees')
@login_required(roles=['accountant'])
def print_all_employees():
    conn = get_db()
    employees = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    conn.close()
    return render_template('print_employees.html', employees=employees)

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
        last_voucher = conn.execute("SELECT voucher_no FROM purchase_vouchers ORDER BY id DESC LIMIT 1").fetchone()
        voucher_no = f"PUR-{int(last_voucher['voucher_no'].split('-')[1]) + 1:03d}" if last_voucher else "PUR-001"
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

@app.route('/print_purchase/<int:voucher_id>')
@login_required(roles=['storekeeper'])
def print_purchase(voucher_id):
    conn = get_db()
    voucher = conn.execute("SELECT * FROM purchase_vouchers WHERE id=?", (voucher_id,)).fetchone()
    lines = conn.execute("SELECT i.name, i.unit, pl.qty, pl.price FROM purchase_lines pl JOIN items i ON pl.item_id = i.id WHERE pl.voucher_id=?", (voucher_id,)).fetchall()
    conn.close()
    return render_template('print_purchase.html', voucher=voucher, lines=lines)

@app.route('/purchase_order', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def purchase_order():
    conn = get_db()
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    if request.method == 'POST':
        item_names, qtys, prices = request.form.getlist('item_name[]'), request.form.getlist('qty[]'), request.form.getlist('price[]')
        carried_items_list = [{'name': item_names[i], 'qty': qtys[i], 'price': prices[i]} for i in range(len(item_names)) if item_names[i]]
        session['carried_items'] = {'items': carried_items_list, 'supplier': request.form.get('supplier', '')}
        flash("تم نقل البيانات بنجاح", "success")
        return redirect(url_for('issue_order'))
    return render_template('purchase_order.html', items=items_list, today=date.today().isoformat(), doc_title="نموذج إذن شراء / طلب توريد", is_purchase=True)

@app.route('/issue_order', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def issue_order():
    conn = get_db()
    if request.method == 'POST':
        voucher_no = f"ISS-{date.today().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        department = request.form.get('supplier', 'عام')
        cur = conn.cursor()
        cur.execute("INSERT INTO issue_vouchers (voucher_no, voucher_date, department, created_by) VALUES (?,?,?,?)", (voucher_no, request.form['voucher_date'], department, session['user_id']))
        vid = cur.lastrowid
        item_names, qtys = request.form.getlist('item_name[]'), request.form.getlist('qty[]')
        for i in range(len(item_names)):
            if item_names[i] and float(qtys[i]) > 0:
                item = cur.execute("SELECT id FROM items WHERE name=?", (item_names[i],)).fetchone()
                item_id = item['id'] if item else cur.execute("INSERT INTO items (code, name, unit, category) VALUES (?, ?, ?, ?)", (f"GEN-{random.randint(1000,9999)}", item_names[i], 'حبة', 'عام')).lastrowid
                cur.execute("INSERT INTO issue_lines (voucher_id, item_id, qty) VALUES (?,?,?)", (vid, item_id, qtys[i]))
                cur.execute("INSERT INTO stock_movements (item_id, move_type, qty, move_date, ref_type, ref_id, created_by) VALUES (?, 'out', ?, ?, 'issue', ?, ?)", (item_id, qtys[i], request.form['voucher_date'], vid, session['user_id']))
        conn.commit()
        log_activity("إذن صرف", f"تسجيل أمر صرف مواد رقم {voucher_no}")
        conn.close()
        flash("تم تسجيل أمر الصرف بنجاح", "success")
        return redirect(url_for('issue'))
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    return render_template('purchase_order.html', items=items_list, today=date.today().isoformat(), doc_title="أمر صرف مواد", is_purchase=False, carried_data=session.pop('carried_items', None))

@app.route('/issue', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def issue():
    conn = get_db()
    if request.method == 'POST':
        voucher_no = f"ISS-{date.today().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        department = request.form.get('supplier', 'عام')
        cur = conn.cursor()
        cur.execute("INSERT INTO issue_vouchers (voucher_no, voucher_date, department, created_by) VALUES (?,?,?,?)", (voucher_no, request.form['voucher_date'], department, session['user_id']))
        vid = cur.lastrowid
        item_names, qtys = request.form.getlist('item_name[]'), request.form.getlist('qty[]')
        for i in range(len(item_names)):
            if item_names[i] and float(qtys[i]) > 0:
                item = cur.execute("SELECT id FROM items WHERE name=?", (item_names[i],)).fetchone()
                item_id = item['id'] if item else cur.execute("INSERT INTO items (code, name, unit, category) VALUES (?, ?, ?, ?)", (f"GEN-{random.randint(1000,9999)}", item_names[i], 'حبة', 'عام')).lastrowid
                cur.execute("INSERT INTO issue_lines (voucher_id, item_id, qty) VALUES (?,?,?)", (vid, item_id, qtys[i]))
                cur.execute("INSERT INTO stock_movements (item_id, move_type, qty, move_date, ref_type, ref_id, created_by) VALUES (?, 'out', ?, ?, 'issue', ?, ?)", (item_id, qtys[i], request.form['voucher_date'], vid, session['user_id']))
        conn.commit()
        log_activity("إذن صرف", f"تسجيل إذن صرف رقم {voucher_no}")
        conn.close()
        flash("تم تسجيل إذن الصرف بنجاح", "success")
        return redirect(url_for('issue'))
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    vouchers = conn.execute("SELECT * FROM issue_vouchers ORDER BY id DESC LIMIT 10").fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM items").fetchall()
    conn.close()
    return render_template('issue.html', items=items_list, vouchers=vouchers, today=date.today().isoformat(), categories=categories)

@app.route('/delete_issue/<int:voucher_id>')
@login_required(roles=['storekeeper'])
def delete_issue(voucher_id):
    conn = get_db()
    conn.execute("DELETE FROM stock_movements WHERE ref_type='issue' AND ref_id=?", (voucher_id,))
    conn.execute("DELETE FROM issue_lines WHERE voucher_id=?", (voucher_id,))
    conn.execute("DELETE FROM issue_vouchers WHERE id=?", (voucher_id,))
    conn.commit()
    log_activity("حذف إذن صرف", f"حذف إذن صرف رقم {voucher_id}")
    conn.close()
    flash("تم الحذف وإرجاع الكميات بنجاح", "success")
    return redirect(url_for('issue'))

@app.route('/print_issue/<int:voucher_id>')
@login_required(roles=['storekeeper'])
def print_issue(voucher_id):
    conn = get_db()
    voucher = conn.execute("SELECT * FROM issue_vouchers WHERE id=?", (voucher_id,)).fetchone()
    lines = conn.execute("SELECT i.name, i.unit, il.qty FROM issue_lines il JOIN items i ON il.item_id = i.id WHERE il.voucher_id=?", (voucher_id,)).fetchall()
    conn.close()
    return render_template('print_issue.html', voucher=voucher, lines=lines)

@app.route('/handover', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def handover():
    conn = get_db()
    items = conn.execute('SELECT * FROM items ORDER BY name').fetchall()
    conn.close()
    return render_template('handover.html', items=items, today=date.today().isoformat())

@app.route('/inventory')
@login_required(roles=['storekeeper'])
def inventory():
    to_date = request.args.get('to_date', date.today().isoformat())
    conn = get_db()
    items = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    data = []
    for item in items:
        in_qty = conn.execute("SELECT COALESCE(SUM(qty), 0) FROM stock_movements WHERE item_id = ? AND move_type = 'in' AND move_date <= ?", (item['id'], to_date)).fetchone()[0]
        out_qty = conn.execute("SELECT COALESCE(SUM(qty), 0) FROM stock_movements WHERE item_id = ? AND move_type = 'out' AND move_date <= ?", (item['id'], to_date)).fetchone()[0]
        data.append({'code': item['code'], 'name': item['name'], 'unit': item['unit'], 'category': item['category'], 'in_qty': in_qty, 'out_qty': out_qty, 'balance': in_qty - out_qty})
    conn.close()
    return render_template('inventory.html', inventory_data=data, to_date=to_date)

@app.route('/equipment_out', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def equipment_out():
    conn = get_db()
    if request.method == 'POST':
        voucher_no = f"EQ-OUT-{date.today().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        cur = conn.cursor()
        cur.execute("INSERT INTO equipment_vouchers (voucher_no, type, worker_name, voucher_date, notes, created_by) VALUES (?, 'out', ?, ?, ?, ?)", (voucher_no, request.form['worker'], request.form['date'], request.form['notes'], session['user_id']))
        vid = cur.lastrowid
        item_ids, qtys = request.form.getlist('item_id[]'), request.form.getlist('qty[]')
        for i in range(len(item_ids)):
            if item_ids[i] and float(qtys[i]) > 0:
                cur.execute("INSERT INTO equipment_lines (voucher_id, item_id, qty) VALUES (?,?,?)", (vid, item_ids[i], qtys[i]))
                cur.execute("INSERT INTO stock_movements (item_id, move_type, qty, move_date, ref_type, ref_id, created_by) VALUES (?, 'out', ?, ?, 'equipment', ?, ?)", (item_ids[i], qtys[i], request.form['date'], vid, session['user_id']))
        conn.commit()
        log_activity("تسليم عهدة", f"تسليم عهدة للموظف {request.form['worker']}")
        conn.close()
        flash("تم تسليم العهدة بنجاح", "success")
        return redirect(url_for('equipment_out'))
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    vouchers = conn.execute("SELECT * FROM equipment_vouchers WHERE type='out' ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('equipment_form.html', title="إدارة العهد", action="تسليم", items=items_list, vouchers=vouchers, today=date.today().isoformat(), type='out')

@app.route('/equipment_in', methods=['GET', 'POST'])
@login_required(roles=['storekeeper'])
def equipment_in():
    conn = get_db()
    if request.method == 'POST':
        voucher_no = f"EQ-IN-{date.today().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        cur = conn.cursor()
        cur.execute("INSERT INTO equipment_vouchers (voucher_no, type, worker_name, voucher_date, notes, created_by) VALUES (?, 'in', ?, ?, ?, ?)", (voucher_no, request.form['worker'], request.form['date'], request.form['notes'], session['user_id']))
        vid = cur.lastrowid
        item_ids, qtys, conds = request.form.getlist('item_id[]'), request.form.getlist('qty[]'), request.form.getlist('condition[]')
        for i in range(len(item_ids)):
            if item_ids[i] and float(qtys[i]) > 0:
                cur.execute("INSERT INTO equipment_lines (voucher_id, item_id, qty, condition) VALUES (?,?,?,?)", (vid, item_ids[i], qtys[i], conds[i]))
                cur.execute("INSERT INTO stock_movements (item_id, move_type, qty, move_date, ref_type, ref_id, created_by) VALUES (?, 'in', ?, ?, 'equipment', ?, ?)", (item_ids[i], qtys[i], request.form['date'], vid, session['user_id']))
        conn.commit()
        log_activity("استلام عهدة", f"استلام عهدة من الموظف {request.form['worker']}")
        conn.close()
        flash("تم استلام العهدة بنجاح", "success")
        return redirect(url_for('equipment_in'))
    items_list = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    vouchers = conn.execute("SELECT * FROM equipment_vouchers WHERE type='in' ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('equipment_form.html', title="إدارة العهد", action="استلام", items=items_list, vouchers=vouchers, today=date.today().isoformat(), type='in')

@app.route('/archive')
@login_required(roles=['storekeeper'])
def archive():
    conn = get_db()
    movements = conn.execute("SELECT m.created_at, m.move_date, m.move_type, i.code, i.name, m.qty, u.full_name, m.ref_type FROM stock_movements m JOIN items i ON m.item_id = i.id LEFT JOIN users u ON m.created_by = u.id ORDER BY m.id DESC").fetchall()
    conn.close()
    return render_template('archive.html', movements=movements)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)