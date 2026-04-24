-- JobHub seed data compatible with current schema.
-- Run after schema.sql

INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES
  ('admin@jobhub.local', '$2b$12$seeded.replace.by.script', 'System Admin', 'admin', 1),
  ('hr@techcorp.vn', '$2b$12$seeded.replace.by.script', 'HR TechCorp', 'hr', 1),
  ('an.nguyen@email.com', '$2b$12$seeded.replace.by.script', 'Nguyen Van An', 'candidate', 1),
  ('binh.tran@email.com', '$2b$12$seeded.replace.by.script', 'Tran Thi Binh', 'candidate', 1)
ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), is_active = VALUES(is_active);

INSERT INTO hr_profiles (user_id, company_name, contact_phone, company_description, approval_status)
SELECT u.id, 'TechCorp Vietnam', '0241234567', 'Tech company hiring engineers.', 'approved'
FROM users u
WHERE u.email = 'hr@techcorp.vn'
ON DUPLICATE KEY UPDATE company_name = VALUES(company_name), approval_status = VALUES(approval_status);

INSERT INTO jobs (hr_user_id, title, description, department, level, min_salary, max_salary, location, job_type, headcount, deadline_text, status)
SELECT u.id, 'Senior Frontend Developer', 'React, TypeScript, modern UI systems.', 'Kỹ thuật & Công nghệ', 'Senior', 20000000, 30000000, 'Ha Noi', 'Full-time', 2, '31/12/2026', 'published'
FROM users u
WHERE u.email = 'hr@techcorp.vn'
LIMIT 1;

INSERT INTO jobs (hr_user_id, title, description, department, level, min_salary, max_salary, location, job_type, headcount, deadline_text, status)
SELECT u.id, 'Backend Developer (Python)', 'FastAPI, PostgreSQL, async processing.', 'Kỹ thuật & Công nghệ', 'Mid', 18000000, 28000000, 'Ho Chi Minh', 'Full-time', 1, '20/12/2026', 'pending_approval'
FROM users u
WHERE u.email = 'hr@techcorp.vn'
LIMIT 1;
