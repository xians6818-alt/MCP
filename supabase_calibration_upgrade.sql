alter table public.calibration_samples
  add column if not exists prediction_path text,
  add column if not exists script_path text,
  add column if not exists script_hash text,
  add column if not exists bucket text,
  add column if not exists center numeric(12, 2),
  add column if not exists confidence text,
  add column if not exists composite numeric(5, 2),
  add column if not exists scores jsonb not null default '{}'::jsonb;

create index if not exists idx_calibration_samples_composite
  on public.calibration_samples (composite);
