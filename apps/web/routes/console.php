<?php

use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

Artisan::command('org:external-processing {slug} {state : on|off}', function (string $slug, string $state) {
    if (! in_array($state, ['on', 'off'], true)) {
        $this->error('State must be "on" or "off".');

        return 1;
    }
    // The application role cannot change organizations; the schema owner connection can.
    $organization = DB::connection('migrator')->table('organizations')->where('slug', $slug)->first();
    if ($organization === null) {
        $this->error("No organization {$slug}.");

        return 1;
    }
    DB::connection('migrator')->table('organizations')->where('id', $organization->id)
        ->update(['allow_external_processing' => $state === 'on', 'updated_at' => now()]);
    app(TenantContext::class)->runForOrganization($organization->id, fn () => app(AuditLog::class)->record(
        'organization.external_processing_changed', null, ['allowed' => $state === 'on', 'via' => 'console'],
    ));
    $this->info("External processing for {$slug}: {$state}.");

    return 0;
})->purpose('Allow or forbid sending document content to cloud OCR and the LLM helper');
