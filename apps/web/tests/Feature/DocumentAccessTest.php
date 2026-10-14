<?php

namespace Tests\Feature;

use App\Enums\DocType;
use App\Http\Controllers\DocumentController;
use App\Jobs\ProcessDocument;
use App\Models\AuditEvent;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\DocumentField;
use App\Models\Membership;
use App\Tenancy\TenantContext;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class DocumentAccessTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        Storage::fake('s3-public');
        Storage::disk('s3-public')->buildTemporaryUrlsUsing(
            fn (string $path, $expiration, array $options) => 'http://localhost:9000/renova-documents/'.$path
                .'?X-Amz-Expires=300&disposition='.urlencode($options['ResponseContentDisposition'] ?? '')
        );
    }

    private function document(Membership $membership, CaseFile $case, array $attributes = []): Document
    {
        return app(TenantContext::class)->run($membership, function () use ($membership, $case, $attributes) {
            $document = Document::factory()->create([
                'case_file_id' => $case->id,
                'uploaded_by' => $membership->user_id,
                'status' => 'processed',
                'storage_key' => "org/{$membership->organization_id}/cases/{$case->id}/documents/x/original.pdf",
            ] + $attributes);
            $document->pages()->create([
                'page_no' => 1, 'width_pt' => 595.28, 'height_pt' => 841.89,
                'image_key' => $document->storagePrefix().'pages/001.png',
                'image_width_px' => 1240, 'image_height_px' => 1754, 'text_source' => 'text_layer', 'word_count' => 120,
            ]);

            return $document;
        });
    }

    public function test_type_correction_is_saved_as_manual_and_audited(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $document = $this->document($owner, $case);

        $this->actingAs($owner->user)
            ->patch("/cases/{$case->id}/documents/{$document->id}/type", ['doc_type' => 'faktura_korygujaca'])
            ->assertRedirect("/cases/{$case->id}");

        app(TenantContext::class)->activate($owner);
        $document->refresh();
        $this->assertSame(DocType::FakturaKorygujaca, $document->doc_type);
        $this->assertSame('user', $document->doc_type_source);
        $event = AuditEvent::query()->where('event_type', 'document.type_corrected')->sole();
        $this->assertEqualsCanonicalizing(['from' => null, 'to' => 'faktura_korygujaca', 'classifier' => null], $event->payload);
    }

    public function test_unknown_type_is_rejected(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $document = $this->document($owner, $case);

        $this->actingAs($owner->user)
            ->patch("/cases/{$case->id}/documents/{$document->id}/type", ['doc_type' => 'paragon'])
            ->assertSessionHasErrors('doc_type');
    }

    public function test_documents_resolve_only_through_their_own_case_and_organization(): void
    {
        $alfa = $this->member();
        $beta = $this->member();
        $alfaCase = $this->caseFor($alfa, 'A/1');
        $otherAlfaCase = $this->caseFor($alfa, 'A/2');
        $betaCase = $this->caseFor($beta, 'B/1');
        $alfaDoc = $this->document($alfa, $alfaCase);
        $betaDoc = $this->document($beta, $betaCase);

        $this->actingAs($alfa->user)->get("/cases/{$otherAlfaCase->id}/documents/{$alfaDoc->id}/pages/1")->assertNotFound();
        $this->actingAs($alfa->user)->get("/cases/{$betaCase->id}/documents/{$betaDoc->id}/pages/1")->assertNotFound();
        $this->actingAs($alfa->user)->get("/cases/{$alfaCase->id}/documents/{$betaDoc->id}/download")->assertNotFound();
        $this->actingAs($alfa->user)
            ->patch("/cases/{$betaCase->id}/documents/{$betaDoc->id}/type", ['doc_type' => 'umowa'])->assertNotFound();
    }

    public function test_page_and_download_redirect_to_short_lived_signed_urls(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $document = $this->document($owner, $case, ['original_name' => 'Fak"tura.pdf']);

        $page = $this->actingAs($owner->user)->get("/cases/{$case->id}/documents/{$document->id}/pages/1");
        $page->assertRedirect();
        $this->assertStringStartsWith('http://localhost:9000/renova-documents/'.$document->storagePrefix().'pages/001.png', $page->headers->get('Location'));

        $download = $this->actingAs($owner->user)->get("/cases/{$case->id}/documents/{$document->id}/download");
        $this->assertStringContainsString(urlencode('attachment; filename="Fak_tura.pdf"'), $download->headers->get('Location'));
        $this->actingAs($owner->user)->get("/cases/{$case->id}/documents/{$document->id}/pages/2")->assertNotFound();
    }

    public function test_case_page_lists_documents_with_type_and_pages(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $this->document($owner, $case, ['original_name' => 'umowa.pdf']);

        $this->actingAs($owner->user)->get("/cases/{$case->id}")
            ->assertOk()
            ->assertSee('umowa.pdf')
            ->assertSee('Nierozpoznany — wskaż typ')
            ->assertSee('Wgraj dokumenty');
    }

    public function test_download_name_is_plain_ascii_with_the_sniffed_extension(): void
    {
        $name = fn (string $original, string $mime = 'application/pdf') => DocumentController::downloadName(
            new Document(['original_name' => $original, 'mime' => $mime]),
        );

        $this->assertSame('Umowa lodz.pdf', $name('Umowa łódź.exe'));
        $this->assertSame('skan.png', $name('skan.pdf', 'image/png'));
        $this->assertSame('a b_c.jpg', $name("a\r\nb;c.html", 'image/jpeg'));
        $this->assertSame('document.pdf', $name('..'));
        $this->assertSame(104, strlen($name(str_repeat('x', 300).'.pdf')));
    }

    private function withFields(Membership $membership, Document $document): void
    {
        app(TenantContext::class)->run($membership, function () use ($document) {
            $document->fields()->create([
                'name' => 'amount_gross', 'value' => '49522.27', 'raw_text' => '49 522,27 zł', 'page_no' => 1,
                'bbox' => ['x0' => 0.82, 'y0' => 0.36, 'x1' => 0.93, 'y1' => 0.37],
                'method' => 'label', 'confidence' => 0.98, 'status' => 'ok',
            ]);
            $document->fields()->create([
                'name' => 'amount_vat', 'value' => null, 'raw_text' => '3 8?2,O7', 'page_no' => 1,
                'bbox' => ['x0' => 0.84, 'y0' => 0.35, 'x1' => 0.93, 'y1' => 0.36],
                'method' => 'label', 'confidence' => 0, 'status' => 'unreadable',
            ]);
        });
    }

    public function test_document_page_shows_fields_over_the_page_image(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $document = $this->document($owner, $case);
        $this->withFields($owner, $document);

        $this->actingAs($owner->user)->get("/cases/{$case->id}/documents/{$document->id}")
            ->assertOk()
            ->assertSee('Kwota brutto')
            ->assertSee('49 522,27 zł')
            ->assertSee('49522.27')
            ->assertSee('nieczytelne')
            ->assertSee('data-box="0.82000,0.36000,0.93000,0.37000"', false)
            ->assertSee("/cases/{$case->id}/documents/{$document->id}/pages/1", false);
        $this->actingAs($owner->user)->get("/cases/{$case->id}")->assertSee('pola: 2');
    }

    public function test_fields_of_another_organization_are_not_visible(): void
    {
        $alfa = $this->member();
        $beta = $this->member();
        $betaCase = $this->caseFor($beta);
        $betaDoc = $this->document($beta, $betaCase);
        $this->withFields($beta, $betaDoc);

        $this->actingAs($alfa->user)->get("/cases/{$betaCase->id}/documents/{$betaDoc->id}")->assertNotFound();
        $count = app(TenantContext::class)->run($alfa, fn () => DocumentField::query()->count());
        $this->assertSame(0, $count);
    }

    public function test_type_correction_analyses_the_document_again(): void
    {
        $owner = $this->member();
        $case = $this->caseFor($owner);
        $document = $this->document($owner, $case);

        $this->actingAs($owner->user)
            ->patch("/cases/{$case->id}/documents/{$document->id}/type", ['doc_type' => 'umowa'])
            ->assertRedirect("/cases/{$case->id}");

        Queue::assertPushed(ProcessDocument::class, fn ($job) => $job->documentId === $document->id);
        app(TenantContext::class)->activate($owner);
        $this->assertSame('uploaded', $document->refresh()->status);
    }

    public function test_field_list_matches_the_field_dictionary(): void
    {
        $path = base_path('../../packages/rules/fields.yaml');
        if (! is_file($path)) {
            $this->markTestSkipped('packages/rules is not available in this checkout.');
        }
        preg_match_all('/^  ([a-z][a-z0-9_]*):\s*$/m', (string) file_get_contents($path), $matches);

        $this->assertEqualsCanonicalizing($matches[1], config('documents.fields'));
        foreach (config('documents.fields') as $name) {
            $this->assertNotSame('field.'.$name, __('field.'.$name, [], 'pl'), "missing Polish label for {$name}");
        }
    }
}
