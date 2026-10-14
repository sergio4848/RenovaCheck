<?php

namespace App\Enums;

enum Permission: string
{
    case CasesView = 'cases.view';
    case CasesCreate = 'cases.create';
    case FindingsDecide = 'findings.decide';
    case AuditView = 'audit.view';
    case MembersView = 'members.view';
    case MembersManage = 'members.manage';
}
