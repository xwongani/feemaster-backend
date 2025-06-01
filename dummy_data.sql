-- Insert dummy data for school settings
INSERT INTO school_settings (school_name, email, phone, address, logo_url, language, timezone, date_format, currency)
VALUES (
    'SchPay Academy',
    'admin@schpay.edu',
    '+260 977 123456',
    '123 Education Street, Lusaka, Zambia',
    'https://storage.schpay.edu/logos/school_logo.png',
    'en',
    'Africa/Lusaka',
    'DD/MM/YYYY',
    'ZMW'
);

-- Insert dummy users (passwords are hashed versions of 'password123')
INSERT INTO users (id, email, password_hash, first_name, last_name, role, is_active) VALUES
('11111111-1111-1111-1111-111111111111', 'admin@schpay.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBAQHxQxJ5KQHy', 'Admin', 'User', 'admin', true),
('22222222-2222-2222-2222-222222222222', 'cashier@schpay.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBAQHxQxJ5KQHy', 'John', 'Cashier', 'cashier', true),
('33333333-3333-3333-3333-333333333333', 'teacher@schpay.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBAQHxQxJ5KQHy', 'Mary', 'Teacher', 'teacher', true);

-- Insert dummy students
INSERT INTO students (id, student_id, first_name, last_name, date_of_birth, gender, grade, section, status, admission_date) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'STU-2024-001', 'James', 'Banda', '2010-05-15', 'male', 'Grade 8', 'A', 'active', '2024-01-10'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'STU-2024-002', 'Chisha', 'Mwanza', '2011-03-20', 'female', 'Grade 7', 'B', 'active', '2024-01-10'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', 'STU-2024-003', 'Tiwonge', 'Phiri', '2010-11-08', 'male', 'Grade 8', 'A', 'active', '2024-01-10'),
('dddddddd-dddd-dddd-dddd-dddddddddddd', 'STU-2024-004', 'Mulenga', 'Ngoma', '2011-07-25', 'female', 'Grade 7', 'B', 'active', '2024-01-10'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'STU-2024-005', 'Mwamba', 'Kunda', '2010-09-30', 'male', 'Grade 8', 'A', 'active', '2024-01-10');

-- Insert dummy parents
INSERT INTO parents (id, first_name, last_name, relationship, phone, email, address) VALUES
('11111111-1111-1111-1111-111111111111', 'Peter', 'Banda', 'Father', '+260 977 111111', 'peter.banda@email.com', '456 Parent Street, Lusaka'),
('22222222-2222-2222-2222-222222222222', 'Grace', 'Mwanza', 'Mother', '+260 977 222222', 'grace.mwanza@email.com', '789 Family Road, Lusaka'),
('33333333-3333-3333-3333-333333333333', 'David', 'Phiri', 'Father', '+260 977 333333', 'david.phiri@email.com', '321 Home Avenue, Lusaka'),
('44444444-4444-4444-4444-444444444444', 'Ruth', 'Ngoma', 'Mother', '+260 977 444444', 'ruth.ngoma@email.com', '654 Parent Lane, Lusaka'),
('55555555-5555-5555-5555-555555555555', 'Michael', 'Kunda', 'Father', '+260 977 555555', 'michael.kunda@email.com', '987 Family Circle, Lusaka');

-- Link parents to students
INSERT INTO parent_student_links (parent_id, student_id, relationship, is_primary_contact) VALUES
('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Father', true),
('22222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Mother', true),
('33333333-3333-3333-3333-333333333333', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'Father', true),
('44444444-4444-4444-4444-444444444444', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'Mother', true),
('55555555-5555-5555-5555-555555555555', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Father', true);

-- Insert fee types
INSERT INTO fee_types (id, name, description, fee_type, amount, is_active) VALUES
('ffffffff-ffff-ffff-ffff-ffffffffffff', 'Term 1 Tuition', 'Term 1 Tuition Fee', 'tuition', 5000.00, true),
('11111111-1111-1111-1111-111111111111', 'Term 1 Uniform', 'School Uniform Fee', 'uniform', 1200.00, true),
('22222222-2222-2222-2222-222222222222', 'Term 1 Books', 'Textbooks and Stationery', 'books', 800.00, true),
('33333333-3333-3333-3333-333333333333', 'Term 1 Transport', 'School Bus Transportation', 'transport', 1500.00, true),
('44444444-4444-4444-4444-444444444444', 'Term 1 Other', 'Miscellaneous Fees', 'other', 500.00, true);

-- Insert student fees for current term
INSERT INTO student_fees (student_id, fee_type_id, academic_year_id, academic_term_id, amount, due_date, is_paid)
SELECT 
    s.id,
    ft.id,
    ay.id,
    at.id,
    ft.amount,
    '2024-02-15',
    false
FROM students s
CROSS JOIN fee_types ft
CROSS JOIN academic_years ay
CROSS JOIN academic_terms at
WHERE ay.is_current = true AND at.is_current = true;

-- Insert some payments
INSERT INTO payments (receipt_number, student_id, amount, payment_method, payment_status, transaction_reference, payment_date, notes) VALUES
('REC-2024-001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 5000.00, 'cash', 'completed', 'TRX-001', '2024-01-20 10:00:00', 'Term 1 Tuition Payment'),
('REC-2024-002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 5000.00, 'mobile-money', 'completed', 'TRX-002', '2024-01-21 11:30:00', 'Term 1 Tuition Payment'),
('REC-2024-003', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 5000.00, 'bank-transfer', 'completed', 'TRX-003', '2024-01-22 14:15:00', 'Term 1 Tuition Payment'),
('REC-2024-004', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 5000.00, 'credit-card', 'pending', 'TRX-004', '2024-01-23 09:45:00', 'Term 1 Tuition Payment'),
('REC-2024-005', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 5000.00, 'mobile-money', 'failed', 'TRX-005', '2024-01-24 16:20:00', 'Term 1 Tuition Payment');

-- Insert payment allocations
INSERT INTO payment_allocations (payment_id, student_fee_id, amount)
SELECT 
    p.id,
    sf.id,
    p.amount
FROM payments p
JOIN student_fees sf ON p.student_id = sf.student_id
WHERE sf.fee_type_id = 'ffffffff-ffff-ffff-ffff-ffffffffffff'; -- Tuition fee type

-- Insert payment receipts
INSERT INTO payment_receipts (payment_id, receipt_number, file_url, sent_via, sent_at)
SELECT 
    id,
    receipt_number,
    'https://storage.schpay.edu/receipts/' || receipt_number || '.pdf',
    ARRAY['email'::notification_channel, 'download'::notification_channel],
    payment_date
FROM payments
WHERE payment_status = 'completed';

-- Insert classes
INSERT INTO classes (name, grade, section, academic_year_id, academic_term_id, teacher_id, capacity, is_active)
SELECT 
    'Grade 8A',
    'Grade 8',
    'A',
    ay.id,
    at.id,
    '33333333-3333-3333-3333-333333333333',
    30,
    true
FROM academic_years ay
CROSS JOIN academic_terms at
WHERE ay.is_current = true AND at.is_current = true;

INSERT INTO classes (name, grade, section, academic_year_id, academic_term_id, teacher_id, capacity, is_active)
SELECT 
    'Grade 7B',
    'Grade 7',
    'B',
    ay.id,
    at.id,
    '33333333-3333-3333-3333-333333333333',
    30,
    true
FROM academic_years ay
CROSS JOIN academic_terms at
WHERE ay.is_current = true AND at.is_current = true;

-- Insert class registers
INSERT INTO class_registers (class_id, student_id, academic_year_id, academic_term_id, is_enrolled, enrollment_date)
SELECT 
    c.id,
    s.id,
    ay.id,
    at.id,
    true,
    '2024-01-10'
FROM classes c
JOIN students s ON c.grade = s.grade AND c.section = s.section
CROSS JOIN academic_years ay
CROSS JOIN academic_terms at
WHERE ay.is_current = true AND at.is_current = true;

-- Insert attendance records
INSERT INTO attendance_records (class_register_id, date, status, recorded_by)
SELECT 
    cr.id,
    CURRENT_DATE,
    'present',
    '33333333-3333-3333-3333-333333333333'
FROM class_registers cr;

-- Insert integration settings
INSERT INTO integration_settings (integration_name, is_enabled, api_key, api_secret, settings)
VALUES 
('quickbooks', true, 'test_api_key', 'test_api_secret', '{"company_id": "123", "environment": "sandbox"}'),
('sms_gateway', true, 'test_sms_key', 'test_sms_secret', '{"provider": "twilio", "from_number": "+260977000000"}'),
('email_service', true, 'test_email_key', 'test_email_secret', '{"provider": "sendgrid", "from_email": "noreply@schpay.edu"}');

-- Insert report templates
INSERT INTO report_templates (name, description, template_type, parameters, created_by, is_public)
VALUES 
('Payment Summary', 'Summary of all payments for a period', 'payment_report', '{"date_range": true, "payment_type": true}', '11111111-1111-1111-1111-111111111111', true),
('Student Balance', 'Current balance for all students', 'balance_report', '{"grade": true, "section": true}', '11111111-1111-1111-1111-111111111111', true),
('Attendance Summary', 'Summary of student attendance', 'attendance_report', '{"date_range": true, "class": true}', '11111111-1111-1111-1111-111111111111', true);

-- Insert saved reports
INSERT INTO saved_reports (template_id, name, parameters, file_url, generated_by)
SELECT 
    id,
    'Payment Summary - January 2024',
    '{"start_date": "2024-01-01", "end_date": "2024-01-31"}',
    'https://storage.schpay.edu/reports/payment_summary_jan2024.pdf',
    '11111111-1111-1111-1111-111111111111'
FROM report_templates
WHERE template_type = 'payment_report';

-- Insert payment reminders
INSERT INTO payment_reminders (student_fee_id, reminder_type, due_date, status, sent_via, sent_at, message)
SELECT 
    sf.id,
    'payment_due',
    sf.due_date,
    'sent',
    ARRAY['email'::notification_channel, 'sms'::notification_channel],
    CURRENT_TIMESTAMP,
    'Reminder: Your payment of ' || sf.amount || ' is due on ' || sf.due_date
FROM student_fees sf
WHERE sf.is_paid = false;

-- Insert audit logs
INSERT INTO audit_logs (user_id, action, table_name, record_id, old_data, new_data)
VALUES 
('11111111-1111-1111-1111-111111111111', 'CREATE', 'payments', '00000000-0000-0000-0000-000000000001', NULL, '{"amount": 5000.00, "status": "completed"}'),
('22222222-2222-2222-2222-222222222222', 'UPDATE', 'students', '00000000-0000-0000-0000-000000000001', '{"grade": "Grade 7"}', '{"grade": "Grade 8"}'),
('33333333-3333-3333-3333-333333333333', 'DELETE', 'fee_types', '00000000-0000-0000-0000-000000000001', '{"name": "Old Fee"}', NULL);

-- Insert backup logs
INSERT INTO backup_logs (backup_type, status, file_url, size_bytes, started_at, completed_at)
VALUES 
('full', 'completed', 'https://storage.schpay.edu/backups/full_20240101.zip', 1048576, '2024-01-01 00:00:00', '2024-01-01 00:05:00'),
('incremental', 'completed', 'https://storage.schpay.edu/backups/incremental_20240102.zip', 524288, '2024-01-02 00:00:00', '2024-01-02 00:02:00');

-- Insert bulk imports
INSERT INTO bulk_imports (import_type, file_name, status, total_records, processed_records, failed_records, imported_by)
VALUES 
('students', 'students_jan2024.csv', 'completed', 100, 98, 2, '11111111-1111-1111-1111-111111111111'),
('fees', 'fees_jan2024.csv', 'completed', 50, 50, 0, '11111111-1111-1111-1111-111111111111');

-- Insert integration logs
INSERT INTO integration_logs (integration_name, action, status, request_data, response_data)
VALUES 
('quickbooks', 'sync_payments', 'success', '{"payment_ids": [1,2,3]}', '{"synced": true}'),
('sms_gateway', 'send_reminder', 'success', '{"phone": "+260977111111", "message": "Payment due"}', '{"message_id": "msg123"}');

-- Insert quickbooks sync logs
INSERT INTO quickbooks_sync_logs (entity_type, entity_id, quickbooks_id, sync_status)
VALUES 
('payment', '00000000-0000-0000-0000-000000000001', 'QB123', 'synced'),
('payment', '00000000-0000-0000-0000-000000000002', 'QB124', 'synced'); 