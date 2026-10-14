<?php

use App\Http\Controllers\AuditEventController;
use App\Http\Controllers\CaseFileController;
use App\Http\Controllers\DocumentController;
use App\Http\Controllers\FindingController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\OrganizationSwitchController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/cases');

Route::middleware(['auth', 'tenant'])->group(function () {
    Route::get('/cases', [CaseFileController::class, 'index'])->name('cases.index')->can('cases.view');
    Route::post('/cases', [CaseFileController::class, 'store'])->name('cases.store')->can('cases.create');
    Route::get('/cases/{caseFile}', [CaseFileController::class, 'show'])->name('cases.show')->can('cases.view');
    Route::post('/cases/{caseFile}/evaluate', [CaseFileController::class, 'evaluate'])->name('cases.evaluate')->can('cases.create');
    Route::post('/cases/{caseFile}/close', [CaseFileController::class, 'close'])->name('cases.close')->can('findings.decide');
    Route::post('/cases/{caseFile}/reopen', [CaseFileController::class, 'reopen'])->name('cases.reopen')->can('findings.decide');

    Route::scopeBindings()->prefix('/cases/{caseFile}/findings')->name('findings.')->group(function () {
        Route::get('/{finding}', [FindingController::class, 'show'])->name('show')->can('cases.view');
        Route::post('/{finding}/decisions', [FindingController::class, 'decide'])->name('decide')->can('findings.decide');
    });

    // Scoped bindings: a document resolves only through its own case (and RLS through the tenant).
    Route::scopeBindings()->prefix('/cases/{caseFile}/documents')->name('documents.')->group(function () {
        Route::post('/', [DocumentController::class, 'store'])->name('store')->can('cases.create');
        Route::patch('/{document}/type', [DocumentController::class, 'updateType'])->name('type')->can('cases.create');
        Route::get('/{document}/pages/{pageNo}', [DocumentController::class, 'page'])
            ->whereNumber('pageNo')->name('page')->can('cases.view');
        Route::get('/{document}/download', [DocumentController::class, 'download'])->name('download')->can('cases.view');
        Route::get('/{document}', [DocumentController::class, 'show'])->name('show')->can('cases.view');
    });

    Route::get('/members', [MemberController::class, 'index'])->name('members.index')->can('members.view');
    Route::get('/audit', [AuditEventController::class, 'index'])->name('audit.index')->can('audit.view');

    Route::post('/organizations/switch', OrganizationSwitchController::class)->name('organizations.switch');
});
