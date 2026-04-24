create table if not exists public.bot_state (
  id bigint primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

insert into public.bot_state (id, payload)
values (
  1,
  jsonb_build_object(
    'categories', jsonb_build_object(
      'chroma', jsonb_build_object('surahs', '{}'::jsonb, 'sheikhs', '{}'::jsonb),
      'designs', jsonb_build_object('surahs', '{}'::jsonb, 'sheikhs', '{}'::jsonb),
      'nature', '[]'::jsonb
    ),
    'settings', jsonb_build_object(
      'default_sheikhs', jsonb_build_array(
        'عبدالباسط عبدالصمد',
        'محمد صديق المنشاوي',
        'محمود خليل الحصري',
        'مشاري راشد العفاسي',
        'ماهر المعيقلي',
        'أحمد العجمي',
        'سعد الغامدي',
        'ياسر الدوسري',
        'علي جابر',
        'عبدالرحمن السديس'
      ),
      'page_size', 12,
      'item_page_size', 8
    )
  )
on conflict (id) do nothing;

alter table public.bot_state enable row level security;
