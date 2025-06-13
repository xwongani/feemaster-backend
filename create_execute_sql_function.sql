-- Create execute_sql function for Supabase
-- This function allows the backend to execute dynamic SQL queries

CREATE OR REPLACE FUNCTION public.execute_sql(query text, params jsonb DEFAULT '[]'::jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jsonb;
    rec record;
    rows jsonb := '[]'::jsonb;
BEGIN
    -- Validate that query is not empty
    IF query IS NULL OR trim(query) = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Query cannot be empty',
            'data', '[]'::jsonb
        );
    END IF;
    
    -- Execute the query and collect results
    BEGIN
        FOR rec IN EXECUTE query LOOP
            rows := rows || jsonb_build_array(to_jsonb(rec));
        END LOOP;
        
        -- Return success response
        RETURN jsonb_build_object(
            'success', true,
            'data', rows,
            'error', null
        );
        
    EXCEPTION WHEN OTHERS THEN
        -- Return error response
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'data', '[]'::jsonb
        );
    END;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.execute_sql(text, jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.execute_sql(text, jsonb) TO service_role;

-- Test the function with a simple query
SELECT public.execute_sql('SELECT COUNT(*) as total_students FROM students WHERE status = ''active'''); 