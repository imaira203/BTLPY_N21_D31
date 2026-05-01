-- Seed data x10 for JobHub schema
-- Default credentials:
--   - admin users:    admin123
--   - hr/candidate:   zzxxcc123
--
-- Generated bcrypt hashes:
--   zzxxcc123 -> $2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.
--   admin123  -> $2b$12$jKxCgKcz59BalFcRYRROJ.0u7m4BX0TFmbjTVEW40StA7ci84m4i2

SET FOREIGN_KEY_CHECKS = 0;

-- Use DELETE instead of TRUNCATE because MySQL can reject TRUNCATE
-- on FK-referenced tables even when FOREIGN_KEY_CHECKS=0.
DELETE FROM profile_views;
DELETE FROM invoices;
DELETE FROM candidate_saved_jobs;
DELETE FROM job_applications;
DELETE FROM cv_documents;
DELETE FROM candidate_subscriptions;
DELETE FROM candidate_profiles;
DELETE FROM jobs;
DELETE FROM hr_profiles;
DELETE FROM users;

SET FOREIGN_KEY_CHECKS = 1;

-- USERS (1 admin + 10 HR + 10 candidates)
INSERT INTO users (id, email, password_hash, full_name, avatar_storage_key, role, is_active, created_at) VALUES
(1,  'admin@jobhub.local', '$2b$12$jKxCgKcz59BalFcRYRROJ.0u7m4BX0TFmbjTVEW40StA7ci84m4i2', 'System Admin', NULL, 'admin', 1, NOW()),
(2,  'hr01@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 01', NULL, 'hr', 1, NOW()),
(3,  'hr02@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 02', NULL, 'hr', 1, NOW()),
(4,  'hr03@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 03', NULL, 'hr', 1, NOW()),
(5,  'hr04@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 04', NULL, 'hr', 1, NOW()),
(6,  'hr05@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 05', NULL, 'hr', 1, NOW()),
(7,  'hr06@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 06', NULL, 'hr', 1, NOW()),
(8,  'hr07@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 07', NULL, 'hr', 1, NOW()),
(9,  'hr08@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 08', NULL, 'hr', 1, NOW()),
(10, 'hr09@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 09', NULL, 'hr', 1, NOW()),
(11, 'hr10@company.local',  '$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.', 'HR User 10', NULL, 'hr', 1, NOW()),
(12, 'candidate01@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 01', NULL, 'candidate', 1, NOW()),
(13, 'candidate02@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 02', NULL, 'candidate', 1, NOW()),
(14, 'candidate03@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 03', NULL, 'candidate', 1, NOW()),
(15, 'candidate04@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 04', NULL, 'candidate', 1, NOW()),
(16, 'candidate05@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 05', NULL, 'candidate', 1, NOW()),
(17, 'candidate06@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 06', NULL, 'candidate', 1, NOW()),
(18, 'candidate07@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 07', NULL, 'candidate', 1, NOW()),
(19, 'candidate08@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 08', NULL, 'candidate', 1, NOW()),
(20, 'candidate09@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 09', NULL, 'candidate', 1, NOW()),
(21, 'candidate10@job.local','$2b$12$EdUG2tH8dhwWPzV6p09V..XpGOJ2dT.QulKn3bpRGaaO2/9iq8J7.','Candidate 10', NULL, 'candidate', 1, NOW());

-- HR PROFILES (10)
INSERT INTO hr_profiles (id, user_id, company_name, avatar_storage_key, contact_phone, company_description, approval_status, admin_note, created_at) VALUES
(1, 2,  'TechCorp 01', NULL, '0901000001', 'Company profile 01', 'approved', NULL, NOW()),
(2, 3,  'TechCorp 02', NULL, '0901000002', 'Company profile 02', 'approved', NULL, NOW()),
(3, 4,  'TechCorp 03', NULL, '0901000003', 'Company profile 03', 'approved', NULL, NOW()),
(4, 5,  'TechCorp 04', NULL, '0901000004', 'Company profile 04', 'pending',  NULL, NOW()),
(5, 6,  'TechCorp 05', NULL, '0901000005', 'Company profile 05', 'approved', NULL, NOW()),
(6, 7,  'TechCorp 06', NULL, '0901000006', 'Company profile 06', 'approved', NULL, NOW()),
(7, 8,  'TechCorp 07', NULL, '0901000007', 'Company profile 07', 'rejected', 'Need more docs', NOW()),
(8, 9,  'TechCorp 08', NULL, '0901000008', 'Company profile 08', 'approved', NULL, NOW()),
(9, 10, 'TechCorp 09', NULL, '0901000009', 'Company profile 09', 'approved', NULL, NOW()),
(10,11, 'TechCorp 10', NULL, '0901000010', 'Company profile 10', 'approved', NULL, NOW());

-- CANDIDATE PROFILES (10)
INSERT INTO candidate_profiles (id, user_id, tagline, phone, address, professional_field, degree, experience_text, language, skills_json, updated_at) VALUES
(1, 12, 'Open to work', '0912000001', 'Ha Noi',       'Frontend', 'Bachelor', '2 years', 'EN', '{"Frontend":["React","Vue"],"Backend":["FastAPI"]}', NOW()),
(2, 13, 'Open to work', '0912000002', 'Ho Chi Minh',  'Backend',  'Bachelor', '3 years', 'EN', '{"Backend":["NodeJS","FastAPI"],"DB":["MySQL"]}', NOW()),
(3, 14, 'Open to work', '0912000003', 'Da Nang',      'Data',     'Bachelor', '1 year',  'EN', '{"Data":["Python","Pandas"],"BI":["PowerBI"]}', NOW()),
(4, 15, 'Open to work', '0912000004', 'Ha Noi',       'QA',       'College',  '4 years', 'EN', '{"QA":["Manual","Automation"],"Tools":["Selenium"]}', NOW()),
(5, 16, 'Open to work', '0912000005', 'Can Tho',      'DevOps',   'Bachelor', '2 years', 'EN', '{"DevOps":["Docker","CI/CD"],"Cloud":["AWS"]}', NOW()),
(6, 17, 'Open to work', '0912000006', 'Hai Phong',    'Mobile',   'Bachelor', '3 years', 'EN', '{"Mobile":["Flutter","Kotlin"],"API":["REST"]}', NOW()),
(7, 18, 'Open to work', '0912000007', 'Nha Trang',    'UI/UX',    'Bachelor', '2 years', 'EN', '{"Design":["Figma","Adobe XD"]}', NOW()),
(8, 19, 'Open to work', '0912000008', 'Hue',          'PM',       'Master',   '5 years', 'EN', '{"PM":["Agile","Scrum"],"Docs":["Jira"]}', NOW()),
(9, 20, 'Open to work', '0912000009', 'Vung Tau',     'Security', 'Bachelor', '2 years', 'EN', '{"Security":["OWASP","SIEM"]}', NOW()),
(10,21, 'Open to work', '0912000010', 'Ha Noi',       'Fullstack','Bachelor', '4 years', 'EN', '{"Frontend":["React"],"Backend":["Django","FastAPI"]}', NOW());

-- CANDIDATE SUBSCRIPTIONS (10)
INSERT INTO candidate_subscriptions (id, candidate_id, status, pro_expires_at, updated_at) VALUES
(1, 12, 'active',   DATE_ADD(NOW(), INTERVAL 60 DAY), NOW()),
(2, 13, 'inactive', NULL, NOW()),
(3, 14, 'active',   DATE_ADD(NOW(), INTERVAL 30 DAY), NOW()),
(4, 15, 'expired',  DATE_SUB(NOW(), INTERVAL 10 DAY), NOW()),
(5, 16, 'inactive', NULL, NOW()),
(6, 17, 'active',   DATE_ADD(NOW(), INTERVAL 90 DAY), NOW()),
(7, 18, 'inactive', NULL, NOW()),
(8, 19, 'active',   DATE_ADD(NOW(), INTERVAL 15 DAY), NOW()),
(9, 20, 'inactive', NULL, NOW()),
(10,21, 'active',   DATE_ADD(NOW(), INTERVAL 45 DAY), NOW());

-- JOBS (10)
INSERT INTO jobs (id, hr_user_id, title, description, department, level, min_salary, max_salary, location, job_type, headcount, deadline_text, view_count, status, admin_note, created_at, updated_at) VALUES
(1, 2,  'Frontend Developer 01', 'React + TS',        'Engineering', 'Junior', 12000000, 18000000, 'Ha Noi',      'Full-time', 2, '30/06/2026', 120, 'published', NULL, NOW(), NOW()),
(2, 3,  'Backend Developer 02',  'FastAPI + MySQL',   'Engineering', 'Mid',    18000000, 26000000, 'Ho Chi Minh', 'Full-time', 1, '15/07/2026',  95, 'published', NULL, NOW(), NOW()),
(3, 4,  'Data Analyst 03',       'SQL + BI',          'Data',        'Junior', 13000000, 20000000, 'Da Nang',     'Hybrid',    1, '25/06/2026',  70, 'pending_approval', NULL, NOW(), NOW()),
(4, 5,  'QA Engineer 04',        'Manual + Auto',     'QA',          'Mid',    15000000, 22000000, 'Ha Noi',      'Full-time', 2, '10/07/2026',  40, 'draft', NULL, NOW(), NOW()),
(5, 6,  'DevOps Engineer 05',    'Docker + CI/CD',    'Infrastructure','Mid',  22000000, 32000000, 'Can Tho',     'Remote',    1, '20/07/2026',  88, 'published', NULL, NOW(), NOW()),
(6, 7,  'Mobile Developer 06',   'Flutter',           'Engineering', 'Junior', 14000000, 21000000, 'Hai Phong',   'Hybrid',    2, '12/07/2026',  62, 'rejected', 'Need more detail', NOW(), NOW()),
(7, 8,  'UI UX Designer 07',     'Figma + UX',        'Design',      'Junior', 12000000, 19000000, 'Nha Trang',   'Full-time', 1, '28/06/2026',  54, 'published', NULL, NOW(), NOW()),
(8, 9,  'Project Manager 08',    'Agile Scrum',       'Management',  'Senior', 25000000, 38000000, 'Hue',         'Full-time', 1, '18/07/2026',  33, 'closed', NULL, NOW(), NOW()),
(9, 10, 'Security Engineer 09',  'AppSec',            'Security',    'Mid',    21000000, 30000000, 'Vung Tau',    'Remote',    1, '22/07/2026',  25, 'published', NULL, NOW(), NOW()),
(10,11, 'Fullstack Engineer 10', 'React + FastAPI',   'Engineering', 'Senior', 26000000, 40000000, 'Ha Noi',      'Hybrid',    2, '30/07/2026', 110, 'published', NULL, NOW(), NOW());

-- CV DOCUMENTS (10)
INSERT INTO cv_documents (id, user_id, original_name, stored_filename, mime_type, created_at) VALUES
(1, 12, 'CV_Candidate_01.pdf', 'cvs/12_cv_01.pdf', 'application/pdf', NOW()),
(2, 13, 'CV_Candidate_02.pdf', 'cvs/13_cv_02.pdf', 'application/pdf', NOW()),
(3, 14, 'CV_Candidate_03.pdf', 'cvs/14_cv_03.pdf', 'application/pdf', NOW()),
(4, 15, 'CV_Candidate_04.pdf', 'cvs/15_cv_04.pdf', 'application/pdf', NOW()),
(5, 16, 'CV_Candidate_05.pdf', 'cvs/16_cv_05.pdf', 'application/pdf', NOW()),
(6, 17, 'CV_Candidate_06.pdf', 'cvs/17_cv_06.pdf', 'application/pdf', NOW()),
(7, 18, 'CV_Candidate_07.pdf', 'cvs/18_cv_07.pdf', 'application/pdf', NOW()),
(8, 19, 'CV_Candidate_08.pdf', 'cvs/19_cv_08.pdf', 'application/pdf', NOW()),
(9, 20, 'CV_Candidate_09.pdf', 'cvs/20_cv_09.pdf', 'application/pdf', NOW()),
(10,21, 'CV_Candidate_10.pdf', 'cvs/21_cv_10.pdf', 'application/pdf', NOW());

-- JOB APPLICATIONS (10)
INSERT INTO job_applications (id, job_id, candidate_id, cv_id, status, accepted_at, contact_unlocked_at, created_at) VALUES
(1,  1, 12, 1,  'pending',  NULL, NULL, NOW()),
(2,  2, 13, 2,  'reviewed', NULL, NULL, NOW()),
(3,  5, 14, 3,  'approved', NOW(), NOW(), NOW()),
(4,  7, 15, 4,  'pending',  NULL, NULL, NOW()),
(5,  9, 16, 5,  'rejected', NULL, NULL, NOW()),
(6, 10, 17, 6,  'approved', NOW(), NOW(), NOW()),
(7,  1, 18, 7,  'reviewed', NULL, NULL, NOW()),
(8,  2, 19, 8,  'pending',  NULL, NULL, NOW()),
(9,  7, 20, 9,  'approved', NOW(), NULL, NOW()),
(10,10, 21, 10, 'pending',  NULL, NULL, NOW());

-- CANDIDATE SAVED JOBS (10)
INSERT INTO candidate_saved_jobs (id, candidate_id, job_id, created_at) VALUES
(1, 12, 2, NOW()),
(2, 13, 1, NOW()),
(3, 14, 5, NOW()),
(4, 15, 7, NOW()),
(5, 16, 9, NOW()),
(6, 17,10, NOW()),
(7, 18, 1, NOW()),
(8, 19, 2, NOW()),
(9, 20, 7, NOW()),
(10,21,10, NOW());

-- INVOICES (10)
INSERT INTO invoices (id, owner_user_id, invoice_type, status, amount, currency, due_at, sepay_order_code, sepay_payment_url, note, created_at, paid_at, application_id) VALUES
(1, 12, 'pro_upgrade',              'paid',    199000.00, 'VND', DATE_ADD(NOW(), INTERVAL 15 DAY), 'INV-PRO-0001', 'https://sepay.vn/pay/INV-PRO-0001', 'Upgrade PRO 1 month', NOW(), NOW(), NULL),
(2, 13, 'pro_upgrade',              'pending', 199000.00, 'VND', DATE_ADD(NOW(), INTERVAL 15 DAY), 'INV-PRO-0002', 'https://sepay.vn/pay/INV-PRO-0002', 'Upgrade PRO 1 month', NOW(), NULL, NULL),
(3, 2,  'candidate_contact_unlock', 'paid',   2500000.00, 'VND', DATE_ADD(NOW(), INTERVAL 7 DAY),  'INV-HR-0001',  'https://sepay.vn/pay/INV-HR-0001',  'Recruitment cycle 06/2026', NOW(), NOW(), 3),
(4, 3,  'candidate_contact_unlock', 'pending',1800000.00, 'VND', DATE_ADD(NOW(), INTERVAL 7 DAY),  'INV-HR-0002',  'https://sepay.vn/pay/INV-HR-0002',  'Recruitment cycle 06/2026', NOW(), NULL, 6),
(5, 14, 'pro_upgrade',              'paid',    398000.00, 'VND', DATE_ADD(NOW(), INTERVAL 30 DAY), 'INV-PRO-0003', 'https://sepay.vn/pay/INV-PRO-0003', 'Upgrade PRO 2 months', NOW(), NOW(), NULL),
(6, 15, 'pro_upgrade',              'cancelled',199000.00,'VND', DATE_ADD(NOW(), INTERVAL 15 DAY), 'INV-PRO-0004', 'https://sepay.vn/pay/INV-PRO-0004', 'Upgrade cancelled', NOW(), NULL, NULL),
(7, 4,  'candidate_contact_unlock', 'overdue', 900000.00, 'VND', DATE_SUB(NOW(), INTERVAL 3 DAY),  'INV-HR-0003',  'https://sepay.vn/pay/INV-HR-0003',  'Recruitment cycle 05/2026', NOW(), NULL, 9),
(8, 16, 'pro_upgrade',              'pending', 199000.00, 'VND', DATE_ADD(NOW(), INTERVAL 20 DAY), 'INV-PRO-0005', 'https://sepay.vn/pay/INV-PRO-0005', 'Upgrade PRO 1 month', NOW(), NULL, NULL),
(9, 5,  'candidate_contact_unlock', 'paid',   1200000.00, 'VND', DATE_ADD(NOW(), INTERVAL 5 DAY),  'INV-HR-0004',  'https://sepay.vn/pay/INV-HR-0004',  'Recruitment cycle 06/2026', NOW(), NOW(), 3),
(10,17, 'pro_upgrade',              'paid',    199000.00, 'VND', DATE_ADD(NOW(), INTERVAL 25 DAY), 'INV-PRO-0006', 'https://sepay.vn/pay/INV-PRO-0006', 'Upgrade PRO 1 month', NOW(), NOW(), NULL);

-- PROFILE VIEWS (unique viewer-viewed pairs)
INSERT INTO profile_views (id, viewer_user_id, viewed_user_id, viewed_at) VALUES
(1, 2, 14, NOW()),
(2, 3, 17, NOW()),
(3, 4, 20, NOW()),
(4, 2, 12, NOW()),
(5, 3, 13, NOW()),
(6, 8, 15, NOW()),
(7, 10,16, NOW()),
(8, 2, 18, NOW()),
(9, 3, 19, NOW()),
(10,11,21, NOW());

-- Keep auto increment consistent
ALTER TABLE users AUTO_INCREMENT = 22;
ALTER TABLE hr_profiles AUTO_INCREMENT = 11;
ALTER TABLE candidate_profiles AUTO_INCREMENT = 11;
ALTER TABLE candidate_subscriptions AUTO_INCREMENT = 11;
ALTER TABLE jobs AUTO_INCREMENT = 11;
ALTER TABLE cv_documents AUTO_INCREMENT = 11;
ALTER TABLE job_applications AUTO_INCREMENT = 11;
ALTER TABLE candidate_saved_jobs AUTO_INCREMENT = 11;
ALTER TABLE invoices AUTO_INCREMENT = 11;
ALTER TABLE profile_views AUTO_INCREMENT = 11;
