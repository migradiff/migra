alter table "public"."orders" alter column "status" drop default;

alter type "public"."order_status" add value 'rejected' after 'complete';

alter table "public"."orders" alter column status type "public"."order_status" using status::text::"public"."order_status";

alter table "public"."orders" alter column "status" set default 'pending'::order_status;

alter table "public"."orders" alter column "othercolumn" set data type other.otherenum2 using "othercolumn"::text::other.otherenum2;
