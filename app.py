from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from database import get_db, init_db
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'library_mgmt_secret_2024'

init_db()

# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated

# ── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND is_active=1",
            (username, password)
        ).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['is_admin'] = bool(user['is_admin'])
            return redirect(url_for('home'))
        else:
            flash('Invalid User ID or Password. Please try again.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')

# ── Home ──────────────────────────────────────────────────────────────────────

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

# ── Transactions ──────────────────────────────────────────────────────────────

@app.route('/transactions')
@login_required
def transactions():
    return render_template('transactions.html')

# Book Available (search)
@app.route('/book-available', methods=['GET', 'POST'])
@login_required
def book_available():
    db = get_db()
    book_names = [r['name'] for r in db.execute("SELECT DISTINCT name FROM products ORDER BY name").fetchall()]
    authors = [r['author'] for r in db.execute("SELECT DISTINCT author FROM products ORDER BY author").fetchall()]

    results = []
    searched = False
    book_name = ''
    author = ''

    if request.method == 'POST':
        book_name = request.form.get('book_name', '').strip()
        author = request.form.get('author', '').strip()
        if not book_name and not author:
            flash('Please fill in at least one field - Book Name or Author - before submitting.', 'error')
        else:
            searched = True
            query = "SELECT * FROM products WHERE 1=1"
            params = []
            if book_name:
                query += " AND name LIKE ?"
                params.append(f'%{book_name}%')
            if author:
                query += " AND author LIKE ?"
                params.append(f'%{author}%')
            results = db.execute(query, params).fetchall()
    db.close()
    return render_template('book_available.html',
                           book_names=book_names, authors=authors,
                           results=results, searched=searched,
                           book_name=book_name, author=author)

# Book Issue
@app.route('/book-issue', methods=['GET', 'POST'])
@login_required
def book_issue():
    db = get_db()
    book_names = [r['name'] for r in db.execute("SELECT DISTINCT name FROM products WHERE status='Available' ORDER BY name").fetchall()]

    if request.method == 'POST':
        book_name = request.form.get('book_name', '').strip()
        author = request.form.get('author', '').strip()
        issue_date = request.form.get('issue_date', '').strip()
        return_date = request.form.get('return_date', '').strip()
        remarks = request.form.get('remarks', '').strip()

        errors = []
        if not book_name:
            errors.append('Name of book is required.')
        if not issue_date:
            errors.append('Issue Date is required.')
        if not return_date:
            errors.append('Return Date is required.')

        if not errors:
            try:
                id_obj = datetime.strptime(issue_date, '%Y-%m-%d').date()
                rd_obj = datetime.strptime(return_date, '%Y-%m-%d').date()
                today = datetime.now().date()
                if id_obj < today:
                    errors.append('Issue Date cannot be lesser than today.')
                max_return = id_obj + timedelta(days=15)
                if rd_obj > max_return:
                    errors.append('Return Date cannot be greater than 15 days from Issue Date.')
            except ValueError:
                errors.append('Invalid date format.')

        if not errors:
            product = db.execute(
                "SELECT * FROM products WHERE name=? AND status='Available' LIMIT 1",
                (book_name,)
            ).fetchone()
            if not product:
                errors.append('Selected book is not available for issue.')

        if errors:
            for e in errors:
                flash(e, 'error')
            db.close()
            return render_template('book_issue.html', book_names=book_names,
                                   form=request.form)

        # Issue the book
        db.execute(
            "INSERT INTO issues (serial_no, product_name, author, membership_id, issue_date, return_date, remarks, status) VALUES (?,?,?,?,?,?,?,?)",
            (product['serial_no'], book_name, product['author'], 'WALK-IN', issue_date, return_date, remarks, 'Active')
        )
        db.execute("UPDATE products SET status='Issued' WHERE serial_no=?", (product['serial_no'],))
        db.commit()
        db.close()
        return redirect(url_for('confirmation'))

    db.close()
    return render_template('book_issue.html', book_names=book_names, form={})

# AJAX: get author for a book name
@app.route('/api/book-author')
@login_required
def api_book_author():
    name = request.args.get('name', '')
    db = get_db()
    product = db.execute("SELECT author FROM products WHERE name=? AND status='Available' LIMIT 1", (name,)).fetchone()
    db.close()
    return jsonify({'author': product['author'] if product else ''})

# Return Book
@app.route('/return-book', methods=['GET', 'POST'])
@login_required
def return_book():
    db = get_db()
    issued_books = [r['product_name'] for r in db.execute(
        "SELECT DISTINCT product_name FROM issues WHERE status='Active' ORDER BY product_name"
    ).fetchall()]

    if request.method == 'POST':
        book_name = request.form.get('book_name', '').strip()
        serial_no = request.form.get('serial_no', '').strip()
        return_date = request.form.get('return_date', '').strip()
        remarks = request.form.get('remarks', '').strip()

        errors = []
        if not book_name:
            errors.append('Name of Book is required.')
        if not serial_no:
            errors.append('Serial No is a mandatory field.')
        if not return_date:
            errors.append('Return Date is required.')

        if not errors:
            issue = db.execute(
                "SELECT * FROM issues WHERE product_name=? AND serial_no=? AND status='Active'",
                (book_name, serial_no)
            ).fetchone()
            if not issue:
                errors.append('No active issue found for this book and serial number.')

        if errors:
            for e in errors:
                flash(e, 'error')
            db.close()
            return render_template('return_book.html', issued_books=issued_books, form=request.form)

        # Calculate fine: Rs 10 per day past return_date
        original_return = datetime.strptime(issue['return_date'], '%Y-%m-%d').date()
        actual_return = datetime.strptime(return_date, '%Y-%m-%d').date()
        fine = max(0, (actual_return - original_return).days) * 10

        db.execute(
            "UPDATE issues SET actual_return_date=?, remarks=?, fine_calculated=?, status='PendingFine' WHERE id=?",
            (return_date, remarks, fine, issue['id'])
        )
        db.commit()
        db.close()
        # Always go to Pay Fine page after Return Book (per instructions)
        return redirect(url_for('pay_fine', issue_id=issue['id']))

    db.close()
    return render_template('return_book.html', issued_books=issued_books, form={})

# AJAX: get serial numbers and author/issue_date for issued book
@app.route('/api/issued-book-details')
@login_required
def api_issued_book_details():
    name = request.args.get('name', '')
    db = get_db()
    issues = db.execute(
        "SELECT serial_no, author, issue_date, return_date FROM issues WHERE product_name=? AND status='Active'",
        (name,)
    ).fetchall()
    db.close()
    return jsonify([dict(i) for i in issues])

# Pay Fine
@app.route('/pay-fine', methods=['GET', 'POST'])
@login_required
def pay_fine():
    issue_id = request.args.get('issue_id') or request.form.get('issue_id')

    if request.method == 'POST':
        fine_paid = 'fine_paid' in request.form
        remarks = request.form.get('remarks', '').strip()

        db = get_db()
        issue = db.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()

        if not issue:
            flash('Issue record not found.', 'error')
            db.close()
            return redirect(url_for('transactions'))

        fine = issue['fine_calculated']
        if fine > 0 and not fine_paid:
            flash('For a pending fine, the Fine Paid checkbox must be selected before completing the return.', 'error')
            db.close()
            return render_template('pay_fine.html', issue=issue)

        db.execute(
            "UPDATE issues SET fine_paid=1, remarks=?, status='Returned' WHERE id=?",
            (remarks, issue_id)
        )
        db.execute("UPDATE products SET status='Available' WHERE serial_no=?", (issue['serial_no'],))
        db.commit()
        db.close()
        return redirect(url_for('confirmation'))

    db = get_db()
    issue = db.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    db.close()

    if not issue:
        flash('Issue record not found.', 'error')
        return redirect(url_for('transactions'))

    return render_template('pay_fine.html', issue=issue)

# ── Reports ───────────────────────────────────────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/master-list-of-books')
@login_required
def report_books():
    db = get_db()
    items = db.execute("SELECT * FROM products WHERE type='Book' ORDER BY serial_no").fetchall()
    db.close()
    return render_template('report_books.html', items=items)

@app.route('/reports/master-list-of-movies')
@login_required
def report_movies():
    db = get_db()
    items = db.execute("SELECT * FROM products WHERE type='Movie' ORDER BY serial_no").fetchall()
    db.close()
    return render_template('report_movies.html', items=items)

@app.route('/reports/master-list-of-memberships')
@login_required
def report_memberships():
    db = get_db()
    members = db.execute("SELECT * FROM memberships ORDER BY membership_id").fetchall()
    db.close()
    return render_template('report_memberships.html', members=members)

@app.route('/reports/active-issues')
@login_required
def report_active_issues():
    db = get_db()
    issues = db.execute("SELECT * FROM issues WHERE status='Active' ORDER BY issue_date DESC").fetchall()
    db.close()
    return render_template('report_active_issues.html', issues=issues)

@app.route('/reports/overdue-returns')
@login_required
def report_overdue():
    today = str(datetime.now().date())
    db = get_db()
    issues = db.execute(
        "SELECT * FROM issues WHERE status='Active' AND return_date < ? ORDER BY return_date ASC",
        (today,)
    ).fetchall()
    db.close()
    return render_template('report_overdue.html', issues=issues, today=today)

@app.route('/reports/issue-requests')
@login_required
def report_issue_requests():
    db = get_db()
    requests_list = db.execute("SELECT * FROM issue_requests ORDER BY requested_date DESC").fetchall()
    db.close()
    return render_template('report_issue_requests.html', requests_list=requests_list)

# ── Maintenance (Admin only) ──────────────────────────────────────────────────

@app.route('/maintenance')
@admin_required
def maintenance():
    return render_template('maintenance.html')

# Add Membership
@app.route('/maintenance/add-membership', methods=['GET', 'POST'])
@admin_required
def add_membership():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        contact_name = request.form.get('contact_name', '').strip()
        contact_address = request.form.get('contact_address', '').strip()
        aadhar_no = request.form.get('aadhar_no', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        membership_type = request.form.get('membership_type', 'Six Months')

        errors = []
        if not first_name: errors.append('First Name is required.')
        if not last_name: errors.append('Last Name is required.')
        if not contact_name: errors.append('Contact Name is required.')
        if not contact_address: errors.append('Contact Address is required.')
        if not aadhar_no: errors.append('Aadhaar Card No is required.')
        if not start_date: errors.append('Start Date is required.')
        if not end_date: errors.append('End Date is required.')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('add_membership.html', form=request.form)

        db = get_db()
        count = db.execute("SELECT COUNT(*) as c FROM memberships").fetchone()['c']
        mem_id = f"MEM{str(count + 1).zfill(6)}"
        try:
            db.execute(
                "INSERT INTO memberships (membership_id, first_name, last_name, contact_name, contact_address, aadhar_no, start_date, end_date, membership_type, status, amount_pending) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (mem_id, first_name, last_name, contact_name, contact_address, aadhar_no, start_date, end_date, membership_type, 'Active', 0)
            )
            db.commit()
            db.close()
            return redirect(url_for('confirmation'))
        except Exception as e:
            db.close()
            flash(f'Error saving membership: {str(e)}', 'error')

    return render_template('add_membership.html', form={})

# Update Membership
@app.route('/maintenance/update-membership', methods=['GET', 'POST'])
@admin_required
def update_membership():
    member = None
    form = {}

    if request.method == 'POST':
        action = request.form.get('action', 'fetch')
        mem_num = request.form.get('membership_number', '').strip()

        if action == 'fetch':
            db = get_db()
            member = db.execute("SELECT * FROM memberships WHERE membership_id=?", (mem_num,)).fetchone()
            db.close()
            if not member:
                flash('Membership Number not found.', 'error')
            form = request.form

        elif action == 'update':
            membership_extn = request.form.get('membership_extn', 'Six Months')
            membership_remove = request.form.get('membership_remove', '')

            db = get_db()
            member = db.execute("SELECT * FROM memberships WHERE membership_id=?", (mem_num,)).fetchone()
            if not member:
                flash('Membership Number not found.', 'error')
                db.close()
                return render_template('update_membership.html', member=None, form=request.form)

            if membership_remove == 'yes':
                db.execute("UPDATE memberships SET status='Inactive' WHERE membership_id=?", (mem_num,))
            else:
                # Extend end date from current end date
                try:
                    end = datetime.strptime(member['end_date'], '%Y-%m-%d').date()
                    if membership_extn == 'Six Months':
                        end = end + timedelta(days=183)
                    elif membership_extn == 'One Year':
                        end = end.replace(year=end.year + 1)
                    elif membership_extn == 'Two Years':
                        end = end.replace(year=end.year + 2)
                    db.execute("UPDATE memberships SET end_date=?, membership_type=? WHERE membership_id=?",
                               (str(end), membership_extn, mem_num))
                except:
                    flash('Error updating end date.', 'error')
                    db.close()
                    return render_template('update_membership.html', member=member, form=request.form)

            db.commit()
            db.close()
            return redirect(url_for('confirmation'))

    return render_template('update_membership.html', member=member, form=form)

# Add Book/Movie
@app.route('/maintenance/add-book', methods=['GET', 'POST'])
@admin_required
def add_book():
    if request.method == 'POST':
        item_type = request.form.get('item_type', 'Book')
        name = request.form.get('name', '').strip()
        procurement_date = request.form.get('procurement_date', '').strip()
        quantity = request.form.get('quantity', '1').strip()

        errors = []
        if not name: errors.append('Book/Movie Name is required.')
        if not procurement_date: errors.append('Date of Procurement is required.')
        if not quantity: errors.append('Quantity/Copies is required.')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('add_book.html', form=request.form)

        try:
            qty = int(quantity)
        except:
            flash('Quantity must be a number.', 'error')
            return render_template('add_book.html', form=request.form)

        db = get_db()
        try:
            for i in range(qty):
                count = db.execute("SELECT COUNT(*) as c FROM products WHERE type=?", (item_type,)).fetchone()['c']
                type_char = 'B' if item_type == 'Book' else 'M'
                serial = f"NEW({type_char}){str(count + 1).zfill(6)}"
                db.execute(
                    "INSERT INTO products (serial_no, name, type, status, procurement_date) VALUES (?,?,?,?,?)",
                    (serial, name, item_type, 'Available', procurement_date)
                )
            db.commit()
            db.close()
            return redirect(url_for('confirmation'))
        except Exception as e:
            db.close()
            flash(f'Error: {str(e)}', 'error')

    return render_template('add_book.html', form={})

# Update Book/Movie
@app.route('/maintenance/update-book', methods=['GET', 'POST'])
@admin_required
def update_book():
    item = None
    form = {}

    if request.method == 'POST':
        action = request.form.get('action', 'fetch')
        item_type = request.form.get('item_type', 'Book')
        name = request.form.get('name', '').strip()
        serial_no = request.form.get('serial_no', '').strip()

        if action == 'fetch':
            db = get_db()
            q = "SELECT * FROM products WHERE type=?"
            params = [item_type]
            if name:
                q += " AND name LIKE ?"
                params.append(f'%{name}%')
            if serial_no:
                q += " AND serial_no=?"
                params.append(serial_no)
            item = db.execute(q + " LIMIT 1", params).fetchone()
            db.close()
            if not item:
                flash('No matching item found.', 'error')
            form = request.form

        elif action == 'update':
            status = request.form.get('status', '').strip()
            date = request.form.get('date', '').strip()

            errors = []
            if not serial_no: errors.append('Serial No is required.')
            if not status: errors.append('Status is required.')
            if not date: errors.append('Date is required.')

            if errors:
                for e in errors: flash(e, 'error')
                return render_template('update_book.html', item=None, form=request.form)

            db = get_db()
            db.execute("UPDATE products SET status=?, procurement_date=? WHERE serial_no=?", (status, date, serial_no))
            db.commit()
            db.close()
            return redirect(url_for('confirmation'))

    db = get_db()
    book_names = [r['name'] for r in db.execute("SELECT DISTINCT name FROM products ORDER BY name").fetchall()]
    db.close()
    return render_template('update_book.html', item=item, form=form, book_names=book_names)

# User Management
@app.route('/maintenance/user-management', methods=['GET', 'POST'])
@admin_required
def user_management():
    db = get_db()
    users_list = db.execute("SELECT * FROM users ORDER BY name").fetchall()

    if request.method == 'POST':
        user_type = request.form.get('user_type', 'new')
        name = request.form.get('name', '').strip()
        is_active = 'is_active' in request.form
        is_admin = 'is_admin' in request.form

        if not name:
            flash('Name is required.', 'error')
            db.close()
            return render_template('user_management.html', users_list=users_list, form=request.form)

        if user_type == 'new':
            username = name.lower().replace(' ', '_')
            try:
                db.execute(
                    "INSERT INTO users (username, password, name, is_admin, is_active) VALUES (?,?,?,?,?)",
                    (username, username, name, 1 if is_admin else 0, 1 if is_active else 0)
                )
                db.commit()
            except:
                flash('A user with that name/username already exists.', 'error')
                db.close()
                return render_template('user_management.html', users_list=users_list, form=request.form)
        else:
            username = request.form.get('existing_username', '').strip()
            if not username:
                flash('Please select an existing user.', 'error')
                db.close()
                return render_template('user_management.html', users_list=users_list, form=request.form)
            db.execute(
                "UPDATE users SET name=?, is_admin=?, is_active=? WHERE username=?",
                (name, 1 if is_admin else 0, 1 if is_active else 0, username)
            )
            db.commit()

        db.close()
        return redirect(url_for('confirmation'))

    db.close()
    return render_template('user_management.html', users_list=users_list, form={})

# ── Misc ──────────────────────────────────────────────────────────────────────

@app.route('/confirmation')
@login_required
def confirmation():
    return render_template('confirmation.html')

@app.route('/cancel')
@login_required
def cancel():
    return render_template('cancel.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
