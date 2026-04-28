
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NULL,
  avatar_storage_key VARCHAR(512) NULL,
  role ENUM('candidate','hr','admin') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hr_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  company_name VARCHAR(255) NOT NULL,
  avatar_storage_key VARCHAR(512) NULL,
  contact_phone VARCHAR(64) NULL,
  company_description TEXT NULL,
  approval_status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  admin_note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  hr_user_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  department VARCHAR(128) NULL,
  level VARCHAR(64) NULL,
  min_salary INT NULL,
  max_salary INT NULL,
  location VARCHAR(128) NULL,
  job_type VARCHAR(64) NULL,
  headcount INT NULL,
  deadline_text VARCHAR(32) NULL,
  view_count INT NOT NULL DEFAULT 0,
  status ENUM('draft','pending_approval','published','closed','rejected') NOT NULL DEFAULT 'pending_approval',
  admin_note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hr_user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_jobs_hr (hr_user_id),
  INDEX idx_jobs_status (status)
);

-- stored_filename: đường dẫn tương đối trong uploads/, ví dụ cvs/1_abc.pdf
CREATE TABLE IF NOT EXISTS cv_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  original_name VARCHAR(512) NOT NULL,
  stored_filename VARCHAR(512) NOT NULL UNIQUE,
  mime_type VARCHAR(128) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_cv_user (user_id)
);

CREATE TABLE IF NOT EXISTS job_applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  job_id INT NOT NULL,
  candidate_id INT NOT NULL,
  cv_id INT NULL,
  status ENUM('pending','reviewed','approved','rejected') NOT NULL DEFAULT 'pending',
  accepted_at DATETIME NULL,
  contact_unlocked_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (cv_id) REFERENCES cv_documents(id) ON DELETE SET NULL,
  INDEX idx_app_job (job_id),
  INDEX idx_app_cand (candidate_id)
);

CREATE TABLE IF NOT EXISTS candidate_subscriptions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT NOT NULL UNIQUE,
  status ENUM('inactive','active','expired') NOT NULL DEFAULT 'inactive',
  pro_expires_at DATETIME NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_sub_cand (candidate_id)
);

CREATE TABLE IF NOT EXISTS candidate_saved_jobs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT NOT NULL,
  job_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_candidate_saved_job (candidate_id, job_id),
  INDEX idx_saved_jobs_candidate (candidate_id),
  INDEX idx_saved_jobs_job (job_id)
);

CREATE TABLE IF NOT EXISTS candidate_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  tagline VARCHAR(255) NULL,
  phone VARCHAR(64) NULL,
  address VARCHAR(255) NULL,
  professional_field VARCHAR(255) NULL,
  degree VARCHAR(255) NULL,
  experience_text VARCHAR(255) NULL,
  language VARCHAR(255) NULL,
  skills_json TEXT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_candidate_profile_user (user_id)
);

CREATE TABLE IF NOT EXISTS invoices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_user_id INT NOT NULL,
  invoice_type ENUM('pro_upgrade','candidate_contact_unlock') NOT NULL,
  status ENUM('pending','paid','overdue','cancelled') NOT NULL DEFAULT 'pending',
  amount DECIMAL(12,2) NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'VND',
  due_at DATETIME NOT NULL,
  sepay_order_code VARCHAR(64) NOT NULL UNIQUE,
  sepay_payment_url VARCHAR(1024) NULL,
  note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paid_at DATETIME NULL,
  application_id INT NULL,
  FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (application_id) REFERENCES job_applications(id) ON DELETE SET NULL,
  INDEX idx_invoice_owner (owner_user_id),
  INDEX idx_invoice_application (application_id),
  INDEX idx_invoice_status (status)
);

CREATE TABLE IF NOT EXISTS candidate_subscription_payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT NOT NULL,
  invoice_id INT NULL UNIQUE,
  months INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'VND',
  paid_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL,
  INDEX idx_candidate_sub_payments_candidate (candidate_id),
  INDEX idx_candidate_sub_payments_paid_at (paid_at)
);
