<?php

use App\Http\Controllers\AuditEventController;
use App\Http\Controllers\CaseFileController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\OrganizationSwitchController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/cases');

Route::middleware(['auth', 'tenant'])->group(function () {
    Route::get('/cases', [CaseFileController::class, 'index'])->name('cases.index')->can('cases.view');
    Route::post('/cases', [CaseFileController::class, 'store'])->name('cases.store')->can('cases.create');
    Route::get('/cases/{caseFile}', [CaseFileController::class, 'show'])->name('cases.show')->can('cases.view');

    Route::get('/members', [MemberController::class, 'index'])->name('members.index')->can('members.view');
    Route::get('/audit', [AuditEventController::class, 'index'])->name('audit.index')->can('audit.view');

    Route::post('/organizations/switch', OrganizationSwitchController::class)->name('organizations.switch');
});
