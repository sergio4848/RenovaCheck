<?php

namespace Tests\Feature;

use App\Enums\DocType;
use App\Http\Controllers\DocumentController;
use App\Models\AuditEvent;
use App\Models\CaseFile;
use App\Models\Document;
use App\Models\Membership;
use App\Tenancy\TenantContext;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class DocumentAccessTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
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
}
