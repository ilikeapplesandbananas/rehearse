-- =============================================================================
-- REHEARSE — Supabase PostgreSQL Schema & Storage Migration
-- =============================================================================
-- Run this in your Supabase SQL Editor when deploying to production.

create extension if not exists "pgcrypto";

-- 1. User Profiles
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default 'Alex Morgan',
  workspace_label text not null default 'Personal workspace',
  weekly_goal int not null default 3,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. Uploaded CV Documents (with parsed candidate profile)
create table if not exists public.cv_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  filename text not null,
  file_type text not null check (file_type in ('PDF', 'DOCX', 'TXT')),
  file_size_bytes int not null default 0,
  page_count int not null default 1,
  storage_path text,
  raw_text text not null,
  candidate_profile jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- 3. Cached Company Interview Research (deduplicated via archetype_id)
create table if not exists public.company_research_cache (
  company_key text primary key,
  company_name text not null,
  archetype_id text not null,
  shared_with_companies jsonb not null default '[]'::jsonb,
  process_summary text not null,
  rounds jsonb not null default '[]'::jsonb,
  company_nuances jsonb not null default '[]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

-- 4. Interview Sessions
create table if not exists public.interview_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  cv_document_id uuid references public.cv_documents(id) on delete set null,
  company_name text not null,
  target_role text not null,
  round_focus text not null default 'full_loop',
  job_description text not null,
  jd_signals jsonb not null default '[]'::jsonb,
  company_research jsonb not null default '{}'::jsonb,
  candidate_profile jsonb not null default '{}'::jsonb,
  explore_pillars jsonb not null default '[]'::jsonb,
  status text not null default 'in_progress' check (status in ('setup', 'in_progress', 'completed')),
  current_question_index int not null default 0,
  overall_score int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 5. Session Questions
create table if not exists public.session_questions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.interview_sessions(id) on delete cascade,
  order_index int not null,
  short_title text not null,
  category text not null,
  question_text text not null,
  source_attribution text not null,
  guidance_cues jsonb not null default '[]'::jsonb,
  evaluation_focus jsonb not null default '[]'::jsonb,
  status text not null default 'up_next' check (status in ('up_next', 'in_progress', 'completed')),
  created_at timestamptz not null default now(),
  unique(session_id, order_index)
);

-- 6. Recorded Attempts & Multi-Dimensional Evaluations
create table if not exists public.question_attempts (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.interview_sessions(id) on delete cascade,
  question_id uuid not null references public.session_questions(id) on delete cascade,
  attempt_number int not null default 1,
  audio_storage_path text,
  duration_seconds numeric(8,2) not null default 0,
  stt_provider text not null default 'browser',
  transcript_verbatim text not null,
  transcript_clean text not null,
  word_timestamps jsonb not null default '[]'::jsonb,
  delivery_metrics jsonb not null default '{}'::jsonb,
  evaluation jsonb not null default '{}'::jsonb,
  llm_provider text not null default 'fallback',
  created_at timestamptz not null default now()
);

-- 7. Personal Study Plan Items
create table if not exists public.study_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  session_id uuid references public.interview_sessions(id) on delete cascade,
  question_id uuid references public.session_questions(id) on delete set null,
  topic text not null,
  subtitle text not null default '',
  why text not null,
  search_query_or_resource text not null,
  resource_url text not null,
  completed boolean not null default false,
  created_at timestamptz not null default now()
);

-- Row Level Security (enable when Supabase Auth is configured)
alter table public.profiles enable row level security;
alter table public.cv_documents enable row level security;
alter table public.interview_sessions enable row level security;
alter table public.session_questions enable row level security;
alter table public.question_attempts enable row level security;
alter table public.study_items enable row level security;

-- Storage bucket for private CVs and optional audio clips
insert into storage.buckets (id, name, public)
values ('rehearse-cvs', 'rehearse-cvs', false)
on conflict (id) do nothing;
