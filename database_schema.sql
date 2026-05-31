CREATE DATABASE IF NOT EXISTS hrg_inventory;
USE hrg_inventory;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'Viewer',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
);

CREATE TABLE suppliers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL UNIQUE,
  contact VARCHAR(120),
  phone VARCHAR(40),
  category VARCHAR(60) DEFAULT 'Other',
  rating INT DEFAULT 3,
  lead_days INT DEFAULT 3,
  notes TEXT,
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE sites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL UNIQUE,
  code VARCHAR(40) NOT NULL UNIQUE,
  city VARCHAR(80) NOT NULL,
  manager VARCHAR(120),
  status VARCHAR(40) DEFAULT 'Active',
  budget DECIMAL(14, 2) DEFAULT 0
);

CREATE TABLE materials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  category VARCHAR(60) NOT NULL DEFAULT 'Other',
  quantity DECIMAL(14, 2) NOT NULL DEFAULT 0,
  unit VARCHAR(40) NOT NULL DEFAULT 'Pieces',
  min_level DECIMAL(14, 2) NOT NULL DEFAULT 0,
  rate DECIMAL(14, 2) NOT NULL DEFAULT 0,
  supplier_id INT,
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_materials_name (name),
  CONSTRAINT fk_material_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE site_inventory (
  id INT AUTO_INCREMENT PRIMARY KEY,
  site_id INT NOT NULL,
  material_id INT NOT NULL,
  quantity DECIMAL(14, 2) NOT NULL DEFAULT 0,
  UNIQUE KEY uq_site_material (site_id, material_id),
  CONSTRAINT fk_site_inventory_site FOREIGN KEY (site_id) REFERENCES sites(id),
  CONSTRAINT fk_site_inventory_material FOREIGN KEY (material_id) REFERENCES materials(id)
);

CREATE TABLE transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  transaction_date DATE NOT NULL,
  transaction_type VARCHAR(20) NOT NULL,
  material_id INT NOT NULL,
  site_id INT,
  quantity DECIMAL(14, 2) NOT NULL,
  rate DECIMAL(14, 2) NOT NULL DEFAULT 0,
  reference_no VARCHAR(80),
  details TEXT,
  project_code VARCHAR(60),
  created_by_id INT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_transaction_material FOREIGN KEY (material_id) REFERENCES materials(id),
  CONSTRAINT fk_transaction_site FOREIGN KEY (site_id) REFERENCES sites(id),
  CONSTRAINT fk_transaction_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE purchase_orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  po_number VARCHAR(40) NOT NULL UNIQUE,
  supplier_id INT NOT NULL,
  material_id INT NOT NULL,
  site_id INT,
  quantity DECIMAL(14, 2) NOT NULL,
  rate DECIMAL(14, 2) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Pending',
  expected_delivery DATE,
  notes TEXT,
  created_by_id INT,
  approved_by_id INT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approved_at DATETIME,
  CONSTRAINT fk_po_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
  CONSTRAINT fk_po_material FOREIGN KEY (material_id) REFERENCES materials(id),
  CONSTRAINT fk_po_site FOREIGN KEY (site_id) REFERENCES sites(id),
  CONSTRAINT fk_po_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
  CONSTRAINT fk_po_approved_by FOREIGN KEY (approved_by_id) REFERENCES users(id)
);
