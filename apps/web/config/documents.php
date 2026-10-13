<?php

return [
    'disk' => 's3',
    'public_disk' => 's3-public',
    'max_files_per_upload' => 20,
    'max_file_kb' => 20 * 1024,
    // Lifetime of signed URLs handed to the browser and to the extraction service.
    'browser_url_minutes' => 5,
    'extract_url_minutes' => 10,
];
