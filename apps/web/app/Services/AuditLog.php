<?php

namespace App\Services;

use App\Tenancy\TenantContext;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

/**
 * Appends events to audit_events in the caller's transaction, so an event exists exactly when
 * the change it describes was committed. Hash chaining and timestamps are set by the database.
 */
final class AuditLog
{
    private const REDACTED = '[REDACTED]';

    // Redaction idea from emlakpro apps/api/src/modules/security/audit.service.ts — Copyright (c) 2026 Sergen Şahin.
    private const SENSITIVE_KEY = '/pass(word)?|secret|token|api[_-]?key|authorization|cookie/i';

    public function __construct(private readonly TenantContext $tenant) {}

    /** @param  array<string, mixed>  $payload */
    public function record(string $eventType, ?Model $subject = null, array $payload = []): void
    {
        DB::table('audit_events')->insert([
            'organization_id' => $this->tenant->requireOrganizationId(),
            'actor_user_id' => Auth::id(),
            'event_type' => $eventType,
            'subject_type' => $subject ? class_basename($subject) : null,
            'subject_id' => $subject?->getKey(),
            'payload' => json_encode($this->redact($payload), JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE),
            // id, created_at, prev_hash and hash are set by the audit_events_chain trigger.
            'id' => 0,
            'hash' => str_repeat('0', 64),
        ]);
    }

    /** Id of the first event whose hash chain is broken, or null when intact. */
    public function firstBrokenEventId(): ?int
    {
        $row = DB::selectOne('SELECT audit_chain_break() AS id');

        return $row?->id === null ? null : (int) $row->id;
    }

    /**
     * @param  array<array-key, mixed>  $payload
     * @return array<array-key, mixed>
     */
    private function redact(array $payload): array
    {
        foreach ($payload as $key => $value) {
            if (is_string($key) && preg_match(self::SENSITIVE_KEY, $key)) {
                $payload[$key] = self::REDACTED;
            } elseif (is_array($value)) {
                $payload[$key] = $this->redact($value);
            }
        }

        return $payload;
    }
}
