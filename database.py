import sqlite3
import os
from datetime import datetime, timedelta

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'library.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    # Users table (for login - admin and user)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )''')

    # Products table (Books and Movies)
    # Categories: Science, Economics, Fiction, Children, Personal Development
    # Code format: SC(B/M)000001 etc.
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        author TEXT,
        category TEXT,
        type TEXT DEFAULT 'Book',
        status TEXT DEFAULT 'Available',
        cost REAL DEFAULT 0,
        procurement_date TEXT
    )''')

    # Memberships table
    c.execute('''CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_id TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        contact_name TEXT,
        contact_address TEXT,
        aadhar_no TEXT,
        start_date TEXT,
        end_date TEXT,
        membership_type TEXT DEFAULT 'Six Months',
        status TEXT DEFAULT 'Active',
        amount_pending REAL DEFAULT 0
    )''')

    # Issues table (Book Issue / Return / Pay Fine)
    c.execute('''CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_no TEXT NOT NULL,
        product_name TEXT NOT NULL,
        author TEXT,
        membership_id TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        return_date TEXT NOT NULL,
        actual_return_date TEXT,
        remarks TEXT,
        fine_calculated REAL DEFAULT 0,
        fine_paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active'
    )''')

    # Issue Requests table (Pending Issue Requests report)
    c.execute('''CREATE TABLE IF NOT EXISTS issue_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        requested_date TEXT NOT NULL,
        request_fulfilled_date TEXT
    )''')

    # Insert default users exactly as per Excel
    c.execute("INSERT OR IGNORE INTO users (username, password, name, is_admin, is_active) VALUES (?, ?, ?, ?, ?)",
              ('adm', 'adm', 'Administrator', 1, 1))
    c.execute("INSERT OR IGNORE INTO users (username, password, name, is_admin, is_active) VALUES (?, ?, ?, ?, ?)",
              ('user', 'user', 'Regular User', 0, 1))

    # Sample Books - Categories from Excel: Science, Economics, Fiction, Children, Personal Development
    # Code format from Excel: SC(B/M)000001 to SC(B/M)000004 etc.
    today = datetime.now().date()
    books = [
        ('SC(B)000001', 'A Brief History of Time', 'Stephen Hawking', 'Science', 'Book', 'Available', 450.00, '2023-01-15'),
        ('SC(B)000002', 'The Selfish Gene', 'Richard Dawkins', 'Science', 'Book', 'Available', 380.00, '2023-02-10'),
        ('SC(B)000003', 'Cosmos', 'Carl Sagan', 'Science', 'Book', 'Issued', 420.00, '2023-01-20'),
        ('SC(B)000004', 'The Grand Design', 'Stephen Hawking', 'Science', 'Book', 'Available', 500.00, '2023-03-05'),
        ('EC(B)000001', 'The Wealth of Nations', 'Adam Smith', 'Economics', 'Book', 'Available', 600.00, '2023-01-12'),
        ('EC(B)000002', 'Thinking Fast and Slow', 'Daniel Kahneman', 'Economics', 'Book', 'Available', 550.00, '2023-04-01'),
        ('EC(B)000003', 'Freakonomics', 'Steven Levitt', 'Economics', 'Book', 'Issued', 350.00, '2023-02-22'),
        ('EC(B)000004', 'The Black Swan', 'Nassim Taleb', 'Economics', 'Book', 'Available', 480.00, '2023-03-14'),
        ('FC(B)000001', 'To Kill a Mockingbird', 'Harper Lee', 'Fiction', 'Book', 'Available', 300.00, '2023-01-08'),
        ('FC(B)000002', '1984', 'George Orwell', 'Fiction', 'Book', 'Available', 280.00, '2023-02-18'),
        ('FC(B)000003', 'The Great Gatsby', 'F. Scott Fitzgerald', 'Fiction', 'Book', 'Available', 320.00, '2023-03-22'),
        ('FC(B)000004', 'Pride and Prejudice', 'Jane Austen', 'Fiction', 'Book', 'Issued', 290.00, '2023-01-30'),
        ('CH(B)000001', 'Harry Potter', 'J.K. Rowling', 'Children', 'Book', 'Available', 400.00, '2023-02-05'),
        ('CH(B)000002', 'The Lion the Witch and the Wardrobe', 'C.S. Lewis', 'Children', 'Book', 'Available', 350.00, '2023-03-11'),
        ('CH(B)000003', 'Charlottes Web', 'E.B. White', 'Children', 'Book', 'Available', 280.00, '2023-01-25'),
        ('CH(B)000004', 'The Jungle Book', 'Rudyard Kipling', 'Children', 'Book', 'Available', 260.00, '2023-04-08'),
        ('PD(B)000001', 'Atomic Habits', 'James Clear', 'Personal Development', 'Book', 'Available', 450.00, '2023-02-14'),
        ('PD(B)000002', '7 Habits of Highly Effective People', 'Stephen Covey', 'Personal Development', 'Book', 'Available', 500.00, '2023-03-01'),
        ('PD(B)000003', 'Think and Grow Rich', 'Napoleon Hill', 'Personal Development', 'Book', 'Available', 380.00, '2023-01-18'),
        ('PD(B)000004', 'Deep Work', 'Cal Newport', 'Personal Development', 'Book', 'Issued', 420.00, '2023-02-28'),
        # Movies
        ('SC(M)000001', 'Interstellar', 'Christopher Nolan', 'Science', 'Movie', 'Available', 200.00, '2023-01-10'),
        ('SC(M)000002', 'The Martian', 'Ridley Scott', 'Science', 'Movie', 'Available', 180.00, '2023-02-15'),
        ('SC(M)000003', 'Gravity', 'Alfonso Cuaron', 'Science', 'Movie', 'Available', 160.00, '2023-03-20'),
        ('SC(M)000004', 'Apollo 13', 'Ron Howard', 'Science', 'Movie', 'Issued', 170.00, '2023-04-01'),
        ('FC(M)000001', 'The Lord of the Rings', 'Peter Jackson', 'Fiction', 'Movie', 'Available', 250.00, '2023-03-20'),
        ('FC(M)000002', 'Inception', 'Christopher Nolan', 'Fiction', 'Movie', 'Available', 220.00, '2023-01-22'),
        ('FC(M)000003', 'The Dark Knight', 'Christopher Nolan', 'Fiction', 'Movie', 'Issued', 230.00, '2023-02-10'),
        ('FC(M)000004', 'Avengers Endgame', 'Russo Brothers', 'Fiction', 'Movie', 'Available', 240.00, '2023-03-15'),
    ]
    for b in books:
        c.execute("INSERT OR IGNORE INTO products (serial_no, name, author, category, type, status, cost, procurement_date) VALUES (?,?,?,?,?,?,?,?)", b)

    # Sample memberships
    members = [
        ('MEM000001', 'Rahul', 'Sharma', 'Rahul Sharma', '123 MG Road Mumbai', '1234-5678-9012', '2024-01-01', '2024-07-01', 'Six Months', 'Active', 0),
        ('MEM000002', 'Priya', 'Patel', 'Priya Patel', '456 FC Road Pune', '2345-6789-0123', '2024-02-01', '2025-02-01', 'One Year', 'Active', 150.00),
        ('MEM000003', 'Amit', 'Singh', 'Amit Singh', '789 Brigade Road Bangalore', '3456-7890-1234', '2023-06-01', '2025-06-01', 'Two Years', 'Active', 0),
        ('MEM000004', 'Neha', 'Gupta', 'Neha Gupta', '321 Park Street Kolkata', '4567-8901-2345', '2023-01-01', '2024-01-01', 'One Year', 'Inactive', 300.00),
        ('MEM000005', 'Vikram', 'Kumar', 'Vikram Kumar', '654 Anna Salai Chennai', '5678-9012-3456', '2024-03-01', '2024-09-01', 'Six Months', 'Active', 0),
    ]
    for m in members:
        c.execute("INSERT OR IGNORE INTO memberships (membership_id, first_name, last_name, contact_name, contact_address, aadhar_no, start_date, end_date, membership_type, status, amount_pending) VALUES (?,?,?,?,?,?,?,?,?,?,?)", m)

    # Sample active issues
    issues = [
        ('SC(B)000003', 'Cosmos', 'Carl Sagan', 'MEM000001', str(today - timedelta(days=5)), str(today + timedelta(days=10)), None, '', 0, 0, 'Active'),
        ('EC(B)000003', 'Freakonomics', 'Steven Levitt', 'MEM000002', str(today - timedelta(days=20)), str(today - timedelta(days=5)), None, '', 150.00, 0, 'Active'),
        ('FC(B)000004', 'Pride and Prejudice', 'Jane Austen', 'MEM000003', str(today - timedelta(days=3)), str(today + timedelta(days=12)), None, '', 0, 0, 'Active'),
        ('SC(M)000004', 'Apollo 13', 'Ron Howard', 'MEM000005', str(today - timedelta(days=18)), str(today - timedelta(days=3)), None, '', 60.00, 0, 'Active'),
        ('FC(M)000003', 'The Dark Knight', 'Christopher Nolan', 'MEM000001', str(today - timedelta(days=30)), str(today - timedelta(days=15)), None, '', 150.00, 0, 'Active'),
        ('PD(B)000004', 'Deep Work', 'Cal Newport', 'MEM000002', str(today - timedelta(days=7)), str(today + timedelta(days=8)), None, '', 0, 0, 'Active'),
    ]
    for i in issues:
        c.execute("INSERT OR IGNORE INTO issues (serial_no, product_name, author, membership_id, issue_date, return_date, actual_return_date, remarks, fine_calculated, fine_paid, status) VALUES (?,?,?,?,?,?,?,?,?,?,?)", i)

    # Sample issue requests
    requests = [
        ('MEM000004', '1984', str(today - timedelta(days=2)), None),
        ('MEM000002', 'Atomic Habits', str(today - timedelta(days=5)), None),
        ('MEM000003', 'Interstellar', str(today - timedelta(days=1)), None),
    ]
    for r in requests:
        c.execute("INSERT OR IGNORE INTO issue_requests (membership_id, product_name, requested_date, request_fulfilled_date) VALUES (?,?,?,?)", r)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
