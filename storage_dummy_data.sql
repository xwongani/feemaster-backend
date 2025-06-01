-- Insert dummy data for logos bucket (max 5MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('logos', 'main/logo.png', auth.uid(), '{"mimetype": "image/png", "size": 1024, "width": 200, "height": 200}'),
('logos', 'main/banner.jpg', auth.uid(), '{"mimetype": "image/jpeg", "size": 2048, "width": 1200, "height": 400}'),
('logos', 'icons/favicon.png', auth.uid(), '{"mimetype": "image/png", "size": 512, "width": 32, "height": 32}'),
('logos', 'icons/apple-touch-icon.png', auth.uid(), '{"mimetype": "image/png", "size": 1024, "width": 180, "height": 180}');

-- Insert dummy data for receipts bucket (max 10MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('receipts', '2024/01/REC-2024-001.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('receipts', '2024/01/REC-2024-002.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('receipts', '2024/02/REC-2024-003.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('receipts', '2024/02/REC-2024-004.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('receipts', '2024/03/REC-2024-005.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}');

-- Insert dummy data for reports bucket (max 20MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('reports', 'payments/2024/01/summary.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 4096, "sheets": 3}'),
('reports', 'payments/2024/02/summary.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 4096, "sheets": 3}'),
('reports', 'attendance/2024/01/summary.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 5120, "sheets": 2}'),
('reports', 'attendance/2024/02/summary.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 5120, "sheets": 2}'),
('reports', 'monthly/2024/01/report.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 3072, "pages": 5}'),
('reports', 'monthly/2024/02/report.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 4096, "pages": 8}');

-- Insert dummy data for backups bucket (max 100MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('backups', '2024/01/full_backup_20240101.zip', auth.uid(), '{"mimetype": "application/zip", "size": 52428800, "compressed": true}'),
('backups', '2024/01/incremental_backup_20240102.zip', auth.uid(), '{"mimetype": "application/zip", "size": 26214400, "compressed": true}'),
('backups', '2024/02/full_backup_20240201.zip', auth.uid(), '{"mimetype": "application/zip", "size": 52428800, "compressed": true}');

-- Insert dummy data for imports bucket (max 50MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('imports', 'students/2024/01/import.csv', auth.uid(), '{"mimetype": "text/csv", "size": 1024, "rows": 100}'),
('imports', 'students/2024/02/import.csv', auth.uid(), '{"mimetype": "text/csv", "size": 1024, "rows": 100}'),
('imports', 'fees/2024/01/import.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 2048, "sheets": 1}'),
('imports', 'fees/2024/02/import.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 2048, "sheets": 1}');

-- Insert dummy data for attachments bucket (max 15MB)
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('attachments', 'students/STU-2024-001/id_photo.jpg', auth.uid(), '{"mimetype": "image/jpeg", "size": 2048, "width": 400, "height": 400}'),
('attachments', 'students/STU-2024-001/birth_certificate.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('attachments', 'students/STU-2024-002/id_photo.jpg', auth.uid(), '{"mimetype": "image/jpeg", "size": 2048, "width": 400, "height": 400}'),
('attachments', 'students/STU-2024-002/birth_certificate.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048, "pages": 1}'),
('attachments', 'documents/consent_form.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 3072, "pages": 2}'),
('attachments', 'documents/medical_certificate.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 4096, "pages": 1}'),
('attachments', 'documents/transfer_letter.docx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "size": 2048, "pages": 1}'); 