-- Create storage buckets for different types of files
INSERT INTO storage.buckets (id, name, public) VALUES
('receipts', 'receipts', false),
('reports', 'reports', false),
('logos', 'logos', true),
('backups', 'backups', false),
('imports', 'imports', false),
('attachments', 'attachments', false);

-- Set up storage policies for receipts bucket
CREATE POLICY "Receipts are viewable by authenticated users"
ON storage.objects FOR SELECT
USING (bucket_id = 'receipts' AND auth.role() = 'authenticated');

CREATE POLICY "Receipts are insertable by authenticated users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'receipts' AND auth.role() = 'authenticated');

CREATE POLICY "Receipts are updatable by authenticated users"
ON storage.objects FOR UPDATE
USING (bucket_id = 'receipts' AND auth.role() = 'authenticated');

-- Set up storage policies for reports bucket
CREATE POLICY "Reports are viewable by authenticated users"
ON storage.objects FOR SELECT
USING (bucket_id = 'reports' AND auth.role() = 'authenticated');

CREATE POLICY "Reports are insertable by authenticated users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'reports' AND auth.role() = 'authenticated');

CREATE POLICY "Reports are updatable by authenticated users"
ON storage.objects FOR UPDATE
USING (bucket_id = 'reports' AND auth.role() = 'authenticated');

-- Set up storage policies for logos bucket (public)
CREATE POLICY "Logos are viewable by everyone"
ON storage.objects FOR SELECT
USING (bucket_id = 'logos');

CREATE POLICY "Logos are insertable by authenticated users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'logos' AND auth.role() = 'authenticated');

CREATE POLICY "Logos are updatable by authenticated users"
ON storage.objects FOR UPDATE
USING (bucket_id = 'logos' AND auth.role() = 'authenticated');

-- Set up storage policies for backups bucket
CREATE POLICY "Backups are viewable by admin users"
ON storage.objects FOR SELECT
USING (bucket_id = 'backups' AND auth.role() = 'authenticated' AND auth.jwt() ->> 'role' = 'admin');

CREATE POLICY "Backups are insertable by admin users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'backups' AND auth.role() = 'authenticated' AND auth.jwt() ->> 'role' = 'admin');

-- Set up storage policies for imports bucket
CREATE POLICY "Imports are viewable by authenticated users"
ON storage.objects FOR SELECT
USING (bucket_id = 'imports' AND auth.role() = 'authenticated');

CREATE POLICY "Imports are insertable by authenticated users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'imports' AND auth.role() = 'authenticated');

-- Set up storage policies for attachments bucket
CREATE POLICY "Attachments are viewable by authenticated users"
ON storage.objects FOR SELECT
USING (bucket_id = 'attachments' AND auth.role() = 'authenticated');

CREATE POLICY "Attachments are insertable by authenticated users"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'attachments' AND auth.role() = 'authenticated');

CREATE POLICY "Attachments are updatable by authenticated users"
ON storage.objects FOR UPDATE
USING (bucket_id = 'attachments' AND auth.role() = 'authenticated');

-- Create storage folders structure
INSERT INTO storage.objects (bucket_id, name, owner, metadata) VALUES
('logos', 'school_logo.png', auth.uid(), '{"mimetype": "image/png", "size": 1024}'),
('receipts', 'template.pdf', auth.uid(), '{"mimetype": "application/pdf", "size": 2048}'),
('reports', 'template.xlsx', auth.uid(), '{"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 4096}');

-- Create storage triggers for file cleanup
CREATE OR REPLACE FUNCTION public.handle_file_cleanup()
RETURNS TRIGGER AS $$
BEGIN
    -- Delete the file from storage when the record is deleted
    IF TG_OP = 'DELETE' THEN
        DELETE FROM storage.objects
        WHERE bucket_id = OLD.bucket_id AND name = OLD.name;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create triggers for file cleanup
CREATE TRIGGER handle_file_cleanup
    AFTER DELETE ON storage.objects
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_file_cleanup();

-- Create function to generate signed URLs
CREATE OR REPLACE FUNCTION public.generate_signed_url(
    bucket_id text,
    object_path text,
    expires_in interval DEFAULT '1 hour'::interval
)
RETURNS text AS $$
DECLARE
    signed_url text;
BEGIN
    -- Generate a signed URL for the object
    signed_url := storage.get_signed_url(
        bucket_id,
        object_path,
        expires_in
    );
    RETURN signed_url;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check file size limits
CREATE OR REPLACE FUNCTION public.check_file_size_limit(
    bucket_id text,
    file_size bigint
)
RETURNS boolean AS $$
DECLARE
    max_size bigint;
BEGIN
    -- Set different size limits for different buckets
    CASE bucket_id
        WHEN 'logos' THEN max_size := 5 * 1024 * 1024; -- 5MB
        WHEN 'receipts' THEN max_size := 10 * 1024 * 1024; -- 10MB
        WHEN 'reports' THEN max_size := 20 * 1024 * 1024; -- 20MB
        WHEN 'backups' THEN max_size := 100 * 1024 * 1024; -- 100MB
        WHEN 'imports' THEN max_size := 50 * 1024 * 1024; -- 50MB
        WHEN 'attachments' THEN max_size := 15 * 1024 * 1024; -- 15MB
        ELSE max_size := 5 * 1024 * 1024; -- Default 5MB
    END CASE;

    RETURN file_size <= max_size;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to validate file types
CREATE OR REPLACE FUNCTION public.validate_file_type(
    bucket_id text,
    mime_type text
)
RETURNS boolean AS $$
BEGIN
    -- Set allowed file types for different buckets
    CASE bucket_id
        WHEN 'logos' THEN
            RETURN mime_type IN ('image/jpeg', 'image/png', 'image/gif');
        WHEN 'receipts' THEN
            RETURN mime_type IN ('application/pdf');
        WHEN 'reports' THEN
            RETURN mime_type IN (
                'application/pdf',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-word',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            );
        WHEN 'backups' THEN
            RETURN mime_type IN ('application/zip', 'application/x-zip-compressed');
        WHEN 'imports' THEN
            RETURN mime_type IN (
                'text/csv',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            );
        WHEN 'attachments' THEN
            RETURN mime_type IN (
                'application/pdf',
                'image/jpeg',
                'image/png',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            );
        ELSE
            RETURN false;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to validate file uploads
CREATE OR REPLACE FUNCTION public.validate_file_upload()
RETURNS TRIGGER AS $$
BEGIN
    -- Check file size
    IF NOT public.check_file_size_limit(NEW.bucket_id, (NEW.metadata->>'size')::bigint) THEN
        RAISE EXCEPTION 'File size exceeds limit for bucket %', NEW.bucket_id;
    END IF;

    -- Check file type
    IF NOT public.validate_file_type(NEW.bucket_id, NEW.metadata->>'mimetype') THEN
        RAISE EXCEPTION 'File type not allowed for bucket %', NEW.bucket_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER validate_file_upload
    BEFORE INSERT ON storage.objects
    FOR EACH ROW
    EXECUTE FUNCTION public.validate_file_upload(); 