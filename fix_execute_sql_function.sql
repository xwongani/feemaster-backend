-- Fix execute_sql function conflict
-- Drop the redundant function and keep only the main one

-- Drop the simpler version that's causing conflicts
DROP FUNCTION IF EXISTS public.execute_sql(text);

-- Ensure we have only the main function with proper signature
CREATE OR REPLACE FUNCTION public.execute_sql(query text, params jsonb DEFAULT '[]')
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jsonb;
    rec record;
    rows jsonb := '[]';
BEGIN
    -- Validate that query is not empty
    IF query IS NULL OR trim(query) = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Query cannot be empty',
            'data', '[]'
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
            'data', '[]'
        );
    END;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.execute_sql(text, jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.execute_sql(text, jsonb) TO service_role;

-- Test the function with explicit parameter types
SELECT public.execute_sql('SELECT COUNT(*) as total_students FROM students WHERE status = ''active'''::text, '[]'::jsonb); 