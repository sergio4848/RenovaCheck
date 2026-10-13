<?php

namespace Tests\Feature;

use App\Enums\Role;
use App\Jobs\ProcessDocument;
use App\Models\AuditEvent;
use App\Models\Document;
use App\Services\Antivirus\InfectedFile;
use App\Services\Antivirus\Scanner;
use App\Tenancy\TenantContext;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class DocumentUploadTest extends TestCase
{
    private const FIXTURE = __DIR__.'/../Fixtures/faktura_clean.pdf';

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
        Queue::fake();
    }

    private function pdf(string $name = 'faktura.pdf'): UploadedFile
    {
        return UploadedFile::fake()->createWithContent($name, (string) file_get_contents(self::FIXTURE));
    }

    public function test_accepted_file_is_stored_privately_audited_and_queued(): void
    {
        $owner = $this->member(Role::Reviewer);
        $case = $this->caseFor($owner);

        $this->actingAs($owner->user)
            ->post("/cases/{$case->id}/documents", ['files' => [$this->pdf('Faktura VAT 05-2026.pdf')]])
            ->assertRedirect("/cases/{$case->id}")
            ->assertSessionHas('upload_results');

        app(TenantContext::class)->activate($owner);
        $document = Document::query()->sole();
        $this->assertSame('application/pdf', $document->mime);
        $this->assertSame(hash_file('sha256', self::FIXTURE), $document->sha256);
        $this->assertSame('skipped', $document->scan_status);
        $this->assertSame("org/{$owner->organization_id}/cases/{$case->id}/documents/{$document->id}/original.pdf", $document->storage_key);
        Storage::disk('s3')->assertExists($document->storage_key);
        Queue::assertPushed(ProcessDocument::class, fn ($job) => $job->documentId === $document->id
            && $job->organizationId === $owner->organization_id);
        $this->assertSame(1, AuditEvent::query()->where('event_type', 'document.uploaded')->count());
    }

    public function test_same_file_twice_is_one_document(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$this->pdf()]]);
        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$this->pdf('kopia.pdf')]])
            ->assertSessionHas('upload_results', ['„kopia.pdf” — ten plik jest już w sprawie.']);

        app(TenantContext::class)->activate($owner);
        $this->assertSame(1, Document::query()->count());
        Queue::assertPushed(ProcessDocument::class, 1);
    }

    public function test_content_decides_the_type_not_the_name(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $html = UploadedFile::fake()->createWithContent('faktura.pdf', '<html><script>alert(1)</script></html>');
        $exe = UploadedFile::fake()->createWithContent('faktura.pdf', "MZ\x90\x00".str_repeat("\x00", 64));

        // Test uploads report a type from their name, so the validator's finfo check is bypassed here;
        // the intake's own magic-byte check must still refuse them.
        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$html, $exe]])
            ->assertSessionHas('upload_results', [
                '„faktura.pdf” — odrzucono: dozwolone są tylko PDF, PNG i JPEG.',
                '„faktura.pdf” — odrzucono: dozwolone są tylko PDF, PNG i JPEG.',
            ]);

        app(TenantContext::class)->activate($owner);
        $this->assertSame(0, Document::query()->count());
        $this->assertSame([], Storage::disk('s3')->allFiles());
    }

    public function test_a_png_named_pdf_is_stored_as_png(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        // A 1x1 PNG, built without GD so the test also runs in the slim container.
        $pngBytes = base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==');
        $png = UploadedFile::fake()->createWithContent('skan.pdf', $pngBytes);

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$png]]);

        app(TenantContext::class)->activate($owner);
        $document = Document::query()->sole();
        $this->assertSame('image/png', $document->mime);
        $this->assertStringEndsWith('/original.png', $document->storage_key);
    }

    public function test_limits_on_count_and_size(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $tooMany = array_fill(0, 21, $this->pdf());
        $tooLarge = UploadedFile::fake()->create('duzy.pdf', 25 * 1024, 'application/pdf');

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => $tooMany])
            ->assertSessionHasErrors('files');
        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$tooLarge]])
            ->assertSessionHasErrors('files.0');
    }

    public function test_infected_files_are_rejected_without_storing_them(): void
    {
        $this->app->bind(Scanner::class, fn () => new class implements Scanner
        {
            public function scan(string $path): string
            {
                throw new InfectedFile;
            }
        });
        $owner = $this->member();
        $case = $this->caseFor($owner);

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$this->pdf()]])
            ->assertSessionHas('upload_results', ['„faktura.pdf” — odrzucono: wykryto złośliwe oprogramowanie.']);

        app(TenantContext::class)->activate($owner);
        $this->assertSame(0, Document::query()->count());
        $this->assertSame([], Storage::disk('s3')->allFiles());
        $this->assertSame(1, AuditEvent::query()->where('event_type', 'document.rejected_infected')->count());
        Queue::assertNothingPushed();
    }

    public function test_cannot_upload_into_another_organizations_case(): void
    {
        $alfa = $this->member();
        $beta = $this->member();
        $betaCase = $this->caseFor($beta);

        $this->actingAs($alfa->user)->post("/cases/{$betaCase->id}/documents", ['files' => [$this->pdf()]])
            ->assertNotFound();
        Queue::assertNothingPushed();
    }

    public function test_display_names_lose_paths_and_control_characters(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", [
            'files' => [$this->pdf("..\\..\\etc/pass\x07wd.pdf")],
        ]);

        app(TenantContext::class)->activate($owner);
        $this->assertSame('passwd.pdf', Document::query()->sole()->original_name);
    }

    public function test_a_concurrent_upload_of_the_same_file_ends_as_a_duplicate(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $sha256 = hash_file('sha256', self::FIXTURE);
        // The other request commits its row after this one's duplicate check, while the file is scanned.
        $this->app->instance(Scanner::class, new class($case->id, $owner->user_id, $sha256) implements Scanner
        {
            public function __construct(private string $caseId, private string $userId, private string $sha256) {}

            public function scan(string $path): string
            {
                Document::factory()->create([
                    'case_file_id' => $this->caseId, 'uploaded_by' => $this->userId, 'sha256' => $this->sha256,
                ]);

                return 'skipped';
            }
        });

        $this->actingAs($owner->user)->post("/cases/{$case->id}/documents", ['files' => [$this->pdf()]])
            ->assertSessionHas('upload_results', ['„faktura.pdf” — ten plik jest już w sprawie.']);

        app(TenantContext::class)->activate($owner);
        $this->assertSame(1, Document::query()->count());
        $this->assertSame([], Storage::disk('s3')->allFiles());
        $this->assertSame(0, AuditEvent::query()->where('event_type', 'document.uploaded')->count());
        Queue::assertNothingPushed();
    }
}
