drop index if exists "goodschema"."t_id_idx";

alter type "goodschema"."sdfasdfasdf" add value 'not delivered' after 'delivered';

alter table "goodschema"."t" add column "name" text;

create or replace view "goodschema"."v" as  SELECT 2 AS a;
