# HRG Smart Inventory Pro

A full-stack construction inventory management system upgraded from a single-page prototype into a Flask application with authentication, persistent database storage, business workflows, dashboards, and machine-learning based reorder recommendations.

## Key Features

- Role-based login with Admin, Manager, and Viewer access.
- bcrypt password hashing and Flask-Login session management.
- MySQL-ready SQLAlchemy models for users, materials, suppliers, transactions, purchase orders, construction sites, and site inventory.
- Stock In / Stock Out workflows with site-wise consumption tracking.
- Purchase order creation, approval, delivery, and cancellation.
- Multi-site inventory tracking for Jaipur Project, Ajmer Project, and Jodhpur Project.
- Chart.js dashboards for inventory value, monthly consumption, supplier performance, and PO trends.
- Linear Regression demand forecasting using Pandas, NumPy, and scikit-learn.
- CSV export for inventory reports.

## Demo Login

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@hrg.com` | `admin123` |
| Manager | `manager@hrg.com` | `manager123` |
| Viewer | `viewer@hrg.com` | `viewer123` |

## Tech Stack

| Layer | Tools |
| --- | --- |
| Backend | Flask, Flask-Login |
| Database | MySQL, SQLAlchemy, PyMySQL |
| Security | bcrypt password hashing |
| Analytics | Chart.js |
| Machine Learning | Pandas, NumPy, scikit-learn Linear Regression |
| Deployment | Render, Railway, PythonAnywhere, or any Gunicorn-compatible host |

## Local Setup

```powershell
cd HRG_Smart_Inventory_Pro_Flask
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

For a quick local demo, keep the SQLite fallback:

```env
DATABASE_URL=sqlite:///hrg_inventory_dev.db
```

For MySQL, create a database first:

```sql
CREATE DATABASE hrg_inventory;
```

Then set `.env`:

```env
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost/hrg_inventory
```

Run the app:

```powershell
flask --app app seed-demo
flask --app app run
```

Open `http://127.0.0.1:5000`.

## Database Design

The app creates these tables automatically through SQLAlchemy:

- `users`
- `materials`
- `suppliers`
- `transactions`
- `purchase_orders`
- `sites`
- `site_inventory`

The same structure is also documented in `database_schema.sql` for interview discussion or manual MySQL setup.

## Role Permissions

| Feature | Admin | Manager | Viewer |
| --- | --- | --- | --- |
| View dashboards | Yes | Yes | Yes |
| Add/edit materials | Yes | Yes | No |
| Add suppliers | Yes | Yes | No |
| Record stock movement | Yes | Yes | No |
| Create purchase orders | Yes | Yes | No |
| Approve/deliver/cancel POs | Yes | Yes | No |
| Export reports | Yes | Yes | Yes |

## Phase Mapping

| Requested Phase | Implemented In |
| --- | --- |
| Authentication | `User` model, `/login`, `/logout`, roles, bcrypt hashes |
| Database Integration | SQLAlchemy models with MySQL `DATABASE_URL` support |
| Data Persistence | All inventory, suppliers, transactions, POs, and sites stored in DB |
| Purchase Orders | `/purchase-orders` workflow with Pending, Approved, Delivered, Cancelled |
| Multi-Site Inventory | `/sites`, `Site`, `SiteInventory`, and site-linked transactions |
| Advanced Dashboard | `/dashboard` and `/analytics` with Chart.js KPIs |
| Demand Forecasting | `/forecast` with Linear Regression prediction |
| Reorder Engine | Recommended purchase quantity and remaining days calculations |
| GitHub Repository | `.gitignore`, README, schema, requirements, deployment files |
| Live Deployment | `Procfile`, `runtime.txt`, and deployment notes below |

## Deployment Notes

### Recommended Public Demo: Railway + MySQL

1. Push this folder to a GitHub repository.
2. In Railway, create a new project from that GitHub repo.
3. Add a MySQL database service to the same Railway project.
4. Copy the MySQL connection variable into the web service as:
   - `DATABASE_URL=${{MySQL.MYSQL_URL}}`
5. Add another web service variable:
   - `SECRET_KEY=replace-with-a-long-random-secret`
6. Set the start command to:

```bash
gunicorn app:app
```

7. Deploy the service, then open the generated Railway public domain.

If the service starts with empty tables, open the Railway shell for the web service and run:

```bash
flask --app app seed-demo
```

### Render or Railway

1. Push this folder to GitHub.
2. Create a new web service from the repository.
3. Add environment variables:
   - `SECRET_KEY`
   - `DATABASE_URL`
4. Use `pip install -r requirements.txt` as the build command.
5. Use `gunicorn app:app` as the start command.

### PythonAnywhere

1. Upload the project or clone it from GitHub.
2. Create a virtual environment and install `requirements.txt`.
3. Configure the WSGI file to import `app` from `app.py`.
4. Add MySQL credentials in `.env`.

## Screenshots Included

The `screenshots/` folder includes PNGs for:

- `dashboard.png`
- `inventory.png`
- `purchase-orders.png`
- `sites.png`
- `forecast.png`

## Interview Talking Points

- The project moved from frontend arrays to a normalized relational database.
- The role system separates read-only users from operational users.
- Purchase orders model a real approval and delivery workflow.
- Site-wise inventory helps construction companies track consumption by project.
- Forecasting uses historical consumption to recommend future purchase quantities.
