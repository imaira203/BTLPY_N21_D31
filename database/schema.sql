
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
  salary_text VARCHAR(128) NULL,
  location VARCHAR(128) NULL,
  job_type VARCHAR(64) NULL,
  status ENUM('draft','pending_approval','published','rejected') NOT NULL DEFAULT 'pending_approval',
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
  status ENUM('submitted','reviewed','rejected') NOT NULL DEFAULT 'submitted',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (cv_id) REFERENCES cv_documents(id) ON DELETE SET NULL,
  INDEX idx_app_job (job_id),
  INDEX idx_app_cand (candidate_id)
);
