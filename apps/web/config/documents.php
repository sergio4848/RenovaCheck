<?php

return [
    'disk' => 's3',
    'public_disk' => 's3-public',
    'max_files_per_upload' => 20,
    // The rule engine reads at most 50 documents per case.
    'max_documents_per_case' => 40,
    'max_file_kb' => 20 * 1024,
    // Lifetime of signed URLs handed to the browser and to the extraction service.
    'browser_url_minutes' => 5,
    'extract_url_minutes' => 10,
    // Field names from packages/rules/fields.yaml, in display order (tests keep them in sync).
    'fields' => [
        'document_number', 'application_number', 'related_document_number',
        'investor_name', 'address_street', 'address_building_no', 'address_postal_code', 'address_city',
        'contractor_name', 'contractor_nip',
        'product_manufacturer', 'product_model', 'product_power_kw', 'serial_number', 'zum_id',
        'amount_net', 'amount_vat', 'amount_gross', 'advance_amount', 'amount_due',
        'application_date', 'contract_date', 'invoice_date', 'sale_date', 'acceptance_date',
        'signature_investor', 'signature_contractor',
    ],
    'field_methods' => ['label', 'block', 'above', 'title_number', 'address', 'signature', 'llm'],
];
