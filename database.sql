-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types if they don't exist
DO $$ BEGIN
    CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_method AS ENUM ('cash', 'credit-card', 'mobile-money', 'bank-transfer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE gender AS ENUM ('male', 'female', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE relationship_type AS ENUM ('Father', 'Mother', 'Guardian', 'Other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE fee_type AS ENUM ('tuition', 'uniform', 'books', 'transport', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'cashier', 'teacher', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notification_channel AS ENUM ('whatsapp', 'sms', 'email', 'download');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_plan_status AS ENUM ('active', 'completed', 'overdue', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE student_status AS ENUM ('active', 'inactive', 'graduated', 'transferred');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late', 'excused');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE academic_term AS ENUM ('1', '2', '3');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create normalized academic_years table
CREATE TABLE academic_years (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year_name VARCHAR(9) UNIQUE NOT NULL, -- e.g., "2023/2024"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_year_dates CHECK (end_date > start_date)
);

-- Create a function to ensure only one current year
CREATE OR REPLACE FUNCTION ensure_single_current_year()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = true THEN
        UPDATE academic_years 
        SET is_current = false 
        WHERE id != NEW.id AND is_current = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single current year
CREATE TRIGGER enforce_single_current_year
    BEFORE INSERT OR UPDATE ON academic_years
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_current_year();

-- Create normalized academic_terms table
CREATE TABLE academic_terms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    academic_year_id UUID REFERENCES academic_years(id) ON DELETE CASCADE,
    term_number academic_term NOT NULL,
    term_name VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_term_dates CHECK (end_date > start_date),
    CONSTRAINT unique_term_per_year UNIQUE(academic_year_id, term_number)
);

-- Create a function to ensure only one current term
CREATE OR REPLACE FUNCTION ensure_single_current_term()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = true THEN
        UPDATE academic_terms 
        SET is_current = false 
        WHERE id != NEW.id AND is_current = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single current term
CREATE TRIGGER enforce_single_current_term
    BEFORE INSERT OR UPDATE ON academic_terms
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_current_term();

-- Create school_settings table (updated to reference normalized tables)
CREATE TABLE school_settings (
    id SERIAL PRIMARY KEY,
    school_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    logo_url TEXT,
    current_academic_year_id UUID REFERENCES academic_years(id),
    current_academic_term_id UUID REFERENCES academic_terms(id),
    language VARCHAR(2) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'Africa/Lusaka',
    date_format VARCHAR(10) DEFAULT 'DD/MM/YYYY',
    currency VARCHAR(3) DEFAULT 'ZMW',
    email_notifications BOOLEAN DEFAULT true,
    sms_notifications BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table for authentication and authorization
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role user_role NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create user_permissions table for granular access control
CREATE TABLE user_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission_name VARCHAR(100) NOT NULL,
    is_granted BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, permission_name)
);

-- Create students table
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender gender NOT NULL,
    grade VARCHAR(10) NOT NULL,
    section VARCHAR(10),
    status student_status DEFAULT 'active',
    admission_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create parents table
CREATE TABLE parents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    relationship relationship_type NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create parent_accounts table for parent portal access
CREATE TABLE parent_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES parents(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50) UNIQUE,
    password_hash TEXT,
    is_verified BOOLEAN DEFAULT false,
    verification_token TEXT,
    verification_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create parent_student_links table
CREATE TABLE parent_student_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES parents(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    relationship relationship_type NOT NULL,
    is_primary_contact BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parent_id, student_id)
);

-- Create parent_notification_preferences table
CREATE TABLE parent_notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES parents(id) ON DELETE CASCADE,
    channel notification_channel NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parent_id, channel)
);

-- Create fee_types table
CREATE TABLE fee_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    fee_type fee_type NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create student_fees table
CREATE TABLE student_fees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    fee_type_id UUID REFERENCES fee_types(id) ON DELETE CASCADE,
    academic_year_id UUID REFERENCES academic_years(id) ON DELETE CASCADE,
    academic_term_id UUID REFERENCES academic_terms(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    is_paid BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, fee_type_id, academic_year_id, academic_term_id)
);

-- First create the payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_number VARCHAR(20) UNIQUE NOT NULL,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_method payment_method NOT NULL,
    payment_status payment_status DEFAULT 'pending',
    transaction_reference VARCHAR(100),
    payment_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Then create payment_plans table
CREATE TABLE payment_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_fee_id UUID REFERENCES student_fees(id) ON DELETE CASCADE,
    total_amount DECIMAL(10,2) NOT NULL,
    number_of_installments INTEGER NOT NULL,
    status payment_plan_status DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Finally create payment_plan_installments table
CREATE TABLE payment_plan_installments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_plan_id UUID REFERENCES payment_plans(id) ON DELETE CASCADE,
    installment_number INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    is_paid BOOLEAN DEFAULT false,
    payment_id UUID REFERENCES payments(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create payment_allocations table
CREATE TABLE payment_allocations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    student_fee_id UUID REFERENCES student_fees(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create payment_receipts table
CREATE TABLE payment_receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    receipt_number VARCHAR(50) UNIQUE NOT NULL,
    file_url TEXT,
    sent_via notification_channel[],
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create classes table
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(10) NOT NULL,
    section VARCHAR(10),
    academic_year_id UUID REFERENCES academic_years(id) ON DELETE CASCADE,
    academic_term_id UUID REFERENCES academic_terms(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES users(id),
    capacity INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grade, section, academic_year_id, academic_term_id)
);

-- Then create class_registers table
CREATE TABLE class_registers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    academic_year_id UUID REFERENCES academic_years(id) ON DELETE CASCADE,
    academic_term_id UUID REFERENCES academic_terms(id) ON DELETE CASCADE,
    is_enrolled BOOLEAN DEFAULT true,
    enrollment_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, student_id, academic_year_id, academic_term_id)
);

-- Create attendance_records table
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_register_id UUID REFERENCES class_registers(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status attendance_status NOT NULL,
    notes TEXT,
    recorded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create integration_settings table
CREATE TABLE integration_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT false,
    api_key TEXT,
    api_secret TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(integration_name)
);

-- Create integration_logs table
CREATE TABLE integration_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_name VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    request_data JSONB,
    response_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create quickbooks_sync_logs table
CREATE TABLE quickbooks_sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    quickbooks_id VARCHAR(100),
    sync_status VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create report_templates table
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL,
    parameters JSONB,
    created_by UUID REFERENCES users(id),
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create saved_reports table
CREATE TABLE saved_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES report_templates(id),
    name VARCHAR(100) NOT NULL,
    parameters JSONB,
    file_url TEXT,
    generated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create bulk_imports table
CREATE TABLE bulk_imports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    import_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    total_records INTEGER,
    processed_records INTEGER,
    failed_records INTEGER,
    error_log TEXT,
    imported_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create payment_reminders table
CREATE TABLE payment_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_fee_id UUID REFERENCES student_fees(id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL,
    sent_via notification_channel[],
    sent_at TIMESTAMP WITH TIME ZONE,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create backup_logs table
CREATE TABLE backup_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backup_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    file_url TEXT,
    size_bytes BIGINT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_students_student_id ON students(student_id);
CREATE INDEX idx_students_grade ON students(grade);
CREATE INDEX idx_parents_student_id ON parents(id);
CREATE INDEX idx_parent_accounts_email ON parent_accounts(email);
CREATE INDEX idx_parent_accounts_phone ON parent_accounts(phone);
CREATE INDEX idx_parent_student_links_parent_id ON parent_student_links(parent_id);
CREATE INDEX idx_parent_student_links_student_id ON parent_student_links(student_id);
CREATE INDEX idx_student_fees_student_id ON student_fees(student_id);
CREATE INDEX idx_student_fees_fee_type_id ON student_fees(fee_type_id);
CREATE INDEX idx_payments_student_id ON payments(student_id);
CREATE INDEX idx_payments_receipt_number ON payments(receipt_number);
CREATE INDEX idx_payments_payment_status ON payments(payment_status);
CREATE INDEX idx_payment_plans_student_fee_id ON payment_plans(student_fee_id);
CREATE INDEX idx_payment_plan_installments_payment_plan_id ON payment_plan_installments(payment_plan_id);
CREATE INDEX idx_class_registers_class_id ON class_registers(class_id);
CREATE INDEX idx_class_registers_student_id ON class_registers(student_id);
CREATE INDEX idx_attendance_records_class_register_id ON attendance_records(class_register_id);
CREATE INDEX idx_payment_receipts_payment_id ON payment_receipts(payment_id);
CREATE INDEX idx_integration_settings_name ON integration_settings(integration_name);
CREATE INDEX idx_integration_logs_name ON integration_logs(integration_name);
CREATE INDEX idx_quickbooks_sync_logs_entity_type ON quickbooks_sync_logs(entity_type);
CREATE INDEX idx_report_templates_type ON report_templates(template_type);
CREATE INDEX idx_saved_reports_template_id ON saved_reports(template_id);
CREATE INDEX idx_bulk_imports_import_type ON bulk_imports(import_type);
CREATE INDEX idx_payment_reminders_student_fee_id ON payment_reminders(student_fee_id);
CREATE INDEX idx_backup_logs_type ON backup_logs(backup_type);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_school_settings_updated_at
    BEFORE UPDATE ON school_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_permissions_updated_at
    BEFORE UPDATE ON user_permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_students_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parents_updated_at
    BEFORE UPDATE ON parents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parent_accounts_updated_at
    BEFORE UPDATE ON parent_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fee_types_updated_at
    BEFORE UPDATE ON fee_types
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_fees_updated_at
    BEFORE UPDATE ON student_fees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_plans_updated_at
    BEFORE UPDATE ON payment_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_plan_installments_updated_at
    BEFORE UPDATE ON payment_plan_installments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_allocations_updated_at
    BEFORE UPDATE ON payment_allocations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_receipts_updated_at
    BEFORE UPDATE ON payment_receipts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_class_registers_updated_at
    BEFORE UPDATE ON class_registers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_attendance_records_updated_at
    BEFORE UPDATE ON attendance_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integration_settings_updated_at
    BEFORE UPDATE ON integration_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integration_logs_updated_at
    BEFORE UPDATE ON integration_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quickbooks_sync_logs_updated_at
    BEFORE UPDATE ON quickbooks_sync_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_report_templates_updated_at
    BEFORE UPDATE ON report_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classes_updated_at
    BEFORE UPDATE ON classes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE school_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE parents ENABLE ROW LEVEL SECURITY;
ALTER TABLE parent_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE parent_student_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE parent_notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_fees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_plan_installments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_registers ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quickbooks_sync_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE backup_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create basic read policies
CREATE POLICY "Enable read access for all users" ON school_settings FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON users FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON user_permissions FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON students FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON parents FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON parent_accounts FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON parent_student_links FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON parent_notification_preferences FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON fee_types FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON student_fees FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payments FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payment_plans FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payment_plan_installments FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payment_allocations FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payment_receipts FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON class_registers FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON attendance_records FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON integration_settings FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON integration_logs FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON quickbooks_sync_logs FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON report_templates FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON saved_reports FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON bulk_imports FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON payment_reminders FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON backup_logs FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON audit_logs FOR SELECT USING (true);

-- Add new RLS policy for classes
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON classes FOR SELECT USING (true);

-- Add triggers for new academic tables
CREATE TRIGGER update_academic_years_updated_at
    BEFORE UPDATE ON academic_years
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_academic_terms_updated_at
    BEFORE UPDATE ON academic_terms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add additional indexes for normalized foreign keys
CREATE INDEX idx_student_fees_academic_year ON student_fees(academic_year_id);
CREATE INDEX idx_student_fees_academic_term ON student_fees(academic_term_id);
CREATE INDEX idx_classes_academic_year ON classes(academic_year_id);
CREATE INDEX idx_classes_academic_term ON classes(academic_term_id);
CREATE INDEX idx_class_registers_academic_year ON class_registers(academic_year_id);
CREATE INDEX idx_class_registers_academic_term ON class_registers(academic_term_id);
CREATE INDEX idx_academic_terms_academic_year ON academic_terms(academic_year_id);

-- Enable RLS for new tables
ALTER TABLE academic_years ENABLE ROW LEVEL SECURITY;
ALTER TABLE academic_terms ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for new tables
CREATE POLICY "Enable read access for all users" ON academic_years FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON academic_terms FOR SELECT USING (true);

-- Insert default academic year and terms
INSERT INTO academic_years (year_name, start_date, end_date, is_current, is_active) 
VALUES ('2024/2025', '2024-01-01', '2024-12-31', true, true);

-- Insert default terms for the current academic year
INSERT INTO academic_terms (academic_year_id, term_number, term_name, start_date, end_date, is_current, is_active)
SELECT 
    ay.id, 
    '1', 
    'Term 1', 
    '2024-01-15', 
    '2024-04-30', 
    true, 
    true
FROM academic_years ay WHERE ay.year_name = '2024/2025';

INSERT INTO academic_terms (academic_year_id, term_number, term_name, start_date, end_date, is_current, is_active)
SELECT 
    ay.id, 
    '2', 
    'Term 2', 
    '2024-05-01', 
    '2024-08-31', 
    false, 
    true
FROM academic_years ay WHERE ay.year_name = '2024/2025';

INSERT INTO academic_terms (academic_year_id, term_number, term_name, start_date, end_date, is_current, is_active)
SELECT 
    ay.id, 
    '3', 
    'Term 3', 
    '2024-09-01', 
    '2024-12-15', 
    false, 
    true
FROM academic_years ay WHERE ay.year_name = '2024/2025';

-- Update school_settings to reference the current academic year and term
UPDATE school_settings 
SET 
    current_academic_year_id = (SELECT id FROM academic_years WHERE is_current = true LIMIT 1),
    current_academic_term_id = (SELECT id FROM academic_terms WHERE is_current = true LIMIT 1)
WHERE id = 1;

-- Add indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_payment_status ON payments(payment_status);
CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_students_grade ON students(grade);
CREATE INDEX IF NOT EXISTS idx_student_fees_is_paid ON student_fees(is_paid);
CREATE INDEX IF NOT EXISTS idx_student_fees_due_date ON student_fees(due_date);
CREATE INDEX IF NOT EXISTS idx_payment_receipts_payment_id ON payment_receipts(payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment_id ON payment_allocations(payment_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_payments_date_status ON payments(payment_date, payment_status);
CREATE INDEX IF NOT EXISTS idx_students_grade_status ON students(grade, status);
CREATE INDEX IF NOT EXISTS idx_student_fees_student_paid ON student_fees(student_id, is_paid);