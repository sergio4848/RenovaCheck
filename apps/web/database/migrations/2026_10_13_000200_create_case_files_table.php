<?php

use App\Support\Database\RowLevelSecurity;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // A "sprawa": one renovation project whose documents are checked against each other.
        Schema::create('case_files', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('organization_id')->constrained()->cascadeOnDelete();
            $table->string('reference', 64);
            $table->string('title', 200);
            $table->string('status', 24)->default('new');
            $table->foreignUuid('created_by')->constrained('users');
            $table->timestamps();
            $table->unique(['organization_id', 'reference']);
            $table->index(['organization_id', 'created_at']);
            $table->index('created_by');
        });
        DB::statement("ALTER TABLE case_files ADD CONSTRAINT case_files_status_check CHECK (status IN ('new', 'in_review', 'closed'))");

        RowLevelSecurity::isolateByOrganization('case_files');
        RowLevelSecurity::grant('case_files', ['SELECT', 'INSERT', 'UPDATE', 'DELETE']);
    }

    public function down(): void
    {
        Schema::dropIfExists('case_files');
    }
};
