import csv
import os
from collections import defaultdict
from datetime import date, datetime
from io import StringIO

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy


load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

ROLE_LEVEL = {"Viewer": 1, "Manager": 2, "Admin": 3}
CATEGORIES = ["Binding", "Aggregate", "Steel", "Masonry", "Electrical", "Plumbing", "Other"]
UNITS = ["Bags", "MT", "Cubic Meter", "Pieces", "Litres", "Kg", "Meters"]
PO_STATUSES = ["Pending", "Approved", "Delivered", "Cancelled"]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Viewer")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.active

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), unique=True, nullable=False)
    contact = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    category = db.Column(db.String(60), default="Other")
    rating = db.Column(db.Integer, default=3)
    lead_days = db.Column(db.Integer, default=3)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    materials = db.relationship("Material", back_populates="supplier")
    purchase_orders = db.relationship("PurchaseOrder", back_populates="supplier")


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), unique=True, nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    manager = db.Column(db.String(120))
    status = db.Column(db.String(40), default="Active")
    budget = db.Column(db.Float, default=0)

    transactions = db.relationship("Transaction", back_populates="site")
    inventory_items = db.relationship("SiteInventory", back_populates="site")
    purchase_orders = db.relationship("PurchaseOrder", back_populates="site")


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    category = db.Column(db.String(60), nullable=False, default="Other")
    quantity = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(40), nullable=False, default="Pieces")
    min_level = db.Column(db.Float, nullable=False, default=0)
    rate = db.Column(db.Float, nullable=False, default=0)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    supplier = db.relationship("Supplier", back_populates="materials")
    transactions = db.relationship("Transaction", back_populates="material")
    purchase_orders = db.relationship("PurchaseOrder", back_populates="material")
    site_inventories = db.relationship("SiteInventory", back_populates="material")

    @property
    def value(self):
        return self.quantity * self.rate

    @property
    def status_label(self):
        if self.quantity <= 0:
            return "Out of Stock"
        if self.quantity < self.min_level:
            return "Low Stock"
        return "In Stock"

    @property
    def status_slug(self):
        if self.quantity <= 0:
            return "danger"
        if self.quantity < self.min_level:
            return "warn"
        return "ok"


class SiteInventory(db.Model):
    __tablename__ = "site_inventory"
    __table_args__ = (db.UniqueConstraint("site_id", "material_id", name="uq_site_material"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0)

    site = db.relationship("Site", back_populates="inventory_items")
    material = db.relationship("Material", back_populates="site_inventories")


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.Date, nullable=False, default=date.today)
    transaction_type = db.Column(db.String(20), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"))
    quantity = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False, default=0)
    reference_no = db.Column(db.String(80))
    details = db.Column(db.Text)
    project_code = db.Column(db.String(60))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    material = db.relationship("Material", back_populates="transactions")
    site = db.relationship("Site", back_populates="transactions")
    created_by = db.relationship("User")

    @property
    def value(self):
        return self.quantity * self.rate


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(40), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"))
    quantity = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    expected_delivery = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)

    supplier = db.relationship("Supplier", back_populates="purchase_orders")
    material = db.relationship("Material", back_populates="purchase_orders")
    site = db.relationship("Site", back_populates="purchase_orders")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    @property
    def total_value(self):
        return self.quantity * self.rate


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-this-secret")
    database_url = os.getenv("DATABASE_URL", "sqlite:///hrg_inventory_dev.db")
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    register_filters(app)
    register_routes(app)

    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app


def register_filters(app):
    @app.template_filter("currency")
    def currency(value):
        value = float(value or 0)
        if value >= 10000000:
            return f"Rs {value / 10000000:.2f} Cr"
        if value >= 100000:
            return f"Rs {value / 100000:.2f} L"
        return f"Rs {value:,.0f}"

    @app.template_filter("num")
    def number(value):
        value = float(value or 0)
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"

    @app.context_processor
    def inject_globals():
        can_manage = current_user.is_authenticated and ROLE_LEVEL.get(current_user.role, 0) >= 2
        can_admin = current_user.is_authenticated and current_user.role == "Admin"
        return {
            "categories": CATEGORIES,
            "units": UNITS,
            "po_statuses": PO_STATUSES,
            "can_manage": can_manage,
            "can_admin": can_admin,
            "today": date.today(),
        }


def role_required(*allowed_roles):
    def decorator(view_func):
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in allowed_roles:
                flash("Your role does not have permission for that action.", "danger")
                return redirect(request.referrer or url_for("dashboard"))
            return view_func(*args, **kwargs)

        wrapped.__name__ = view_func.__name__
        return wrapped

    return decorator


def parse_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value, default=None):
    if not value:
        return default or date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def register_routes(app):
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash(f"Welcome back, {user.name}.", "success")
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        stats = dashboard_stats()
        chart_data = chart_payload()
        low_materials = Material.query.order_by(Material.quantity.asc()).all()
        recent_transactions = (
            Transaction.query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(8)
            .all()
        )
        return render_template(
            "dashboard.html",
            active_page="dashboard",
            stats=stats,
            chart_data=chart_data,
            low_materials=low_materials,
            recent_transactions=recent_transactions,
        )

    @app.route("/inventory")
    @login_required
    def inventory():
        query = Material.query
        search = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        status = request.args.get("status", "")
        if search:
            query = query.filter(Material.name.ilike(f"%{search}%"))
        if category:
            query = query.filter_by(category=category)
        materials = query.order_by(Material.category, Material.name).all()
        if status:
            materials = [m for m in materials if m.status_slug == status]
        return render_template(
            "inventory.html",
            active_page="inventory",
            materials=materials,
            search=search,
            category=category,
            status=status,
        )

    @app.route("/materials/new", methods=["GET", "POST"])
    @login_required
    @role_required("Admin", "Manager")
    def material_new():
        if request.method == "POST":
            material = Material()
            save_material_from_form(material)
            db.session.add(material)
            db.session.commit()
            flash("Material created successfully.", "success")
            return redirect(url_for("inventory"))
        return render_template(
            "material_form.html",
            active_page="material_new",
            material=None,
            suppliers=Supplier.query.order_by(Supplier.name).all(),
        )

    @app.route("/materials/<int:material_id>/edit", methods=["GET", "POST"])
    @login_required
    @role_required("Admin", "Manager")
    def material_edit(material_id):
        material = db.get_or_404(Material, material_id)
        if request.method == "POST":
            save_material_from_form(material)
            db.session.commit()
            flash("Material updated successfully.", "success")
            return redirect(url_for("inventory"))
        return render_template(
            "material_form.html",
            active_page="inventory",
            material=material,
            suppliers=Supplier.query.order_by(Supplier.name).all(),
        )

    @app.route("/suppliers", methods=["GET", "POST"])
    @login_required
    def suppliers():
        if request.method == "POST":
            if ROLE_LEVEL.get(current_user.role, 0) < 2:
                flash("Only Admin and Manager users can add suppliers.", "danger")
                return redirect(url_for("suppliers"))
            supplier = Supplier()
            save_supplier_from_form(supplier)
            db.session.add(supplier)
            db.session.commit()
            flash("Supplier saved.", "success")
            return redirect(url_for("suppliers"))
        return render_template(
            "suppliers.html",
            active_page="suppliers",
            suppliers=Supplier.query.order_by(Supplier.name).all(),
        )

    @app.route("/suppliers/<int:supplier_id>/edit", methods=["POST"])
    @login_required
    @role_required("Admin", "Manager")
    def supplier_edit(supplier_id):
        supplier = db.get_or_404(Supplier, supplier_id)
        save_supplier_from_form(supplier)
        db.session.commit()
        flash("Supplier updated.", "success")
        return redirect(url_for("suppliers"))

    @app.route("/stock", methods=["GET", "POST"])
    @login_required
    def stock():
        if request.method == "POST":
            if ROLE_LEVEL.get(current_user.role, 0) < 2:
                flash("Only Admin and Manager users can record stock movement.", "danger")
                return redirect(url_for("stock"))
            handle_stock_form()
            return redirect(url_for("stock"))
        recent = (
            Transaction.query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(12)
            .all()
        )
        return render_template(
            "stock.html",
            active_page="stock",
            materials=Material.query.order_by(Material.name).all(),
            sites=Site.query.order_by(Site.name).all(),
            recent=recent,
        )

    @app.route("/purchase-orders", methods=["GET", "POST"])
    @login_required
    def purchase_orders():
        if request.method == "POST":
            if ROLE_LEVEL.get(current_user.role, 0) < 2:
                flash("Only Admin and Manager users can create purchase orders.", "danger")
                return redirect(url_for("purchase_orders"))
            order = PurchaseOrder(
                po_number=next_po_number(),
                supplier_id=int(request.form["supplier_id"]),
                material_id=int(request.form["material_id"]),
                site_id=int(request.form["site_id"]) if request.form.get("site_id") else None,
                quantity=parse_float(request.form.get("quantity")),
                rate=parse_float(request.form.get("rate")),
                expected_delivery=parse_date(request.form.get("expected_delivery"), None)
                if request.form.get("expected_delivery")
                else None,
                notes=request.form.get("notes"),
                created_by_id=current_user.id,
            )
            db.session.add(order)
            db.session.commit()
            flash(f"Purchase order {order.po_number} created.", "success")
            return redirect(url_for("purchase_orders"))
        return render_template(
            "purchase_orders.html",
            active_page="purchase_orders",
            purchase_orders=PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all(),
            suppliers=Supplier.query.order_by(Supplier.name).all(),
            materials=Material.query.order_by(Material.name).all(),
            sites=Site.query.order_by(Site.name).all(),
        )

    @app.route("/purchase-orders/<int:order_id>/<action>", methods=["POST"])
    @login_required
    @role_required("Admin", "Manager")
    def purchase_order_action(order_id, action):
        order = db.get_or_404(PurchaseOrder, order_id)
        if action == "approve" and order.status == "Pending":
            order.status = "Approved"
            order.approved_by_id = current_user.id
            order.approved_at = datetime.utcnow()
            flash(f"{order.po_number} approved.", "success")
        elif action == "deliver" and order.status in {"Approved", "Pending"}:
            order.status = "Delivered"
            order.material.quantity += order.quantity
            order.material.rate = order.rate
            txn = Transaction(
                transaction_date=date.today(),
                transaction_type="Stock In",
                material_id=order.material_id,
                site_id=order.site_id,
                quantity=order.quantity,
                rate=order.rate,
                reference_no=order.po_number,
                details=f"Delivered from {order.supplier.name}",
                project_code=order.site.code if order.site else "",
                created_by_id=current_user.id,
            )
            db.session.add(txn)
            flash(f"{order.po_number} marked delivered and stock updated.", "success")
        elif action == "cancel" and order.status != "Delivered":
            order.status = "Cancelled"
            flash(f"{order.po_number} cancelled.", "warning")
        else:
            flash("That purchase order action is not allowed from the current status.", "danger")
        db.session.commit()
        return redirect(url_for("purchase_orders"))

    @app.route("/sites")
    @login_required
    def sites():
        site_rows = []
        for site in Site.query.order_by(Site.name).all():
            consumption = (
                db.session.query(db.func.coalesce(db.func.sum(Transaction.quantity * Transaction.rate), 0))
                .filter(Transaction.site_id == site.id, Transaction.transaction_type == "Stock Out")
                .scalar()
            )
            stock_items = SiteInventory.query.filter_by(site_id=site.id).all()
            site_rows.append({"site": site, "consumption": consumption, "stock_items": stock_items})
        return render_template("sites.html", active_page="sites", site_rows=site_rows)

    @app.route("/analytics")
    @login_required
    def analytics():
        return render_template(
            "analytics.html",
            active_page="analytics",
            stats=dashboard_stats(),
            chart_data=chart_payload(),
            supplier_rows=supplier_performance(),
        )

    @app.route("/forecast")
    @login_required
    def forecast():
        rows = forecast_rows()
        return render_template("forecast.html", active_page="forecast", forecast_rows=rows)

    @app.route("/activity")
    @login_required
    def activity():
        filter_type = request.args.get("type", "")
        query = Transaction.query
        if filter_type:
            query = query.filter_by(transaction_type=filter_type)
        transactions = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()
        return render_template(
            "activity.html",
            active_page="activity",
            transactions=transactions,
            filter_type=filter_type,
        )

    @app.route("/reports/inventory.csv")
    @login_required
    def export_inventory():
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Material", "Category", "Quantity", "Unit", "Minimum Level", "Rate", "Value", "Supplier", "Status"])
        for material in Material.query.order_by(Material.name).all():
            writer.writerow(
                [
                    material.name,
                    material.category,
                    material.quantity,
                    material.unit,
                    material.min_level,
                    material.rate,
                    material.value,
                    material.supplier.name if material.supplier else "",
                    material.status_label,
                ]
            )
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=hrg_inventory_report.csv"},
        )

    @app.cli.command("seed-demo")
    def seed_demo_command():
        seed_demo_data(force=True)
        print("Demo data loaded.")


def save_material_from_form(material):
    material.name = request.form["name"].strip()
    material.category = request.form.get("category") or "Other"
    material.unit = request.form.get("unit") or "Pieces"
    material.quantity = parse_float(request.form.get("quantity"))
    material.min_level = parse_float(request.form.get("min_level"))
    material.rate = parse_float(request.form.get("rate"))
    material.supplier_id = int(request.form["supplier_id"]) if request.form.get("supplier_id") else None
    material.notes = request.form.get("notes")


def save_supplier_from_form(supplier):
    supplier.name = request.form["name"].strip()
    supplier.contact = request.form.get("contact")
    supplier.phone = request.form.get("phone")
    supplier.category = request.form.get("category") or "Other"
    supplier.rating = int(parse_float(request.form.get("rating"), 3))
    supplier.lead_days = int(parse_float(request.form.get("lead_days"), 3))
    supplier.notes = request.form.get("notes")
    supplier.active = request.form.get("active", "on") == "on"


def handle_stock_form():
    material = db.get_or_404(Material, int(request.form["material_id"]))
    quantity = parse_float(request.form.get("quantity"))
    transaction_type = request.form.get("transaction_type")
    site_id = int(request.form["site_id"]) if request.form.get("site_id") else None
    rate = parse_float(request.form.get("rate"), material.rate)

    if quantity <= 0:
        flash("Quantity must be greater than zero.", "danger")
        return
    if transaction_type == "Stock Out" and quantity > material.quantity:
        flash(f"Insufficient stock. Only {material.quantity:g} {material.unit} available.", "danger")
        return

    if transaction_type == "Stock In":
        material.quantity += quantity
        material.rate = rate
    else:
        material.quantity -= quantity
        if site_id:
            site_item = SiteInventory.query.filter_by(site_id=site_id, material_id=material.id).first()
            if not site_item:
                site_item = SiteInventory(site_id=site_id, material_id=material.id, quantity=0)
                db.session.add(site_item)
            site_item.quantity += quantity

    txn = Transaction(
        transaction_date=parse_date(request.form.get("transaction_date")),
        transaction_type=transaction_type,
        material_id=material.id,
        site_id=site_id,
        quantity=quantity,
        rate=rate,
        reference_no=request.form.get("reference_no"),
        details=request.form.get("details"),
        project_code=request.form.get("project_code"),
        created_by_id=current_user.id,
    )
    db.session.add(txn)
    db.session.commit()
    flash(f"{transaction_type} recorded for {material.name}.", "success")


def dashboard_stats():
    materials = Material.query.all()
    total_value = sum(m.value for m in materials)
    today_month = date.today().strftime("%Y-%m")
    month_consumption = (
        db.session.query(db.func.coalesce(db.func.sum(Transaction.quantity * Transaction.rate), 0))
        .filter(
            Transaction.transaction_type == "Stock Out",
            db.func.date_format(Transaction.transaction_date, "%Y-%m") == today_month
            if "mysql" in str(db.engine.url)
            else db.func.strftime("%Y-%m", Transaction.transaction_date) == today_month,
        )
        .scalar()
    )
    return {
        "total_materials": len(materials),
        "total_inventory_value": total_value,
        "low_stock": sum(1 for m in materials if m.status_slug == "warn"),
        "out_stock": sum(1 for m in materials if m.status_slug == "danger"),
        "pending_orders": PurchaseOrder.query.filter_by(status="Pending").count(),
        "active_suppliers": Supplier.query.filter_by(active=True).count(),
        "active_sites": Site.query.filter_by(status="Active").count(),
        "monthly_consumption": month_consumption or 0,
    }


def chart_payload():
    materials = Material.query.order_by(Material.name).all()
    txns = Transaction.query.all()
    orders = PurchaseOrder.query.all()

    category_values = defaultdict(float)
    for material in materials:
        category_values[material.category] += material.value

    month_keys = sorted({t.transaction_date.strftime("%Y-%m") for t in txns})[-6:]
    if not month_keys:
        month_keys = [date.today().strftime("%Y-%m")]
    month_labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in month_keys]
    consumption = []
    stock_in = []
    for month in month_keys:
        consumption.append(
            sum(t.quantity * t.rate for t in txns if t.transaction_type == "Stock Out" and t.transaction_date.strftime("%Y-%m") == month)
        )
        stock_in.append(
            sum(t.quantity * t.rate for t in txns if t.transaction_type == "Stock In" and t.transaction_date.strftime("%Y-%m") == month)
        )

    po_month_keys = sorted({o.created_at.strftime("%Y-%m") for o in orders})[-6:] or month_keys
    po_labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in po_month_keys]
    po_counts = [sum(1 for o in orders if o.created_at.strftime("%Y-%m") == month) for month in po_month_keys]

    supplier_labels = []
    supplier_scores = []
    for supplier in Supplier.query.order_by(Supplier.rating.desc(), Supplier.lead_days.asc()).limit(8):
        supplier_labels.append(supplier.name)
        supplier_scores.append(max(1, min(100, supplier.rating * 18 + max(0, 10 - supplier.lead_days))))

    return {
        "categoryLabels": list(category_values.keys()),
        "categoryValues": list(category_values.values()),
        "monthLabels": month_labels,
        "consumptionValues": consumption,
        "stockInValues": stock_in,
        "poLabels": po_labels,
        "poCounts": po_counts,
        "supplierLabels": supplier_labels,
        "supplierScores": supplier_scores,
        "stockLabels": [m.name for m in materials[:10]],
        "stockValues": [m.quantity for m in materials[:10]],
    }


def supplier_performance():
    rows = []
    for supplier in Supplier.query.order_by(Supplier.name).all():
        order_count = PurchaseOrder.query.filter_by(supplier_id=supplier.id).count()
        delivered_count = PurchaseOrder.query.filter_by(supplier_id=supplier.id, status="Delivered").count()
        value = (
            db.session.query(db.func.coalesce(db.func.sum(PurchaseOrder.quantity * PurchaseOrder.rate), 0))
            .filter(PurchaseOrder.supplier_id == supplier.id)
            .scalar()
        )
        rows.append(
            {
                "supplier": supplier,
                "orders": order_count,
                "delivered": delivered_count,
                "delivery_rate": (delivered_count / order_count * 100) if order_count else 0,
                "value": value or 0,
            }
        )
    return rows


def forecast_rows():
    transactions = Transaction.query.filter_by(transaction_type="Stock Out").order_by(Transaction.transaction_date).all()
    by_material = defaultdict(lambda: defaultdict(float))
    for txn in transactions:
        by_material[txn.material_id][txn.transaction_date.strftime("%Y-%m")] += txn.quantity

    rows = []
    for material in Material.query.order_by(Material.name).all():
        monthly = by_material.get(material.id, {})
        values = [monthly[key] for key in sorted(monthly)]
        predicted = predict_next_month(values)
        avg_daily = (sum(values[-3:]) / 90) if values else 0
        remaining_days = int(material.quantity / avg_daily) if avg_daily > 0 else None
        recommended = max(0, round(predicted + material.min_level - material.quantity))
        rows.append(
            {
                "material": material,
                "history_months": len(values),
                "predicted_demand": round(predicted),
                "remaining_days": remaining_days,
                "recommended_purchase": recommended,
                "avg_daily": avg_daily,
            }
        )
    return sorted(rows, key=lambda row: row["recommended_purchase"], reverse=True)


def predict_next_month(values):
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression

        x = np.arange(len(values)).reshape(-1, 1)
        y = np.array(values)
        model = LinearRegression()
        model.fit(x, y)
        return max(0, float(model.predict([[len(values)]])[0]))
    except Exception:
        return sum(values[-3:]) / min(3, len(values))


def next_po_number():
    year = date.today().year
    count = PurchaseOrder.query.count() + 1
    return f"PO-{year}-{count:04d}"


def seed_demo_data(force=False):
    if force:
        db.drop_all()
        db.create_all()
    if User.query.first():
        return

    users = [
        ("Admin User", "admin@hrg.com", "admin123", "Admin"),
        ("Project Manager", "manager@hrg.com", "manager123", "Manager"),
        ("Site Viewer", "viewer@hrg.com", "viewer123", "Viewer"),
    ]
    for name, email, password, role in users:
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)

    suppliers = [
        Supplier(name="Birla Cement Ltd.", contact="Rajiv Sharma", phone="9876543210", category="Binding", rating=5, lead_days=3, notes="Premium supplier, consistent quality"),
        Supplier(name="Rajasthan Aggregates", contact="Suresh Patel", phone="9988776655", category="Aggregate", rating=4, lead_days=2, notes="Local supplier, good pricing"),
        Supplier(name="Tata Steel", contact="Pradeep Kumar", phone="9871234567", category="Steel", rating=5, lead_days=7, notes="Certified TMT rods, ISI marked"),
        Supplier(name="Local Kiln", contact="Ramji Lal", phone="9812345678", category="Masonry", rating=3, lead_days=1, notes="Reliable bulk brick orders"),
        Supplier(name="Supreme Industries", contact="Ankit Jain", phone="9900112233", category="Plumbing", rating=4, lead_days=4, notes="ISI certified PVC products"),
        Supplier(name="Polycab Ltd.", contact="Meena Verma", phone="9001122334", category="Electrical", rating=5, lead_days=5, notes="High quality wiring and cables"),
    ]
    db.session.add_all(suppliers)

    sites = [
        Site(name="Jaipur Project", code="JP-2026-01", city="Jaipur", manager="Jetharam Sir", budget=8500000),
        Site(name="Ajmer Project", code="AP-2026-02", city="Ajmer", manager="Ramesh Sharma", budget=6200000),
        Site(name="Jodhpur Project", code="JD-2026-03", city="Jodhpur", manager="Mohan Singh", budget=7100000),
    ]
    db.session.add_all(sites)
    db.session.flush()

    supplier_map = {supplier.name: supplier for supplier in suppliers}
    materials = [
        Material(name="OPC 53 Cement", category="Binding", quantity=420, unit="Bags", min_level=100, rate=380, supplier=supplier_map["Birla Cement Ltd."]),
        Material(name="River Sand Fine", category="Aggregate", quantity=85, unit="Cubic Meter", min_level=50, rate=1200, supplier=supplier_map["Rajasthan Aggregates"]),
        Material(name="Crushed Stone Bajri", category="Aggregate", quantity=210, unit="Cubic Meter", min_level=80, rate=950, supplier=supplier_map["Rajasthan Aggregates"]),
        Material(name="TMT Steel Rods 12mm", category="Steel", quantity=38, unit="MT", min_level=15, rate=62000, supplier=supplier_map["Tata Steel"]),
        Material(name="TMT Steel Rods 8mm", category="Steel", quantity=12, unit="MT", min_level=10, rate=61500, supplier=supplier_map["Tata Steel"]),
        Material(name="Red Bricks Class A", category="Masonry", quantity=8500, unit="Pieces", min_level=2000, rate=8, supplier=supplier_map["Local Kiln"]),
        Material(name="Coarse Aggregate 20mm", category="Aggregate", quantity=45, unit="Cubic Meter", min_level=60, rate=1100, supplier=supplier_map["Rajasthan Aggregates"]),
        Material(name="PVC Pipes 4 inch", category="Plumbing", quantity=95, unit="Pieces", min_level=20, rate=420, supplier=supplier_map["Supreme Industries"]),
        Material(name="Electrical Wires 2.5mm", category="Electrical", quantity=600, unit="Meters", min_level=200, rate=45, supplier=supplier_map["Polycab Ltd."]),
        Material(name="Paint Exterior White", category="Other", quantity=40, unit="Litres", min_level=50, rate=280, supplier=None),
    ]
    db.session.add_all(materials)
    db.session.flush()

    material_map = {material.name: material for material in materials}
    site_map = {site.name: site for site in sites}
    txn_rows = [
        ("2026-01-05", "Stock In", "OPC 53 Cement", "Jaipur Project", 300, 375, "INV-1001", "Birla Cement bulk purchase"),
        ("2026-01-16", "Stock Out", "OPC 53 Cement", "Jaipur Project", 70, 380, "ISS-1001", "Block A foundation"),
        ("2026-02-03", "Stock Out", "River Sand Fine", "Ajmer Project", 18, 1200, "ISS-1002", "Plastering work"),
        ("2026-02-17", "Stock In", "TMT Steel Rods 12mm", "Jaipur Project", 20, 61500, "INV-1002", "Tata Steel shipment"),
        ("2026-03-04", "Stock Out", "Crushed Stone Bajri", "Jodhpur Project", 36, 950, "ISS-1003", "Foundation filling"),
        ("2026-03-14", "Stock Out", "TMT Steel Rods 8mm", "Jaipur Project", 8, 61500, "ISS-1004", "Roof slab"),
        ("2026-03-21", "Stock In", "Red Bricks Class A", "Ajmer Project", 5000, 8, "INV-1003", "Local Kiln delivery"),
        ("2026-04-02", "Stock Out", "PVC Pipes 4 inch", "Jodhpur Project", 24, 420, "ISS-1005", "Bathroom block"),
        ("2026-04-16", "Stock Out", "Electrical Wires 2.5mm", "Jodhpur Project", 220, 45, "ISS-1006", "Block D wiring"),
        ("2026-05-05", "Stock In", "River Sand Fine", "Ajmer Project", 40, 1180, "INV-1004", "Rajasthan Aggregates"),
        ("2026-05-12", "Stock Out", "OPC 53 Cement", "Jaipur Project", 92, 380, "ISS-1007", "Column casting"),
        ("2026-05-20", "Stock Out", "Coarse Aggregate 20mm", "Ajmer Project", 35, 1100, "ISS-1008", "Road base work"),
    ]
    admin = User.query.filter_by(email="admin@hrg.com").first()
    for txn_date, txn_type, material_name, site_name, qty, rate, ref, details in txn_rows:
        material = material_map[material_name]
        site = site_map[site_name]
        db.session.add(
            Transaction(
                transaction_date=parse_date(txn_date),
                transaction_type=txn_type,
                material=material,
                site=site,
                quantity=qty,
                rate=rate,
                reference_no=ref,
                details=details,
                project_code=site.code,
                created_by=admin,
            )
        )
        if txn_type == "Stock Out":
            site_item = SiteInventory.query.filter_by(site_id=site.id, material_id=material.id).first()
            if not site_item:
                site_item = SiteInventory(site=site, material=material, quantity=0)
                db.session.add(site_item)
            site_item.quantity += qty

    orders = [
        PurchaseOrder(po_number="PO-2026-0001", supplier=supplier_map["Birla Cement Ltd."], material=material_map["OPC 53 Cement"], site=site_map["Jaipur Project"], quantity=250, rate=372, status="Pending", expected_delivery=parse_date("2026-06-05"), created_by=admin),
        PurchaseOrder(po_number="PO-2026-0002", supplier=supplier_map["Rajasthan Aggregates"], material=material_map["Coarse Aggregate 20mm"], site=site_map["Ajmer Project"], quantity=80, rate=1080, status="Approved", expected_delivery=parse_date("2026-06-02"), created_by=admin, approved_by=admin, approved_at=datetime.utcnow()),
        PurchaseOrder(po_number="PO-2026-0003", supplier=supplier_map["Tata Steel"], material=material_map["TMT Steel Rods 12mm"], site=site_map["Jodhpur Project"], quantity=15, rate=61200, status="Delivered", expected_delivery=parse_date("2026-05-18"), created_by=admin, approved_by=admin, approved_at=datetime.utcnow()),
        PurchaseOrder(po_number="PO-2026-0004", supplier=supplier_map["Supreme Industries"], material=material_map["PVC Pipes 4 inch"], site=site_map["Jodhpur Project"], quantity=60, rate=410, status="Cancelled", expected_delivery=parse_date("2026-05-29"), created_by=admin),
    ]
    db.session.add_all(orders)
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
