UPDATE raw_sources
SET normalized_name =
    TRIM(RTRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LOWER(TRIM(raw_name)),
            ' incorporated', ''),
            ' corporation',  ''),
            ' limited',       ''),
            ' private',       ''),
            ' pvt',           ''),
            ' llc',           ''),
            ' ltd',           ''),
            ' inc',           ''),
            ' inc.',          ''),
            ' co.',           ''),
            ',', ''),
        ' .'),
    ' ');

UPDATE raw_sources
SET normalized_domain =
    SUBSTR(
        REPLACE(REPLACE(REPLACE(LOWER(TRIM(raw_domain)),
            'https://', ''), 'http://', ''), 'www.', '') || '/',
        1,
        INSTR(REPLACE(REPLACE(REPLACE(LOWER(TRIM(raw_domain)),
            'https://', ''), 'http://', ''), 'www.', '') || '/', '/') - 1
    )
WHERE raw_domain IS NOT NULL AND TRIM(raw_domain) <> '';
