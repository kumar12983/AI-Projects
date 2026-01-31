-- Check columns in school_type_lookup table
SELECT column_name, data_type
FROM information_schema.columns 
WHERE table_name = 'school_type_lookup'
ORDER BY ordinal_position;
