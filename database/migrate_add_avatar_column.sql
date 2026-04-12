-- Chạy một lần trong MySQL nếu bảng users tạo trước khi có cột avatar:
--   mysql -u ... jobhub < migrate_add_avatar_column.sql

ALTER TABLE users
  ADD COLUMN avatar_storage_key VARCHAR(512) NULL AFTER full_name;
