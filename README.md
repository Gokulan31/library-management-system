# Library Management System

Built strictly per the Excel specification using Python Flask + SQLite + HTML/CSS/JS.

## How to Run

```bash
# 1. Install Flask
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open browser
http://localhost:5000
```

## Login Credentials (from Excel)

| Role  | User ID | Password |
|-------|---------|----------|
| Admin | adm     | adm      |
| User  | user    | user     |

## Pages (per Excel)

| Sheet              | URL                                       |
|--------------------|-------------------------------------------|
| Admin/User Login   | /login                                    |
| Admin Home Page    | /home (admin)                             |
| User Home Page     | /home (user)                              |
| Transactions       | /transactions                             |
| Book Available     | /book-available                           |
| Search Results     | /book-available (POST results)            |
| Book Issue         | /book-issue                               |
| Return Book        | /return-book                              |
| Pay Fine           | /pay-fine                                 |
| Reports            | /reports                                  |
| Master List Books  | /reports/master-list-of-books             |
| Master List Movies | /reports/master-list-of-movies            |
| Memberships        | /reports/master-list-of-memberships       |
| Active Issues      | /reports/active-issues                    |
| Overdue Returns    | /reports/overdue-returns                  |
| Issue Requests     | /reports/issue-requests                   |
| Maintenance        | /maintenance                              |
| Add Membership     | /maintenance/add-membership               |
| Update Membership  | /maintenance/update-membership            |
| Add Book/Movie     | /maintenance/add-book                     |
| Update Book/Movie  | /maintenance/update-book                  |
| User Management    | /maintenance/user-management              |
| Confirmation       | /confirmation                             |
| Cancel             | /cancel                                   |
| Log Out            | /logout                                   |

## Database

SQLite database auto-created at `instance/library.db` on first run.

Tables: users, products, memberships, issues, issue_requests

## Access Control (per Excel)

- Admin: Maintenance + Reports + Transactions
- User: Reports + Transactions only (no Maintenance)
