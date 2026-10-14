<?php

return [

    // Extraction service (services/extract). The token authenticates web -> extract calls.
    'extract' => [
        'url' => env('EXTRACT_URL', 'http://extract:8000'),
        'token' => env('EXTRACT_TOKEN'),
        'timeout' => (int) env('EXTRACT_TIMEOUT', 180),
    ],

    // Optional virus scanning (docker compose --profile av). Off means uploads are marked "skipped".
    'clamav' => [
        'enabled' => (bool) env('CLAMAV_ENABLED', false),
        'host' => env('CLAMAV_HOST', 'clamav'),
        'port' => (int) env('CLAMAV_PORT', 3310),
    ],

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'token' => env('POSTMARK_TOKEN'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'resend' => [
        'key' => env('RESEND_KEY'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

];
