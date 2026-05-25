-- =============================================================================
-- RealtouchHR — Supabase (PostgreSQL) schema
-- Run this in the Supabase SQL Editor (Project → SQL Editor → New query)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
create table if not exists users (
    user_id                 text primary key,
    email                   text unique not null,
    name                    text,
    picture                 text,
    password_hash           text,
    role                    text default 'owner',
    company_id              text,
    employee_id             text,
    is_platform_admin       boolean default false,
    theme_preference        text default 'light',
    totp_secret             text,
    totp_enabled            boolean default false,
    backup_codes            jsonb default '[]',
    failed_logins           int default 0,
    locked_until            timestamptz,
    last_login              timestamptz,
    password_reset_token    text,
    password_reset_expires  timestamptz,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);
create index if not exists users_company_id_idx on users(company_id);
create index if not exists users_email_idx on users(email);

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------
create table if not exists companies (
    company_id              text primary key,
    name                    text,
    sector                  text,
    size                    text,
    address                 text,
    phone                   text,
    email                   text,
    website                 text,
    tax_reference           text,
    paye_reference          text,
    hmrc_sender_id          text,
    accounts_office_ref     text,
    owner_id                text,
    subscription_plan       text default 'free',
    subscription_name       text,
    subscription_status     text default 'inactive',
    subscription_active     boolean default false,
    subscription_updated_at timestamptz,
    employee_limit          int default 10,
    stripe_customer_id      text,
    stripe_subscription_id  text,
    bulk_downloads_active_until timestamptz,
    trust_badge_enabled     boolean default false,
    trust_badge_verified    boolean default false,
    compliance_score        int,
    currency                text default 'GBP',
    payroll_frequency       text default 'monthly',
    tax_year_start          text,
    suspended               boolean default false,
    suspended_reason        text,
    suspended_at            timestamptz,
    setup_completed         boolean default false,
    is_parent               boolean default false,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_sessions
-- ---------------------------------------------------------------------------
create table if not exists user_sessions (
    session_token   text primary key,
    user_id         text not null,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create index if not exists user_sessions_user_id_idx on user_sessions(user_id);

-- ---------------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------------
create table if not exists employees (
    employee_id         text primary key,
    company_id          text not null,
    user_id             text,
    first_name          text,
    last_name           text,
    email               text,
    phone               text,
    job_title           text,
    department          text,
    start_date          text,
    end_date            text,
    employment_type     text default 'full_time',
    status              text default 'active',
    salary              numeric,
    currency            text default 'GBP',
    payroll_id          text,
    ni_number           text,
    tax_code            text,
    student_loan        text,
    pension_enrolled    boolean default false,
    address             text,
    bank_name           text,
    bank_sort_code      text,
    bank_account        text,
    right_to_work       text,
    visa_type           text,
    visa_expiry         text,
    nationality         text,
    emergency_contact   jsonb default '{}',
    custom_fields       jsonb default '{}',
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists employees_company_id_idx on employees(company_id);
create index if not exists employees_email_idx on employees(email);
create index if not exists employees_status_idx on employees(status);

-- ---------------------------------------------------------------------------
-- pay_runs
-- ---------------------------------------------------------------------------
create table if not exists pay_runs (
    payrun_id       text primary key,
    company_id      text not null,
    tax_year        text,
    tax_period      int,
    period_start    text,
    period_end      text,
    pay_date        text,
    status          text default 'draft',
    total_gross     numeric default 0,
    total_net       numeric default 0,
    total_tax       numeric default 0,
    total_ni        numeric default 0,
    employee_count  int default 0,
    rti_submitted   boolean default false,
    rti_submitted_at timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists pay_runs_company_id_idx on pay_runs(company_id);

-- ---------------------------------------------------------------------------
-- payslips
-- ---------------------------------------------------------------------------
create table if not exists payslips (
    payslip_id          text primary key,
    payrun_id           text,
    company_id          text not null,
    employee_id         text,
    employee_name       text,
    employee_email      text,
    tax_year            text,
    tax_period          int,
    pay_date            text,
    gross_pay           numeric default 0,
    net_pay             numeric default 0,
    income_tax          numeric default 0,
    national_insurance  numeric default 0,
    pension_ee          numeric default 0,
    pension_er          numeric default 0,
    student_loan        numeric default 0,
    earnings            jsonb default '[]',
    deductions          jsonb default '[]',
    ytd                 jsonb default '{}',
    status              text default 'draft',
    created_at          timestamptz default now()
);
create index if not exists payslips_payrun_id_idx on payslips(payrun_id);
create index if not exists payslips_company_id_idx on payslips(company_id);
create index if not exists payslips_employee_id_idx on payslips(employee_id);

-- ---------------------------------------------------------------------------
-- payment_transactions
-- ---------------------------------------------------------------------------
create table if not exists payment_transactions (
    transaction_id      text primary key,
    session_id          text,
    company_id          text,
    user_id             text,
    user_email          text,
    type                text,
    plan_id             text,
    plan_name           text,
    addon_id            text,
    addon_name          text,
    payslip_id          text,
    payrun_id           text,
    amount              numeric,
    amount_total        numeric,
    currency            text default 'gbp',
    quantity            int default 1,
    payment_status      text default 'pending',
    status              text default 'initiated',
    stripe_customer_id  text,
    payment_intent_id   text,
    receipt_url         text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists payment_transactions_company_id_idx on payment_transactions(company_id);
create index if not exists payment_transactions_session_id_idx on payment_transactions(session_id);

-- ---------------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------------
create table if not exists audit_log (
    audit_id        text primary key default gen_random_uuid()::text,
    company_id      text,
    user_id         text,
    action          text,
    entity_type     text,
    entity_id       text,
    details         jsonb default '{}',
    ip_address      text,
    timestamp       timestamptz default now()
);
create index if not exists audit_log_company_id_idx on audit_log(company_id);
create index if not exists audit_log_timestamp_idx on audit_log(timestamp);

-- ---------------------------------------------------------------------------
-- leave_requests
-- ---------------------------------------------------------------------------
create table if not exists leave_requests (
    leave_request_id    text primary key,
    leave_id            text,
    company_id          text not null,
    employee_id         text,
    employee_name       text,
    leave_type          text,
    start_date          text,
    end_date            text,
    days                numeric,
    status              text default 'pending',
    reason              text,
    approved_by         text,
    approved_at         timestamptz,
    rejected_reason     text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists leave_requests_company_id_idx on leave_requests(company_id);
create index if not exists leave_requests_employee_id_idx on leave_requests(employee_id);

-- ---------------------------------------------------------------------------
-- leave_balances
-- ---------------------------------------------------------------------------
create table if not exists leave_balances (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    leave_type      text,
    year            int,
    entitlement     numeric default 0,
    used            numeric default 0,
    pending         numeric default 0,
    carried_over    numeric default 0,
    updated_at      timestamptz default now()
);
create index if not exists leave_balances_employee_id_idx on leave_balances(employee_id);

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
create table if not exists documents (
    document_id     text primary key,
    company_id      text not null,
    employee_id     text,
    uploaded_by     text,
    name            text,
    type            text,
    category        text,
    file_url        text,
    file_size       int,
    mime_type       text,
    description     text,
    tags            jsonb default '[]',
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create index if not exists documents_company_id_idx on documents(company_id);
create index if not exists documents_employee_id_idx on documents(employee_id);

-- ---------------------------------------------------------------------------
-- secure_documents
-- ---------------------------------------------------------------------------
create table if not exists secure_documents (
    document_id     text primary key,
    company_id      text,
    employee_id     text,
    name            text,
    type            text,
    content         text,
    metadata        jsonb default '{}',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- policies
-- ---------------------------------------------------------------------------
create table if not exists policies (
    policy_id       text primary key,
    company_id      text not null,
    title           text,
    category        text,
    content         text,
    version         text,
    status          text default 'draft',
    requires_acknowledgement boolean default false,
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists policies_company_id_idx on policies(company_id);

-- ---------------------------------------------------------------------------
-- policy_versions
-- ---------------------------------------------------------------------------
create table if not exists policy_versions (
    record_id       text primary key,
    policy_id       text,
    company_id      text,
    version         text,
    content         text,
    created_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- policy_acknowledgements
-- ---------------------------------------------------------------------------
create table if not exists policy_acknowledgements (
    record_id       text primary key,
    policy_id       text,
    company_id      text,
    employee_id     text,
    employee_name   text,
    version         text,
    acknowledged_at timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- training_courses
-- ---------------------------------------------------------------------------
create table if not exists training_courses (
    training_id     text primary key,
    company_id      text not null,
    title           text,
    description     text,
    category        text,
    duration_hours  numeric,
    mandatory       boolean default false,
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- training_records
-- ---------------------------------------------------------------------------
create table if not exists training_records (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    training_id     text,
    course_name     text,
    status          text default 'enrolled',
    score           numeric,
    completed_at    timestamptz,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create index if not exists training_records_employee_id_idx on training_records(employee_id);

-- ---------------------------------------------------------------------------
-- performance_appraisals
-- ---------------------------------------------------------------------------
create table if not exists performance_appraisals (
    review_id       text primary key,
    company_id      text,
    employee_id     text,
    reviewer_id     text,
    period          text,
    status          text default 'draft',
    overall_rating  numeric,
    goals           jsonb default '[]',
    feedback        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- appraisals (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists appraisals (
    review_id       text primary key,
    company_id      text,
    employee_id     text,
    reviewer_id     text,
    period          text,
    status          text default 'draft',
    overall_rating  numeric,
    goals           jsonb default '[]',
    feedback        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- objectives
-- ---------------------------------------------------------------------------
create table if not exists objectives (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    title           text,
    description     text,
    status          text default 'active',
    progress        int default 0,
    due_date        text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- performance_notes
-- ---------------------------------------------------------------------------
create table if not exists performance_notes (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    author_id       text,
    note            text,
    type            text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- review_notes (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists review_notes (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    author_id       text,
    note            text,
    type            text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- absence_records
-- ---------------------------------------------------------------------------
create table if not exists absence_records (
    absence_id      text primary key,
    company_id      text not null,
    employee_id     text,
    type            text,
    start_date      text,
    end_date        text,
    days            numeric,
    reason          text,
    fit_note        boolean default false,
    status          text default 'open',
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists absence_records_company_id_idx on absence_records(company_id);

-- ---------------------------------------------------------------------------
-- rtw_checks
-- ---------------------------------------------------------------------------
create table if not exists rtw_checks (
    rtw_id          text primary key,
    company_id      text,
    employee_id     text,
    document_type   text,
    document_number text,
    expiry_date     text,
    verified        boolean default false,
    verified_by     text,
    verified_at     timestamptz,
    status          text default 'pending',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists rtw_checks_employee_id_idx on rtw_checks(employee_id);

-- ---------------------------------------------------------------------------
-- certificates_of_sponsorship
-- ---------------------------------------------------------------------------
create table if not exists certificates_of_sponsorship (
    cos_id          text primary key,
    company_id      text,
    employee_id     text,
    cos_number      text,
    visa_type       text,
    start_date      text,
    expiry_date     text,
    status          text default 'active',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- cos_register (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists cos_register (
    cos_id          text primary key,
    company_id      text,
    employee_id     text,
    cos_number      text,
    visa_type       text,
    start_date      text,
    expiry_date     text,
    status          text default 'active',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- ukvi_alerts / ukvi_reports / ukvi_reporting_events
-- ---------------------------------------------------------------------------
create table if not exists ukvi_alerts (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    alert_type      text,
    severity        text,
    message         text,
    status          text default 'open',
    created_at      timestamptz default now()
);
create table if not exists ukvi_reports (
    record_id       text primary key,
    company_id      text,
    report_type     text,
    period          text,
    data            jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists ukvi_reporting_events (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    event_type      text,
    event_date      text,
    details         jsonb default '{}',
    submitted       boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- pension_schemes / pension_enrolments
-- ---------------------------------------------------------------------------
create table if not exists pension_schemes (
    record_id       text primary key,
    company_id      text,
    provider        text,
    scheme_name     text,
    employer_rate   numeric,
    employee_rate   numeric,
    status          text default 'active',
    created_at      timestamptz default now()
);
create table if not exists pension_enrolments (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    scheme_id       text,
    enrolment_date  text,
    opt_out_date    text,
    status          text default 'enrolled',
    employee_rate   numeric,
    employer_rate   numeric,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- statutory_payments
-- ---------------------------------------------------------------------------
create table if not exists statutory_payments (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    type            text,
    start_date      text,
    end_date        text,
    weekly_rate     numeric,
    total_amount    numeric,
    status          text default 'active',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- tax_documents
-- ---------------------------------------------------------------------------
create table if not exists tax_documents (
    tax_doc_id      text primary key,
    company_id      text,
    employee_id     text,
    type            text,
    tax_year        text,
    content         jsonb default '{}',
    pdf_url         text,
    status          text default 'draft',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- timesheets / clock_events / shifts / rotas
-- ---------------------------------------------------------------------------
create table if not exists timesheets (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    date            text,
    start_time      text,
    end_time        text,
    break_minutes   int default 0,
    hours_worked    numeric,
    type            text default 'regular',
    status          text default 'pending',
    notes           text,
    created_at      timestamptz default now()
);
create table if not exists clock_events (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    event_type      text,
    timestamp       timestamptz default now(),
    location        text,
    device          text
);
create table if not exists shifts (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    date            text,
    start_time      text,
    end_time        text,
    role            text,
    department      text,
    status          text default 'scheduled',
    created_at      timestamptz default now()
);
create table if not exists rotas (
    record_id       text primary key,
    company_id      text,
    week_start      text,
    shifts          jsonb default '[]',
    created_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- er_cases
-- ---------------------------------------------------------------------------
create table if not exists er_cases (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    case_type       text,
    description     text,
    status          text default 'open',
    assigned_to     text,
    resolution      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- GDPR tables
-- ---------------------------------------------------------------------------
create table if not exists data_processing_activities (
    record_id       text primary key,
    company_id      text,
    name            text,
    purpose         text,
    lawful_basis    text,
    data_categories jsonb default '[]',
    retention_period text,
    status          text default 'active',
    created_at      timestamptz default now()
);
create table if not exists dsar_requests (
    record_id       text primary key,
    company_id      text,
    subject_name    text,
    subject_email   text,
    request_type    text,
    status          text default 'pending',
    due_date        text,
    response        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create table if not exists dpia_records (
    record_id       text primary key,
    company_id      text,
    title           text,
    description     text,
    risk_level      text,
    status          text default 'draft',
    created_at      timestamptz default now()
);
create table if not exists gdpr_erasure_requests (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    requested_by    text,
    status          text default 'pending',
    completed_at    timestamptz,
    created_at      timestamptz default now()
);
create table if not exists breach_incidents (
    record_id       text primary key,
    company_id      text,
    title           text,
    description     text,
    severity        text,
    reported_to_ico boolean default false,
    status          text default 'open',
    created_at      timestamptz default now()
);
create table if not exists processors_register (
    record_id       text primary key,
    company_id      text,
    processor_name  text,
    services        text,
    dpa_in_place    boolean default false,
    created_at      timestamptz default now()
);
create table if not exists retention_overrides (
    record_id       text primary key,
    company_id      text,
    data_type       text,
    retention_days  int,
    reason          text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- salary_history
-- ---------------------------------------------------------------------------
create table if not exists salary_history (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    salary          numeric,
    currency        text default 'GBP',
    effective_date  text,
    reason          text,
    changed_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- notifications
-- ---------------------------------------------------------------------------
create table if not exists notifications (
    record_id       text primary key,
    user_id         text,
    company_id      text,
    type            text,
    title           text,
    message         text,
    read            boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_2fa
-- ---------------------------------------------------------------------------
create table if not exists user_2fa (
    record_id       text primary key,
    user_id         text,
    code            text,
    type            text,
    expires_at      timestamptz,
    used            boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_invites
-- ---------------------------------------------------------------------------
create table if not exists user_invites (
    invite_token    text primary key,
    company_id      text,
    invited_by      text,
    email           text,
    role            text default 'employee',
    status          text default 'pending',
    expires_at      timestamptz,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- RTI submission tables
-- ---------------------------------------------------------------------------
create table if not exists rti_submissions (
    record_id       text primary key,
    company_id      text,
    submission_type text,
    tax_year        text,
    tax_period      int,
    payrun_id       text,
    status          text default 'pending',
    response_code   text,
    response_message text,
    submitted_at    timestamptz,
    created_at      timestamptz default now()
);
create table if not exists rti_payloads (
    record_id       text primary key,
    company_id      text,
    submission_id   text,
    payload         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_receipts (
    record_id       text primary key,
    company_id      text,
    submission_id   text,
    receipt_data    jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_audit_ledger (
    record_id       text primary key,
    company_id      text,
    action          text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_leaver_queue (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    payrun_id       text,
    processed       boolean default false,
    created_at      timestamptz default now()
);
create table if not exists eps_submissions (
    record_id       text primary key,
    company_id      text,
    tax_year        text,
    tax_period      int,
    status          text default 'pending',
    created_at      timestamptz default now()
);
create table if not exists p60_queue (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    tax_year        text,
    status          text default 'pending',
    created_at      timestamptz default now()
);
create table if not exists p11d_records (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    tax_year        text,
    benefits        jsonb default '[]',
    total_value     numeric default 0,
    status          text default 'draft',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- compliance_tasks
-- ---------------------------------------------------------------------------
create table if not exists compliance_tasks (
    record_id       text primary key,
    company_id      text,
    title           text,
    category        text,
    status          text default 'pending',
    due_date        text,
    assigned_to     text,
    completed_at    timestamptz,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- download_passes / download_usage
-- ---------------------------------------------------------------------------
create table if not exists download_passes (
    pass_id         text primary key,
    company_id      text,
    user_id         text,
    resource_id     text,
    resource_type   text,
    transaction_id  text,
    used            boolean default false,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create table if not exists download_usage (
    record_id       text primary key,
    company_id      text,
    user_id         text,
    resource_id     text,
    resource_type   text,
    month           text,
    count           int default 0,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- feature_flags / platform_plans / sso_configs / roles / entities / organizations
-- ---------------------------------------------------------------------------
create table if not exists feature_flags (
    record_id       text primary key,
    company_id      text,
    flag_name       text,
    enabled         boolean default false,
    updated_at      timestamptz default now()
);
create table if not exists platform_plans (
    record_id       text primary key,
    plan_id         text unique,
    name            text,
    price           numeric,
    currency        text default 'gbp',
    features        jsonb default '[]',
    employee_limit  int,
    active          boolean default true,
    created_at      timestamptz default now()
);
create table if not exists sso_configs (
    record_id       text primary key,
    company_id      text unique,
    provider        text,
    metadata_url    text,
    entity_id       text,
    config          jsonb default '{}',
    enabled         boolean default false,
    created_at      timestamptz default now()
);
create table if not exists roles (
    record_id       text primary key,
    company_id      text,
    name            text,
    permissions     jsonb default '[]',
    created_at      timestamptz default now()
);
create table if not exists entities (
    record_id       text primary key,
    company_id      text,
    name            text,
    type            text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists organizations (
    record_id       text primary key,
    company_id      text,
    name            text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);
