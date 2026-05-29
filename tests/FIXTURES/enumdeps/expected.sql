drop view if exists "public"."v";

drop view if exists "public"."v2";

alter type "public"."e" add value 'd' after 'c';

create table "public"."created_with_e" (
    "id" integer,
    "category" e
);


alter table "public"."t" alter column category type "public"."e" using category::text::"public"."e";

create or replace view "public"."v" as  SELECT id,
    category
   FROM t;


create or replace view "public"."v2" as  SELECT id,
    category,
    'b'::e AS e
   FROM t;


