<?php

namespace Tests\Feature;

use App\Enums\Role;
use App\Models\AuditEvent;
use App\Services\AuditLog;
use App\Tenancy\TenantContext;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

class AuditLogTest extends TestCase
{
    public function test_case_creation_is_recorded_with_actor_and_chained_hashes(): void
    {
        $owner = $this->member(Role::Owner);

        $this->actingAs($owner->user)->post('/cases', ['reference' => 'CP/1', 'title' => 'Dom A']);
        $this->actingAs($owner->user)->post('/cases', ['reference' => 'CP/2', 'title' => 'Dom B']);

        app(TenantContext::class)->activate($owner);
        $events = AuditEvent::query()->orderBy('id')->get();

        $this->assertCount(2, $events);
        $this->assertSame('case.created', $events[0]->event_type);
        $this->assertSame($owner->user_id, $events[0]->actor_user_id);
        $this->assertNull($events[0]->prev_hash);
        $this->assertSame($events[0]->hash, $events[1]->prev_hash);
        $this->assertMatchesRegularExpression('/^[0-9a-f]{64}$/', $events[1]->hash);
        $this->assertNull(app(AuditLog::class)->firstBrokenEventId());
    }

    public function test_events_cannot_be_updated_or_deleted_even_by_the_owner(): void
    {
        $owner = $this->member();
        app(TenantContext::class)->run($owner, fn () => app(AuditLog::class)->record('case.created'));

        foreach (['UPDATE audit_events SET event_type = \'x\'', 'DELETE FROM audit_events'] as $sql) {
            $this->asOwner(function () use ($sql) {
                try {
                    DB::transaction(fn () => DB::statement($sql));
                    $this->fail("{$sql} should have been rejected");
                } catch (QueryException $e) {
                    $this->assertStringContainsString('append-only', $e->getMessage());
                }
            });
        }
    }

    public function test_tampering_is_detected_by_chain_verification(): void
    {
        $owner = $this->member();
        app(TenantContext::class)->run($owner, function () {
            app(AuditLog::class)->record('case.created', null, ['reference' => 'A']);
            app(AuditLog::class)->record('case.created', null, ['reference' => 'B']);
        });

        // Simulate an attacker with schema-owner rights who bypasses the append-only trigger.
        $tampered = $this->asOwner(function () {
            DB::statement('ALTER TABLE audit_events DISABLE TRIGGER audit_events_append_only');
            $id = DB::table('audit_events')->min('id');
            DB::table('audit_events')->where('id', $id)->update(['payload' => json_encode(['reference' => 'Z'])]);
            DB::statement('ALTER TABLE audit_events ENABLE TRIGGER audit_events_append_only');

            return $id;
        });

        app(TenantContext::class)->activate($owner);
        $this->assertSame($tampered, app(AuditLog::class)->firstBrokenEventId());
        $this->actingAs($owner->user)->get('/audit')->assertSee('Łańcuch skrótów przerwany przy zdarzeniu nr '.$tampered);
    }

    public function test_client_supplied_ids_are_replaced_so_id_order_is_chain_order(): void
    {
        $owner = $this->member();
        app(TenantContext::class)->activate($owner);
        DB::statement(
            "INSERT INTO audit_events (id, organization_id, event_type, hash)
             VALUES (-1, ?, 'case.created', repeat('0', 64))",
            [$owner->organization_id],
        );

        app(AuditLog::class)->record('case.created');

        $this->assertSame(0, DB::table('audit_events')->where('id', '<', 1)->count());
        $ids = DB::table('audit_events')->orderBy('id')->pluck('id')->all();
        $this->assertSame($ids[0] + 1, $ids[1], 'ids are consecutive');
        $this->assertNull(app(AuditLog::class)->firstBrokenEventId());
    }

    public function test_chain_verification_requires_an_active_organization(): void
    {
        $this->expectException(QueryException::class);
        $this->expectExceptionMessage('requires an active organization');
        app(AuditLog::class)->firstBrokenEventId();
    }

    public function test_sensitive_payload_keys_are_redacted(): void
    {
        $owner = $this->member();
        app(TenantContext::class)->run($owner, fn () => app(AuditLog::class)->record('case.created', null, [
            'reference' => 'CP/1',
            'nested' => ['api_key' => 'abc', 'password' => 'p'],
        ]));

        app(TenantContext::class)->activate($owner);
        $payload = AuditEvent::query()->first()->payload;
        $this->assertSame('CP/1', $payload['reference']);
        $this->assertSame('[REDACTED]', $payload['nested']['api_key']);
        $this->assertSame('[REDACTED]', $payload['nested']['password']);
    }
}
