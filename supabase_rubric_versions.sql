create table if not exists public.rubric_versions (
  id uuid primary key default gen_random_uuid(),
  version text not null unique,
  formula text not null,
  weights jsonb not null default '{}'::jsonb,
  normalization_constant numeric(8, 3) not null,
  description text,
  dimensions jsonb not null default '[]'::jsonb,
  is_active boolean not null default false,
  created_at timestamptz not null default now()
);

create unique index if not exists idx_rubric_versions_single_active
  on public.rubric_versions (is_active)
  where is_active = true;

create index if not exists idx_rubric_versions_created_at
  on public.rubric_versions (created_at desc);
