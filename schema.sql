-- ============================================================
-- Pharma Control — Schema Supabase / PostgreSQL
-- MVP: auth, dashboard, productos, normativas, alertas, chatbot
-- Autorización a nivel app (Flask @require_role). Se usa la
-- service_role key, por lo que RLS queda deshabilitado a propósito.
-- ============================================================

-- ----------------------------------------------------------------
-- Extensiones
-- ----------------------------------------------------------------
create extension if not exists "pgcrypto";   -- gen_random_uuid()

-- ----------------------------------------------------------------
-- Tipos enumerados
-- ----------------------------------------------------------------
create type user_role        as enum ('admin', 'compliance_officer', 'gerente');
create type estado_producto  as enum ('vigente', 'por_vencer', 'vencido', 'inactivo');
create type severidad_alerta as enum ('info', 'warning', 'critical');
create type estado_alerta    as enum ('activa', 'resuelta');

-- ----------------------------------------------------------------
-- Función utilitaria: updated_at automático
-- ----------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- ================================================================
-- 1. users
-- ================================================================
create table users (
  id            uuid primary key default gen_random_uuid(),
  email         text not null unique,
  password_hash text not null,                 -- bcrypt/argon2 (AuthService)
  nombre        text not null,
  role          user_role not null default 'gerente',
  activo        boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index idx_users_email on users (email);

create trigger trg_users_updated_at
  before update on users
  for each row execute function set_updated_at();

-- ================================================================
-- 2. refresh_tokens
--    Se guarda SOLO el hash del token (nunca el token en claro).
--    Rotación: al refrescar, se marca revoked=true y se emite uno nuevo.
-- ================================================================
create table refresh_tokens (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users (id) on delete cascade,
  token_hash  text not null unique,
  expires_at  timestamptz not null,
  revoked     boolean not null default false,
  created_at  timestamptz not null default now()
);

create index idx_refresh_tokens_user on refresh_tokens (user_id);
create index idx_refresh_tokens_hash on refresh_tokens (token_hash);

-- ================================================================
-- 3. normativas  (catálogo NOMs, alta manual)
-- ================================================================
create table normativas (
  id          uuid primary key default gen_random_uuid(),
  codigo      text not null unique,            -- ej. 'NOM-059-SSA1-2015'
  titulo      text not null,
  descripcion text,
  url         text,
  vigente     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index idx_normativas_codigo on normativas (codigo);

create trigger trg_normativas_updated_at
  before update on normativas
  for each row execute function set_updated_at();

-- ================================================================
-- 4. productos  (registro sanitario + vencimientos)
--    estado y score_riesgo los recalcula ComplianceService en runtime.
-- ================================================================
create table productos (
  id                  uuid primary key default gen_random_uuid(),
  nombre              text not null,
  registro_sanitario  text not null unique,    -- núm. COFEPRIS
  lote                text,
  fecha_registro      date,
  fecha_vencimiento   date not null,           -- vencimiento del registro
  estado              estado_producto not null default 'vigente',
  score_riesgo        integer not null default 0,   -- 0-100, calculado
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create index idx_productos_registro    on productos (registro_sanitario);
create index idx_productos_vencimiento on productos (fecha_vencimiento);
create index idx_productos_estado      on productos (estado);

create trigger trg_productos_updated_at
  before update on productos
  for each row execute function set_updated_at();

-- ================================================================
-- 5. producto_norma  (M:N entre productos y normativas)
-- ================================================================
create table producto_norma (
  producto_id   uuid not null references productos (id)  on delete cascade,
  normativa_id  uuid not null references normativas (id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (producto_id, normativa_id)
);

create index idx_producto_norma_normativa on producto_norma (normativa_id);

-- ================================================================
-- 6. alertas  (generadas por ComplianceService, upsert idempotente)
--    La unicidad (producto_id, tipo) evita duplicar la misma alerta
--    en cada recálculo; se actualiza dias_restantes/severidad.
-- ================================================================
create table alertas (
  id              uuid primary key default gen_random_uuid(),
  producto_id     uuid not null references productos (id) on delete cascade,
  tipo            text not null,               -- ej. 'vencimiento_registro'
  severidad       severidad_alerta not null default 'info',
  mensaje         text not null,
  dias_restantes  integer,
  estado          estado_alerta not null default 'activa',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (producto_id, tipo)
);

create index idx_alertas_producto  on alertas (producto_id);
create index idx_alertas_estado    on alertas (estado);
create index idx_alertas_severidad on alertas (severidad);

create trigger trg_alertas_updated_at
  before update on alertas
  for each row execute function set_updated_at();

-- ================================================================
-- Seed mínimo (opcional) — usuario admin inicial
-- Reemplaza el hash por uno real generado por AuthService.
-- ================================================================
-- insert into users (email, password_hash, nombre, role)
-- values ('admin@pharmacontrol.mx', '<hash>', 'Admin', 'admin');
