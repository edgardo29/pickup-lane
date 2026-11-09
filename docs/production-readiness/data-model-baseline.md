# Pickup Lane Data Model Baseline

This is a read-only inventory of the **current repository schema declarations**, prepared before comparing the 54 approved page specifications with the data model. It describes existing SQLAlchemy mappings and canonical Alembic revisions, not an approved future schema or a verified deployed database. No database was connected to, and no migrations or tests were run.

## Audit report

| Measure | Repository baseline |
|---|---:|
| Application tables | 64 |
| Mapped columns | 1053 |
| Declared foreign-key edges | 211 |
| Declared indexes | 473 |
| Named constraints | 431 |
| CHECK constraints | 404 |
| Alembic revisions | 65 (64 table revisions; one extension revision) |

**Sources and authority.** [Database guidance](../coding-standards/database.md) defines PostgreSQL/Alembic as the schema-management path and the current editable, clean-rebuild migration policy. [Base](../../backend/database_metadata.py) owns mapped metadata; [model registration](../../backend/models/__init__.py) imports the mapped classes; [Alembic env](../../backend/alembic/env.py) sets that metadata as its comparison target and executes revisions against the configured database. The 64 current model files and 65 files in [`backend/alembic/versions/`](../../backend/alembic/versions/) were inspected. Application services and route code were consulted only to explain ownership or lifecycle where needed. The actual schema in any deployed or local database is a separate state and was not inspected.

**Static reconciliation.** One canonical revision creates each mapped table. The migration chain has one base revision and one head. All 64 table names, 1,053 column names, 473 explicit index names, and 431 named constraint names match their corresponding model metadata. Static comparisons found no differences in compiled column types, declared nullability, primary-key flags, foreign-key targets and delete actions, server-default expressions, or index uniqueness, method, predicate, and operator-class options. CHECK expressions match after whitespace normalization except for one ordering difference in the allowed `admin_actions.action_type` values; the value sets match. The sole other syntactic difference is an unnamed uniqueness declaration on `user_payment_methods.stripe_payment_method_id`, expressed as a column flag in the model and a table constraint in its migration. These checks do not prove full index-expression parity or actual database state.

**Domains.** Accounts/authentication/settings; games/venues/hosting; bookings/guests/participants/waitlists; payments/refunds/credits/financial records; Need a Sub; notifications/communications; administration/moderation/auditing; and durable jobs/worker operations.

**Structural observations.**

- **Confirmed:** No model table lacks a table-creating migration, and no migration-created table lacks a model. No table, column-name, explicit-index-name, or named-constraint-name discrepancy was found in the static comparison. This is limited to repository declarations and naming/shape checks.
- **Confirmed:** Relationships are represented by 211 foreign-key edges; the current mapped classes declare no SQLAlchemy `relationship()` properties. The inbound and outbound links below therefore describe database FKs, not ORM navigation attributes.
- **Potential concern, not a confirmed defect:** `games.host_user_id` serves a required community owner and an optional official host designation. The different meanings share one column and are bounded by game-type CHECKs. Review its service use before changing this structure. See [game model](../../backend/models/game_model.py), [game migration](../../backend/alembic/versions/0013_create_games_table.py), and [official host service](../../backend/services/official_game_roster_service.py).
- **Potential concern, not a confirmed defect:** Current-state rows coexist with status/history or event tables across games, bookings, participants, Need a Sub, money issues, refunds, and durable jobs. These structures appear to preserve transitions and provider/workflow evidence; they are not classified as redundant without a full use review. The history/event tables below list their own columns and constraints.
- **Potential concern, not a confirmed defect:** Some historical `previous_status`/`new_status` values have no table-local value CHECK even where the parent current-status field is constrained. This may intentionally preserve historical/provider states. See [durable job events](../../backend/models/durable_job_event_model.py), [money issue events](../../backend/models/money_issue_event_model.py), and [refund events](../../backend/models/refund_event_model.py).
- **Confirmed distinct structures:** User notifications, staff target notices, and platform notices have different target/read-state tables; payment, refund, compensation, and financial-outcome records have different lifecycle purposes. Similar names are not evidence of duplication. Their specific FKs and constraints appear below.

**Non-table objects.** [Revision 0001](../../backend/alembic/versions/0001_enable_pg_trgm_extension.py) enables `pg_trgm`; [platform notices revision](../../backend/alembic/versions/0006_create_platform_notices_table.py) creates `platform_notice_global_sequence_seq`; [admin actions revision](../../backend/alembic/versions/0004_create_admin_actions_table.py) and [rejected attempts revision](../../backend/alembic/versions/0045_create_admin_rejected_attempts_table.py) create immutability functions/triggers. These objects are outside the 64-table count.

**Verification limit.** No production, deployed, development, or test database was queried. Therefore this inventory cannot confirm which revision any database has applied, whether its schema was rebuilt after an edited canonical migration, or whether manually created objects or drift exist. The model-to-migration comparison above is static; full index-expression and live schema parity require a separate authorized verification step.

## Reading the table entries

Each entry lists every mapped column and its PostgreSQL-compiled type, nullability, server/client defaults, and PK or direct column-unique flag. Composite/unnamed uniqueness, all FK constraints (including delete behavior), all CHECK constraints, and every declared index appear separately. Inbound references show other mapped tables that point to this table. Index expressions and PostgreSQL options are rendered from model metadata. Lifecycle values are extracted from direct `IN (...)` CHECKs; other CHECKs remain listed verbatim. `—` means no declared value. Source links point to both the model and the canonical migration for each table.

## Accounts, authentication, and user settings

### `users`

Account identity, profile, access state, and hosting eligibility. Sources: [model](../../backend/models/user_model.py), [canonical migration](../../backend/alembic/versions/0003_create_users_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `auth_user_id` | `VARCHAR(128)` | Yes | — | — |
| `role` | `VARCHAR(20)` | No | server `'player'` | — |
| `email` | `VARCHAR(255)` | Yes | — | — |
| `email_verified_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `phone` | `VARCHAR(30)` | Yes | — | — |
| `first_name` | `VARCHAR(100)` | Yes | — | — |
| `last_name` | `VARCHAR(100)` | Yes | — | — |
| `date_of_birth` | `DATE` | Yes | — | — |
| `profile_photo_url` | `TEXT` | Yes | — | — |
| `home_city` | `VARCHAR(120)` | Yes | — | — |
| `home_state` | `VARCHAR(120)` | Yes | — | — |
| `account_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `hosting_status` | `VARCHAR(30)` | No | server `'not_eligible'` | — |
| `stripe_customer_id` | `VARCHAR(255)` | Yes | — | — |
| `member_since` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** None.
- **Unique constraints:** `uq_users_auth_user_id`: `auth_user_id`; `uq_users_email`: `email`; `uq_users_phone`: `phone`; `uq_users_stripe_customer_id`: `stripe_customer_id`.
- **Other table relationships:** Referenced by `admin_actions`, `admin_financial_outcomes`, `admin_rejected_attempts`, `admin_review_case_events`, `admin_review_case_notes`, `admin_review_cases`, `admin_review_signals`, `admin_target_notices`, `booking_status_history`, `bookings`, `chat_messages`, `community_game_details`, `community_publish_attempts`, `game_chat_reads`, `game_credits`, `game_images`, `game_participants`, `game_status_history`, `games`, `host_publish_entitlements`, `host_publish_fees`, `money_issue_events`, `money_issues`, `notifications`, `participant_status_history`, `payment_confirmation_attempts`, `payment_method_operations`, `payments`, `platform_notice_global_seen_states`, `platform_notice_recipients`, `platform_notice_selected_reads`, `platform_notices`, `policy_acceptances`, `refund_events`, `refunds`, `sub_post_chat_messages`, `sub_post_chat_reads`, `sub_post_request_status_history`, `sub_post_requests`, `sub_post_status_history`, `sub_posts`, `support_flags`, `user_payment_methods`, `user_settings`, `user_stats`, `venue_approval_requests`, `venue_images`, `venues`, `waitlist_entries`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `role`: `player`, `admin`; `account_status`: `active`, `suspended`, `pending_deletion`, `deleted`; `hosting_status`: `not_eligible`, `eligible`, `restricted`.
- **CHECK constraints:**
  - `ck_users_account_status`: `account_status IN ('active', 'suspended', 'pending_deletion', 'deleted')`
  - `ck_users_hosting_status`: `hosting_status IN ('not_eligible', 'eligible', 'restricted')`
  - `ck_users_role`: `role IN ('player', 'admin')`
- **Indexes:**
  - `ix_users_admin_account_status_created_id`: `users.account_status, created_at DESC, id DESC` (`WHERE deleted_at IS NULL`)
  - `ix_users_admin_email_lower`: `lower(email)` (`WHERE deleted_at IS NULL`)
  - `ix_users_admin_hosting_status_created_id`: `users.hosting_status, created_at DESC, id DESC` (`WHERE deleted_at IS NULL`)
  - `ix_users_admin_list_created_id`: `created_at DESC, id DESC`
  - `ix_users_admin_role_created_id`: `users.role, created_at DESC, id DESC` (`WHERE deleted_at IS NULL`)
  - `ix_users_email_trgm`: `users.email` (`USING gin`; `WHERE deleted_at IS NULL`; `operator classes {'email': 'gin_trgm_ops'}`)
  - `ix_users_first_name_trgm`: `users.first_name` (`USING gin`; `WHERE deleted_at IS NULL`; `operator classes {'first_name': 'gin_trgm_ops'}`)
  - `ix_users_last_name_trgm`: `users.last_name` (`USING gin`; `WHERE deleted_at IS NULL`; `operator classes {'last_name': 'gin_trgm_ops'}`)
  - `ix_users_platform_notice_active_id`: `users.id` (`WHERE account_status = 'active' AND deleted_at IS NULL`)

### `user_settings`

Per-user preferences and selected location. Sources: [model](../../backend/models/user_settings_model.py), [canonical migration](../../backend/alembic/versions/0010_create_user_settings_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `user_id` | `UUID` | No | — | PK; FK → `users.id` |
| `push_notifications_enabled` | `BOOLEAN` | No | server `false` | — |
| `email_notifications_enabled` | `BOOLEAN` | No | server `false` | — |
| `sms_notifications_enabled` | `BOOLEAN` | No | server `false` | — |
| `marketing_opt_in` | `BOOLEAN` | No | server `false` | — |
| `location_permission_status` | `VARCHAR(20)` | No | server `'unknown'` | — |
| `selected_city` | `VARCHAR(120)` | Yes | — | — |
| `selected_state` | `VARCHAR(120)` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `user_id`.
- **Foreign keys:** `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `location_permission_status`: `unknown`, `allowed`, `denied`, `skipped`.
- **CHECK constraints:**
  - `ck_user_settings_location_permission_status`: `location_permission_status IN ('unknown', 'allowed', 'denied', 'skipped')`
- **Indexes:** None beyond the primary-key/unique-constraint backing indexes.

### `user_stats`

Stored player and hosting statistics. Sources: [model](../../backend/models/user_stats_model.py), [canonical migration](../../backend/alembic/versions/0011_create_user_stats_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `user_id` | `UUID` | No | — | PK; FK → `users.id` |
| `games_played_count` | `INTEGER` | No | server `0` | — |
| `games_hosted_completed_count` | `INTEGER` | No | server `0` | — |
| `no_show_count` | `INTEGER` | No | server `0` | — |
| `late_cancel_count` | `INTEGER` | No | server `0` | — |
| `host_cancel_count` | `INTEGER` | No | server `0` | — |
| `last_calculated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `user_id`.
- **Foreign keys:** `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:**
  - `ck_user_stats_games_hosted_completed_count`: `games_hosted_completed_count >= 0`
  - `ck_user_stats_games_played_count`: `games_played_count >= 0`
  - `ck_user_stats_host_cancel_count`: `host_cancel_count >= 0`
  - `ck_user_stats_late_cancel_count`: `late_cancel_count >= 0`
  - `ck_user_stats_no_show_count`: `no_show_count >= 0`
- **Indexes:** None beyond the primary-key/unique-constraint backing indexes.

### `user_payment_methods`

Saved payment-method references and default-card state. Sources: [model](../../backend/models/user_payment_method_model.py), [canonical migration](../../backend/alembic/versions/0009_create_user_payment_methods_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `stripe_customer_id` | `VARCHAR(255)` | No | — | — |
| `stripe_payment_method_id` | `VARCHAR(255)` | No | — | column UNIQUE |
| `card_fingerprint` | `VARCHAR(255)` | No | — | — |
| `card_brand` | `VARCHAR(50)` | No | — | — |
| `card_last4` | `VARCHAR(4)` | No | — | — |
| `exp_month` | `SMALLINT` | No | — | — |
| `exp_year` | `SMALLINT` | No | — | — |
| `method_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `is_default` | `BOOLEAN` | No | server `false` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `detached_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** unnamed: `stripe_payment_method_id`.
- **Other table relationships:** Referenced by `community_publish_attempts`, `payment_method_operations`, `waitlist_entries`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `method_status`: `active`, `detached`, `expired`.
- **CHECK constraints:**
  - `ck_user_payment_methods_card_last4`: `char_length(card_last4) = 4`
  - `ck_user_payment_methods_default_requires_active`: `(is_default = false OR method_status = 'active')`
  - `ck_user_payment_methods_detached_at_status`: `(method_status = 'detached' OR detached_at IS NULL)`
  - `ck_user_payment_methods_exp_month`: `exp_month BETWEEN 1 AND 12`
  - `ck_user_payment_methods_method_status`: `method_status IN ('active', 'detached', 'expired')`
- **Indexes:**
  - `ix_user_payment_methods_one_active_default_per_user`: `user_payment_methods.user_id` (`UNIQUE`; `WHERE is_default = true AND method_status = 'active'`)
  - `ix_user_payment_methods_user_card_fingerprint`: `user_payment_methods.user_id, user_payment_methods.card_fingerprint` (`UNIQUE`)
  - `ix_user_payment_methods_user_id`: `user_payment_methods.user_id`
  - `ix_user_payment_methods_user_status`: `user_payment_methods.user_id, user_payment_methods.method_status`

### `policy_documents`

Versioned legal/policy document records. Sources: [model](../../backend/models/policy_document_model.py), [canonical migration](../../backend/alembic/versions/0002_create_policy_documents_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `policy_type` | `VARCHAR(50)` | No | — | — |
| `version` | `VARCHAR(30)` | No | — | — |
| `title` | `VARCHAR(150)` | No | — | — |
| `content_url` | `TEXT` | Yes | — | — |
| `content_text` | `TEXT` | Yes | — | — |
| `effective_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `retired_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `is_active` | `BOOLEAN` | No | server `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** None.
- **Unique constraints:** `uq_policy_documents_policy_type_version`: `policy_type, version`.
- **Other table relationships:** Referenced by `booking_policy_acceptances`, `policy_acceptances`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `policy_type`: `terms_of_service`, `privacy_policy`, `refund_policy`, `player_cancellation_policy`, `community_host_agreement`, `official_game_rules`.
- **CHECK constraints:**
  - `ck_policy_documents_content_required`: `(content_url IS NOT NULL AND char_length(btrim(content_url)) > 0) OR (content_text IS NOT NULL AND char_length(btrim(content_text)) > 0)`
  - `ck_policy_documents_policy_type`: `policy_type IN ('terms_of_service', 'privacy_policy', 'refund_policy', 'player_cancellation_policy', 'community_host_agreement', 'official_game_rules')`
  - `ck_policy_documents_retired_after_effective`: `(retired_at IS NULL OR retired_at > effective_at)`
  - `ck_policy_documents_title_not_empty`: `char_length(btrim(title)) > 0`
  - `ck_policy_documents_version_not_empty`: `char_length(btrim(version)) > 0`
- **Indexes:**
  - `ix_policy_documents_effective_at`: `policy_documents.effective_at`
  - `ix_policy_documents_is_active`: `policy_documents.is_active`
  - `ix_policy_documents_policy_type`: `policy_documents.policy_type`

### `policy_acceptances`

Account-level acceptance of policy versions. Sources: [model](../../backend/models/policy_acceptance_model.py), [canonical migration](../../backend/alembic/versions/0007_create_policy_acceptances_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `policy_document_id` | `UUID` | No | — | FK → `policy_documents.id` |
| `accepted_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `ip_address` | `VARCHAR(45)` | Yes | — | — |
| `user_agent` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `policy_document_id` → `policy_documents.id` (ON DELETE RESTRICT); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_policy_acceptances_user_id_policy_document_id`: `user_id, policy_document_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_policy_acceptances_accepted_at`: `policy_acceptances.accepted_at`
  - `ix_policy_acceptances_policy_document_id`: `policy_acceptances.policy_document_id`
  - `ix_policy_acceptances_user_id`: `policy_acceptances.user_id`

## Games, venues, and hosting

### `venues`

Venue identity, location, ownership, and approval state. Sources: [model](../../backend/models/venue_model.py), [canonical migration](../../backend/alembic/versions/0012_create_venues_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `name` | `VARCHAR(150)` | No | — | — |
| `address_line_1` | `VARCHAR(200)` | No | — | — |
| `city` | `VARCHAR(100)` | No | — | — |
| `state` | `VARCHAR(100)` | No | — | — |
| `postal_code` | `VARCHAR(20)` | No | — | — |
| `country_code` | `CHAR(2)` | No | server `'US'` | — |
| `neighborhood` | `VARCHAR(120)` | Yes | — | — |
| `latitude` | `NUMERIC(9, 6)` | Yes | — | — |
| `longitude` | `NUMERIC(9, 6)` | Yes | — | — |
| `external_place_id` | `VARCHAR(255)` | Yes | — | — |
| `venue_status` | `VARCHAR(30)` | No | server `'pending_review'` | — |
| `created_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `approved_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `approved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `is_active` | `BOOLEAN` | No | server `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `approved_by_user_id` → `users.id` (ON DELETE SET NULL); `created_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `games`, `support_flags`, `venue_approval_requests`, `venue_images`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `venue_status`: `pending_review`, `approved`, `rejected`, `inactive`.
- **CHECK constraints:**
  - `ck_venues_country_code`: `char_length(country_code) = 2`
  - `ck_venues_latitude`: `(latitude IS NULL OR latitude BETWEEN -90 AND 90)`
  - `ck_venues_longitude`: `(longitude IS NULL OR longitude BETWEEN -180 AND 180)`
  - `ck_venues_venue_status`: `venue_status IN ('pending_review', 'approved', 'rejected', 'inactive')`
- **Indexes:**
  - `ix_venues_approved_by_user_id`: `venues.approved_by_user_id`
  - `ix_venues_city_state`: `venues.city, venues.state`
  - `ix_venues_created_by_user_id`: `venues.created_by_user_id`
  - `ix_venues_external_place_id`: `venues.external_place_id`
  - `ix_venues_is_active`: `venues.is_active`
  - `ix_venues_venue_status`: `venues.venue_status`

### `venue_images`

Images attached to venues. Sources: [model](../../backend/models/venue_image_model.py), [canonical migration](../../backend/alembic/versions/0020_create_venue_images_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `venue_id` | `UUID` | No | — | FK → `venues.id` |
| `uploaded_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `storage_provider` | `VARCHAR(30)` | No | server `'r2'` | — |
| `storage_object_key` | `TEXT` | No | — | — |
| `storage_bucket` | `VARCHAR(120)` | No | — | — |
| `storage_account_id` | `VARCHAR(120)` | No | — | — |
| `content_type` | `VARCHAR(120)` | No | — | — |
| `size_bytes` | `INTEGER` | No | — | — |
| `etag` | `VARCHAR(255)` | Yes | — | — |
| `publication_object_key` | `TEXT` | Yes | — | — |
| `publication_content_type` | `VARCHAR(120)` | Yes | — | — |
| `publication_size_bytes` | `INTEGER` | Yes | — | — |
| `publication_etag` | `VARCHAR(255)` | Yes | — | — |
| `image_role` | `VARCHAR(30)` | No | server `'gallery'` | — |
| `image_status` | `VARCHAR(30)` | No | server `'pending_upload'` | — |
| `is_primary` | `BOOLEAN` | No | server `false` | — |
| `sort_order` | `INTEGER` | No | server `0` | — |
| `alt_text` | `VARCHAR(280)` | Yes | — | — |
| `caption` | `VARCHAR(280)` | Yes | — | — |
| `upload_requested_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `upload_completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `upload_expires_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `uploaded_by_user_id` → `users.id` (ON DELETE SET NULL); `venue_id` → `venues.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `content_type`: see CHECK constraints below; `publication_content_type`: `image/jpeg`, `image/png`, `image/webp`; `image_role`: `card`, `gallery`; `image_status`: `pending_upload`, `active`, `hidden`, `removed`.
- **CHECK constraints:**
  - `ck_venue_images_content_type_not_empty`: `char_length(btrim(content_type)) > 0`
  - `ck_venue_images_image_role`: `image_role IN ('card', 'gallery')`
  - `ck_venue_images_image_status`: `image_status IN ('pending_upload', 'active', 'hidden', 'removed')`
  - `ck_venue_images_pending_upload_intent`: `image_status <> 'pending_upload' OR (upload_expires_at IS NOT NULL AND upload_completed_at IS NULL)`
  - `ck_venue_images_publication_content_type`: `publication_content_type IS NULL OR publication_content_type IN ('image/jpeg', 'image/png', 'image/webp')`
  - `ck_venue_images_publication_etag_not_empty`: `publication_etag IS NULL OR char_length(btrim(publication_etag)) > 0`
  - `ck_venue_images_publication_object_key_not_empty`: `publication_object_key IS NULL OR char_length(btrim(publication_object_key)) > 0`
  - `ck_venue_images_publication_size_bytes`: `publication_size_bytes IS NULL OR publication_size_bytes BETWEEN 1 AND 8388608`
  - `ck_venue_images_publication_status`: `((image_status = 'pending_upload' AND publication_object_key IS NULL) OR (image_status IN ('active', 'hidden') AND publication_object_key IS NOT NULL) OR image_status = 'removed')`
  - `ck_venue_images_publication_tuple_complete`: `((publication_object_key IS NULL AND publication_content_type IS NULL AND publication_size_bytes IS NULL AND publication_etag IS NULL AND upload_completed_at IS NULL) OR (publication_object_key IS NOT NULL AND publication_content_type IS NOT NULL AND publication_size_bytes IS NOT NULL AND publication_etag IS NOT NULL AND upload_completed_at IS NOT NULL))`
  - `ck_venue_images_size_bytes_positive`: `size_bytes > 0`
  - `ck_venue_images_sort_order_non_negative`: `sort_order >= 0`
  - `ck_venue_images_storage_account_id_not_empty`: `char_length(btrim(storage_account_id)) > 0`
  - `ck_venue_images_storage_bucket_not_empty`: `char_length(btrim(storage_bucket)) > 0`
  - `ck_venue_images_storage_object_key_not_empty`: `char_length(btrim(storage_object_key)) > 0`
  - `ck_venue_images_storage_provider_not_empty`: `char_length(btrim(storage_provider)) > 0`
- **Indexes:**
  - `ix_venue_images_image_status`: `venue_images.image_status`
  - `ix_venue_images_sort_order`: `venue_images.sort_order`
  - `ix_venue_images_uploaded_by_user_id`: `venue_images.uploaded_by_user_id`
  - `ix_venue_images_venue_id`: `venue_images.venue_id`
  - `ix_venue_images_venue_id_image_status_sort_order`: `venue_images.venue_id, venue_images.image_status, venue_images.sort_order`
  - `uq_venue_images_one_active_primary_per_venue`: `venue_images.venue_id` (`UNIQUE`; `WHERE is_primary = true AND image_status = 'active' AND deleted_at IS NULL`)
  - `uq_venue_images_publication_object_key`: `venue_images.publication_object_key` (`UNIQUE`; `WHERE publication_object_key IS NOT NULL`)
  - `uq_venue_images_storage_object_key`: `venue_images.storage_object_key` (`UNIQUE`)

### `venue_approval_requests`

Requests and decisions for venue approval. Sources: [model](../../backend/models/venue_approval_request_model.py), [canonical migration](../../backend/alembic/versions/0019_create_venue_approval_requests_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `submitted_by_user_id` | `UUID` | No | — | FK → `users.id` |
| `venue_id` | `UUID` | Yes | — | FK → `venues.id` |
| `requested_name` | `VARCHAR(150)` | No | — | — |
| `requested_address_line_1` | `VARCHAR(200)` | No | — | — |
| `requested_city` | `VARCHAR(100)` | No | — | — |
| `requested_state` | `VARCHAR(100)` | No | — | — |
| `requested_postal_code` | `VARCHAR(20)` | No | — | — |
| `requested_country_code` | `CHAR(2)` | No | server `'US'` | — |
| `request_status` | `VARCHAR(30)` | No | server `'pending_review'` | — |
| `reviewed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `reviewed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `review_notes` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `reviewed_by_user_id` → `users.id` (ON DELETE SET NULL); `submitted_by_user_id` → `users.id` (ON DELETE RESTRICT); `venue_id` → `venues.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `request_status`: `pending_review`, `approved`, `rejected`, `inactive`.
- **CHECK constraints:**
  - `ck_venue_approval_requests_approved_requires_venue_id`: `(request_status <> 'approved' OR venue_id IS NOT NULL)`
  - `ck_venue_approval_requests_request_status`: `request_status IN ('pending_review', 'approved', 'rejected', 'inactive')`
  - `ck_venue_approval_requests_requested_country_code`: `char_length(requested_country_code) = 2`
  - `ck_venue_approval_requests_reviewed_status_requires_reviewed_at`: `request_status NOT IN ('approved', 'rejected', 'inactive') OR reviewed_at IS NOT NULL`
- **Indexes:**
  - `ix_venue_approval_requests_created_at`: `venue_approval_requests.created_at`
  - `ix_venue_approval_requests_request_status`: `venue_approval_requests.request_status`
  - `ix_venue_approval_requests_request_status_created_at`: `venue_approval_requests.request_status, venue_approval_requests.created_at`
  - `ix_venue_approval_requests_reviewed_by_user_id`: `venue_approval_requests.reviewed_by_user_id`
  - `ix_venue_approval_requests_submitted_by_user_id`: `venue_approval_requests.submitted_by_user_id`
  - `ix_venue_approval_requests_submitted_by_user_id_created_at`: `venue_approval_requests.submitted_by_user_id, venue_approval_requests.created_at`
  - `ix_venue_approval_requests_venue_id`: `venue_approval_requests.venue_id`

### `games`

Core official and community game schedule, listing, and lifecycle record. Sources: [model](../../backend/models/game_model.py), [canonical migration](../../backend/alembic/versions/0013_create_games_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_type` | `VARCHAR(20)` | No | — | — |
| `payment_collection_type` | `VARCHAR(30)` | No | — | — |
| `publish_status` | `VARCHAR(20)` | No | server `'draft'` | — |
| `game_status` | `VARCHAR(20)` | No | server `'active'` | — |
| `public_visibility_status` | `VARCHAR(20)` | No | server `'visible'` | — |
| `join_enforcement_status` | `VARCHAR(20)` | No | server `'open'` | — |
| `title` | `VARCHAR(150)` | No | — | — |
| `description` | `TEXT` | Yes | — | — |
| `venue_id` | `UUID` | No | — | FK → `venues.id` |
| `venue_name_snapshot` | `VARCHAR(150)` | No | — | — |
| `address_snapshot` | `TEXT` | No | — | — |
| `city_snapshot` | `VARCHAR(100)` | No | — | — |
| `state_snapshot` | `VARCHAR(100)` | No | — | — |
| `neighborhood_snapshot` | `VARCHAR(120)` | Yes | — | — |
| `host_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `created_by_user_id` | `UUID` | No | — | FK → `users.id` |
| `starts_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `ends_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `starts_on_local` | `DATE` | No | — | — |
| `timezone` | `VARCHAR(60)` | No | server `'America/Chicago'` | — |
| `sport_type` | `VARCHAR(50)` | No | server `'soccer'` | — |
| `format_label` | `VARCHAR(20)` | No | — | — |
| `game_player_group` | `VARCHAR(30)` | No | server `'coed'` | — |
| `skill_level` | `VARCHAR(30)` | No | server `'any'` | — |
| `environment_type` | `VARCHAR(20)` | No | — | — |
| `total_spots` | `INTEGER` | No | — | — |
| `price_per_player_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `minimum_age` | `INTEGER` | Yes | — | — |
| `allow_guests` | `BOOLEAN` | No | server `true` | — |
| `max_guests_per_booking` | `INTEGER` | No | server `2` | — |
| `host_guest_max` | `INTEGER` | No | server `0` | — |
| `waitlist_enabled` | `BOOLEAN` | No | server `true` | — |
| `is_chat_enabled` | `BOOLEAN` | No | server `true` | — |
| `policy_mode` | `VARCHAR(30)` | No | — | — |
| `custom_rules_text` | `TEXT` | Yes | — | — |
| `custom_cancellation_text` | `TEXT` | Yes | — | — |
| `game_notes` | `TEXT` | Yes | — | — |
| `parking_notes` | `TEXT` | Yes | — | — |
| `published_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `cancellation_source` | `VARCHAR(20)` | Yes | — | — |
| `cancel_reason` | `TEXT` | Yes | — | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `completed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `cancelled_by_user_id` → `users.id` (ON DELETE RESTRICT); `completed_by_user_id` → `users.id` (ON DELETE RESTRICT); `created_by_user_id` → `users.id` (ON DELETE RESTRICT); `host_user_id` → `users.id` (ON DELETE RESTRICT); `venue_id` → `venues.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_financial_outcomes`, `admin_review_cases`, `admin_review_signals`, `admin_target_notices`, `bookings`, `community_game_details`, `community_publish_attempts`, `game_chats`, `game_credit_usage`, `game_credits`, `game_images`, `game_participants`, `game_status_history`, `host_publish_entitlements`, `host_publish_fees`, `money_issues`, `notifications`, `payments`, `support_flags`, `waitlist_entries`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `game_type`: `official`, `community`; `payment_collection_type`: `in_app`, `external_host`, `none`; `publish_status`: `draft`, `published`, `archived`; `game_status`: `active`, `completed`, `cancelled`, `expired`, `removed`; `public_visibility_status`: `visible`, `hidden`; `join_enforcement_status`: `open`, `paused`; `sport_type`: no table-local value CHECK; application-defined or historical value; `environment_type`: `indoor`, `outdoor`; `policy_mode`: `official_standard`, `custom_hosted`.
- **CHECK constraints:**
  - `ck_games_cancellation_source`: `(cancellation_source IS NULL OR cancellation_source IN ('host', 'admin', 'system'))`
  - `ck_games_cancellation_source_requires_cancelled`: `(cancellation_source IS NULL OR game_status = 'cancelled')`
  - `ck_games_cancelled_requires_cancelled_at`: `(game_status <> 'cancelled' OR cancelled_at IS NOT NULL)`
  - `ck_games_community_payment_collection`: `(game_type <> 'community' OR payment_collection_type IN ('external_host', 'none'))`
  - `ck_games_community_policy_mode`: `(game_type <> 'community' OR policy_mode = 'custom_hosted')`
  - `ck_games_community_requires_host_user`: `(game_type <> 'community' OR host_user_id IS NOT NULL)`
  - `ck_games_completed_requires_completed_at`: `(game_status <> 'completed' OR completed_at IS NOT NULL)`
  - `ck_games_currency`: `currency = 'USD'`
  - `ck_games_ends_after_starts`: `ends_at > starts_at`
  - `ck_games_environment_type`: `environment_type IN ('indoor', 'outdoor')`
  - `ck_games_game_player_group`: `game_player_group IN ('men', 'women', 'coed')`
  - `ck_games_game_status`: `game_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')`
  - `ck_games_game_type`: `game_type IN ('official', 'community')`
  - `ck_games_host_guest_max`: `host_guest_max >= 0`
  - `ck_games_join_enforcement_status`: `join_enforcement_status IN ('open', 'paused')`
  - `ck_games_max_guests_per_booking`: `max_guests_per_booking >= 0`
  - `ck_games_minimum_age`: `(minimum_age IS NULL OR minimum_age >= 13)`
  - `ck_games_no_payment_requires_free`: `(payment_collection_type <> 'none' OR price_per_player_cents = 0)`
  - `ck_games_official_host_guest_max_zero`: `(game_type <> 'official' OR host_guest_max = 0)`
  - `ck_games_official_minimum_age_null`: `(game_type <> 'official' OR minimum_age IS NULL)`
  - `ck_games_official_no_custom_cancellation`: `(game_type <> 'official' OR custom_cancellation_text IS NULL)`
  - `ck_games_official_no_custom_rules`: `(game_type <> 'official' OR custom_rules_text IS NULL)`
  - `ck_games_official_payment_collection`: `(game_type <> 'official' OR payment_collection_type = 'in_app')`
  - `ck_games_official_policy_mode`: `(game_type <> 'official' OR policy_mode = 'official_standard')`
  - `ck_games_payment_collection_type`: `payment_collection_type IN ('in_app', 'external_host', 'none')`
  - `ck_games_policy_mode`: `policy_mode IN ('official_standard', 'custom_hosted')`
  - `ck_games_price_per_player_cents`: `price_per_player_cents >= 0`
  - `ck_games_public_visibility_status`: `public_visibility_status IN ('visible', 'hidden')`
  - `ck_games_publish_status`: `publish_status IN ('draft', 'published', 'archived')`
  - `ck_games_published_requires_published_at`: `(publish_status <> 'published' OR published_at IS NOT NULL)`
  - `ck_games_skill_level`: `skill_level IN ('any', 'beginner', 'recreational', 'intermediate', 'advanced', 'competitive')`
  - `ck_games_total_spots`: `total_spots > 0`
- **Indexes:**
  - `ix_games_admin_community_city_trgm`: `games.city_snapshot` (`USING gin`; `WHERE game_type = 'community' AND deleted_at IS NULL`; `operator classes {'city_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_admin_community_state_trgm`: `games.state_snapshot` (`USING gin`; `WHERE game_type = 'community' AND deleted_at IS NULL`; `operator classes {'state_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_admin_community_status_local_starts_created_id`: `games.game_status, games.public_visibility_status, games.join_enforcement_status, games.publish_status, games.starts_on_local, games.starts_at, games.created_at, games.id` (`WHERE game_type = 'community' AND deleted_at IS NULL`)
  - `ix_games_admin_community_title_trgm`: `games.title` (`USING gin`; `WHERE game_type = 'community' AND deleted_at IS NULL`; `operator classes {'title': 'gin_trgm_ops'}`)
  - `ix_games_admin_community_venue_name_trgm`: `games.venue_name_snapshot` (`USING gin`; `WHERE game_type = 'community' AND deleted_at IS NULL`; `operator classes {'venue_name_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_admin_official_city_trgm`: `games.city_snapshot` (`USING gin`; `WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`; `operator classes {'city_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_admin_official_state_trgm`: `games.state_snapshot` (`USING gin`; `WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`; `operator classes {'state_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_admin_official_status_local_starts_created_id`: `games.game_status, games.starts_on_local, games.starts_at, games.created_at, games.id` (`WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`)
  - `ix_games_admin_official_status_starts_created_id`: `games.game_status, games.starts_at, games.created_at, games.id` (`WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`)
  - `ix_games_admin_official_title_trgm`: `games.title` (`USING gin`; `WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`; `operator classes {'title': 'gin_trgm_ops'}`)
  - `ix_games_admin_official_venue_name_trgm`: `games.venue_name_snapshot` (`USING gin`; `WHERE game_type = 'official' AND publish_status = 'published' AND deleted_at IS NULL`; `operator classes {'venue_name_snapshot': 'gin_trgm_ops'}`)
  - `ix_games_browse_cards_local_starts_created_id`: `games.starts_on_local, games.starts_at, games.created_at, games.id` (`WHERE publish_status = 'published' AND game_status = 'active' AND public_visibility_status = 'visible' AND join_enforcement_status = 'open' AND deleted_at IS NULL`)
  - `ix_games_created_by_user_id`: `games.created_by_user_id`
  - `ix_games_host_cards_starts_created_id`: `games.host_user_id, games.starts_at, games.created_at, games.id` (`WHERE publish_status = 'published' AND deleted_at IS NULL`)
  - `ix_games_host_user_id`: `games.host_user_id`
  - `ix_games_starts_at`: `games.starts_at`
  - `ix_games_starts_on_local`: `games.starts_on_local`
  - `ix_games_venue_id`: `games.venue_id`
  - `ux_games_one_active_community_game_per_host_date`: `games.host_user_id, games.starts_on_local` (`UNIQUE`; `WHERE game_type = 'community' AND publish_status = 'published' AND game_status = 'active' AND deleted_at IS NULL`)

### `community_game_details`

Community-specific game content and host instructions. Sources: [model](../../backend/models/community_game_detail_model.py), [canonical migration](../../backend/alembic/versions/0022_create_community_game_details_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `payment_methods_snapshot` | `JSONB` | No | server `'[]'::jsonb` | — |
| `payment_instructions_snapshot` | `TEXT` | Yes | — | — |
| `payment_text_moderation_status` | `VARCHAR(30)` | No | server `'visible'` | — |
| `payment_text_hidden_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `payment_text_hidden_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `payment_text_hidden_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `game_id` → `games.id` (ON DELETE RESTRICT); `payment_text_hidden_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** `uq_community_game_details_game_id`: `game_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `payment_text_moderation_status`: `visible`, `hidden`.
- **CHECK constraints:**
  - `ck_community_game_details_hidden_requires_metadata`: `payment_text_moderation_status != 'hidden' OR (payment_text_hidden_at IS NOT NULL AND NULLIF(BTRIM(payment_text_hidden_reason), '') IS NOT NULL)`
  - `ck_community_game_details_payment_methods_array`: `jsonb_typeof(payment_methods_snapshot) = 'array'`
  - `ck_community_game_details_payment_text_moderation_status`: `payment_text_moderation_status IN ('visible', 'hidden')`
- **Indexes:**
  - `ix_community_game_details_game_id`: `community_game_details.game_id`
  - `ix_community_game_details_payment_text_moderation_status`: `community_game_details.payment_text_moderation_status`

### `game_images`

Images attached to games. Sources: [model](../../backend/models/game_image_model.py), [canonical migration](../../backend/alembic/versions/0024_create_game_images_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `uploaded_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `image_url` | `TEXT` | No | — | — |
| `image_role` | `VARCHAR(30)` | No | server `'gallery'` | — |
| `image_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `is_primary` | `BOOLEAN` | No | server `false` | — |
| `sort_order` | `INTEGER` | No | server `0` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `deleted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `game_id` → `games.id` (ON DELETE CASCADE); `uploaded_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `image_role`: `card`, `gallery`; `image_status`: `active`, `hidden`, `removed`.
- **CHECK constraints:**
  - `ck_game_images_image_role`: `image_role IN ('card', 'gallery')`
  - `ck_game_images_image_status`: `image_status IN ('active', 'hidden', 'removed')`
  - `ck_game_images_image_url_not_empty`: `char_length(btrim(image_url)) > 0`
  - `ck_game_images_sort_order_non_negative`: `sort_order >= 0`
- **Indexes:**
  - `ix_game_images_game_id`: `game_images.game_id`
  - `ix_game_images_game_id_image_status_sort_order`: `game_images.game_id, game_images.image_status, game_images.sort_order`
  - `ix_game_images_image_status`: `game_images.image_status`
  - `ix_game_images_sort_order`: `game_images.sort_order`
  - `ix_game_images_uploaded_by_user_id`: `game_images.uploaded_by_user_id`
  - `uq_game_images_one_active_primary_per_game`: `game_images.game_id` (`UNIQUE`; `WHERE is_primary = true AND image_status = 'active' AND deleted_at IS NULL`)

### `game_status_history`

Recorded game lifecycle changes. Sources: [model](../../backend/models/game_status_history_model.py), [canonical migration](../../backend/alembic/versions/0025_create_game_status_history_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `old_publish_status` | `VARCHAR(30)` | Yes | — | — |
| `new_publish_status` | `VARCHAR(30)` | No | — | — |
| `old_game_status` | `VARCHAR(30)` | Yes | — | — |
| `new_game_status` | `VARCHAR(30)` | No | — | — |
| `changed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `change_source` | `VARCHAR(30)` | No | server `'user'` | — |
| `change_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `changed_by_user_id` → `users.id` (ON DELETE SET NULL); `game_id` → `games.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `old_publish_status`: `draft`, `published`, `archived`; `new_publish_status`: `draft`, `published`, `archived`; `old_game_status`: `active`, `completed`, `cancelled`, `expired`, `removed`; `new_game_status`: `active`, `completed`, `cancelled`, `expired`, `removed`.
- **CHECK constraints:**
  - `ck_game_status_history_change_source`: `change_source IN ('user', 'host', 'admin', 'system', 'payment_webhook', 'scheduled_job')`
  - `ck_game_status_history_new_game_status`: `new_game_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')`
  - `ck_game_status_history_new_publish_status`: `new_publish_status IN ('draft', 'published', 'archived')`
  - `ck_game_status_history_old_game_status`: `(old_game_status IS NULL OR old_game_status IN ('active', 'completed', 'cancelled', 'expired', 'removed'))`
  - `ck_game_status_history_old_publish_status`: `(old_publish_status IS NULL OR old_publish_status IN ('draft', 'published', 'archived'))`
- **Indexes:**
  - `ix_game_status_history_change_source`: `game_status_history.change_source`
  - `ix_game_status_history_changed_by_user_id`: `game_status_history.changed_by_user_id`
  - `ix_game_status_history_created_at`: `game_status_history.created_at`
  - `ix_game_status_history_game_id`: `game_status_history.game_id`
  - `ix_game_status_history_game_id_created_at`: `game_status_history.game_id, game_status_history.created_at`

### `host_publish_entitlements`

Entitlements to publish community games. Sources: [model](../../backend/models/host_publish_entitlement_model.py), [canonical migration](../../backend/alembic/versions/0047_create_host_publish_entitlements_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `host_user_id` | `UUID` | No | — | FK → `users.id` |
| `entitlement_type` | `VARCHAR(40)` | No | — | — |
| `status` | `VARCHAR(30)` | No | — | — |
| `source` | `VARCHAR(40)` | No | — | — |
| `source_admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `source_financial_outcome_id` | `UUID` | Yes | — | — |
| `reserved_by_attempt_id` | `UUID` | Yes | — | FK → `community_publish_attempts.id` |
| `used_by_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `used_by_host_publish_fee_id` | `UUID` | Yes | — | FK → `host_publish_fees.id` |
| `used_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `revoked_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `revoked_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `revoke_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `host_user_id` → `users.id` (ON DELETE RESTRICT); `reserved_by_attempt_id` → `community_publish_attempts.id` (ON DELETE SET NULL); `revoked_by_user_id` → `users.id` (ON DELETE SET NULL); `source_admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `used_by_game_id` → `games.id` (ON DELETE SET NULL); `used_by_host_publish_fee_id` → `host_publish_fees.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_financial_outcomes`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `entitlement_type`: `first_free`, `admin_grant`, `refund_replacement`, `courtesy`; `status`: `available`, `reserved`, `used`, `revoked`, `expired`.
- **CHECK constraints:**
  - `ck_host_publish_entitlements_reserved_requirements`: `status <> 'reserved' OR (reserved_by_attempt_id IS NOT NULL AND used_at IS NULL)`
  - `ck_host_publish_entitlements_revoked_requirements`: `status <> 'revoked' OR (revoked_at IS NOT NULL AND NULLIF(BTRIM(revoke_reason), '') IS NOT NULL)`
  - `ck_host_publish_entitlements_source`: `source IN ('system', 'admin', 'financial_outcome')`
  - `ck_host_publish_entitlements_status`: `status IN ('available', 'reserved', 'used', 'revoked', 'expired')`
  - `ck_host_publish_entitlements_type`: `entitlement_type IN ('first_free', 'admin_grant', 'refund_replacement', 'courtesy')`
  - `ck_host_publish_entitlements_used_requirements`: `status <> 'used' OR (used_by_game_id IS NOT NULL AND used_by_host_publish_fee_id IS NOT NULL AND used_at IS NOT NULL)`
- **Indexes:**
  - `ix_host_publish_entitlements_host_status`: `host_publish_entitlements.host_user_id, host_publish_entitlements.status`
  - `ix_host_publish_entitlements_host_user_id`: `host_publish_entitlements.host_user_id`
  - `ix_host_publish_entitlements_reserved_by_attempt_id`: `host_publish_entitlements.reserved_by_attempt_id`
  - `ix_host_publish_entitlements_status`: `host_publish_entitlements.status`
  - `ix_host_publish_entitlements_used_by_fee_id`: `host_publish_entitlements.used_by_host_publish_fee_id`
  - `ix_host_publish_entitlements_used_by_game_id`: `host_publish_entitlements.used_by_game_id`
  - `ux_host_publish_entitlements_one_first_free_per_host`: `host_publish_entitlements.host_user_id` (`UNIQUE`; `WHERE entitlement_type = 'first_free'`)
  - `ux_host_publish_entitlements_source_financial_outcome_id`: `host_publish_entitlements.source_financial_outcome_id` (`UNIQUE`; `WHERE source_financial_outcome_id IS NOT NULL`)

### `host_publish_fees`

Charges and outcomes for community-game publication. Sources: [model](../../backend/models/host_publish_fee_model.py), [canonical migration](../../backend/alembic/versions/0042_create_host_publish_fees_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `host_user_id` | `UUID` | No | — | FK → `users.id` |
| `payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `fee_status` | `VARCHAR(30)` | No | — | — |
| `waiver_reason` | `VARCHAR(30)` | No | server `'none'` | — |
| `paid_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `game_id` → `games.id` (ON DELETE RESTRICT); `host_user_id` → `users.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_host_publish_fees_game_id`: `game_id`; `uq_host_publish_fees_payment_id`: `payment_id`.
- **Other table relationships:** Referenced by `admin_financial_outcomes`, `host_publish_entitlements`, `refunds`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `fee_status`: `pending`, `paid`, `waived`, `failed`, `refunded`.
- **CHECK constraints:**
  - `ck_host_publish_fees_amount_cents`: `amount_cents >= 0`
  - `ck_host_publish_fees_currency`: `currency = 'USD'`
  - `ck_host_publish_fees_fee_status`: `fee_status IN ('pending', 'paid', 'waived', 'failed', 'refunded')`
  - `ck_host_publish_fees_paid_requires_payment`: `fee_status <> 'paid' OR (payment_id IS NOT NULL AND paid_at IS NOT NULL AND amount_cents > 0)`
  - `ck_host_publish_fees_waived_requirements`: `fee_status <> 'waived' OR (amount_cents = 0 AND waiver_reason <> 'none' AND payment_id IS NULL)`
  - `ck_host_publish_fees_waiver_reason`: `waiver_reason IN ('none', 'first_game_free', 'admin_comp')`
- **Indexes:**
  - `ix_host_publish_fees_fee_status`: `host_publish_fees.fee_status`
  - `ix_host_publish_fees_game_id`: `host_publish_fees.game_id`
  - `ix_host_publish_fees_host_user_id`: `host_publish_fees.host_user_id`
  - `ix_host_publish_fees_payment_id`: `host_publish_fees.payment_id`

### `community_publish_attempts`

Attempts to complete paid community publication. Sources: [model](../../backend/models/community_publish_attempt_model.py), [canonical migration](../../backend/alembic/versions/0038_create_community_publish_attempts_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `host_user_id` | `UUID` | No | — | FK → `users.id` |
| `payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `created_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `attempt_status` | `VARCHAR(30)` | No | — | — |
| `publish_payload` | `JSONB` | No | — | — |
| `payment_method_id` | `UUID` | Yes | — | FK → `user_payment_methods.id` |
| `starts_on_local` | `DATE` | No | — | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `failure_code` | `VARCHAR(100)` | Yes | — | — |
| `failure_message` | `TEXT` | Yes | — | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `created_game_id` → `games.id` (ON DELETE RESTRICT); `host_user_id` → `users.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE RESTRICT); `payment_method_id` → `user_payment_methods.id` (ON DELETE SET NULL).
- **Unique constraints:** `uq_community_publish_attempts_created_game_id`: `created_game_id`; `uq_community_publish_attempts_payment_id`: `payment_id`.
- **Other table relationships:** Referenced by `host_publish_entitlements`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `attempt_status`: `requires_payment_method`, `requires_action`, `processing`, `succeeded`, `failed`, `cancelled`, `expired`.
- **CHECK constraints:**
  - `ck_community_publish_attempts_amount_cents`: `amount_cents >= 0`
  - `ck_community_publish_attempts_currency`: `currency = 'USD'`
  - `ck_community_publish_attempts_payload_object`: `jsonb_typeof(publish_payload) = 'object'`
  - `ck_community_publish_attempts_status`: `attempt_status IN ('requires_payment_method', 'requires_action', 'processing', 'succeeded', 'failed', 'cancelled', 'expired')`
  - `ck_community_publish_attempts_succeeded_requires_game`: `(attempt_status <> 'succeeded' OR created_game_id IS NOT NULL)`
- **Indexes:**
  - `ix_community_publish_attempts_attempt_status`: `community_publish_attempts.attempt_status`
  - `ix_community_publish_attempts_created_game_id`: `community_publish_attempts.created_game_id`
  - `ix_community_publish_attempts_host_date`: `community_publish_attempts.host_user_id, community_publish_attempts.starts_on_local`
  - `ix_community_publish_attempts_host_user_id`: `community_publish_attempts.host_user_id`
  - `ix_community_publish_attempts_payment_id`: `community_publish_attempts.payment_id`
  - `ux_community_publish_attempts_one_active_paid_per_host_date`: `community_publish_attempts.host_user_id, community_publish_attempts.starts_on_local` (`UNIQUE`; `WHERE attempt_status IN ('requires_payment_method', 'requires_action', 'processing')`)

## Bookings, guests, participants, and waitlists

### `bookings`

Player booking parties and their financial/attendance state. Sources: [model](../../backend/models/booking_model.py), [canonical migration](../../backend/alembic/versions/0021_create_bookings_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `buyer_user_id` | `UUID` | No | — | FK → `users.id` |
| `booking_status` | `VARCHAR(30)` | No | server `'pending_payment'` | — |
| `payment_status` | `VARCHAR(30)` | No | server `'unpaid'` | — |
| `reservation_status` | `VARCHAR(30)` | No | server `'held'` | — |
| `participant_count` | `INTEGER` | No | — | — |
| `subtotal_cents` | `INTEGER` | No | — | — |
| `platform_fee_cents` | `INTEGER` | No | server `0` | — |
| `discount_cents` | `INTEGER` | No | server `0` | — |
| `total_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `price_per_player_snapshot_cents` | `INTEGER` | No | — | — |
| `platform_fee_snapshot_cents` | `INTEGER` | No | server `0` | — |
| `booked_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `cancel_reason` | `TEXT` | Yes | — | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `buyer_user_id` → `users.id` (ON DELETE RESTRICT); `cancelled_by_user_id` → `users.id` (ON DELETE SET NULL); `game_id` → `games.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `booking_policy_acceptances`, `booking_status_history`, `game_credit_usage`, `game_credits`, `game_participants`, `money_issues`, `notifications`, `payment_compensations`, `payment_confirmation_attempts`, `payments`, `refunds`, `support_flags`, `waitlist_entries`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `booking_status`: `pending_payment`, `confirmed`, `waitlisted`, `partially_cancelled`, `cancelled`, `expired`, `failed`, `capacity_conflict`; `payment_status`: `not_required`, `unpaid`, `requires_action`, `processing`, `paid`, `failed`, `partially_refunded`, `refunded`, `credit_restored`, `disputed`; `reservation_status`: `not_required`, `held`, `confirmed`, `released`, `capacity_conflict`.
- **CHECK constraints:**
  - `ck_bookings_booking_status`: `booking_status IN ('pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', 'cancelled', 'expired', 'failed', 'capacity_conflict')`
  - `ck_bookings_cancelled_requires_cancelled_at`: `(booking_status <> 'cancelled' OR cancelled_at IS NOT NULL)`
  - `ck_bookings_confirmed_requires_booked_at`: `(booking_status <> 'confirmed' OR booked_at IS NOT NULL)`
  - `ck_bookings_currency`: `currency = 'USD'`
  - `ck_bookings_discount_cents`: `discount_cents >= 0`
  - `ck_bookings_held_financial_summary`: `reservation_status <> 'held' OR payment_status NOT IN ('partially_refunded', 'refunded', 'credit_restored')`
  - `ck_bookings_participant_count`: `participant_count > 0`
  - `ck_bookings_payment_status`: `payment_status IN ('not_required', 'unpaid', 'requires_action', 'processing', 'paid', 'failed', 'partially_refunded', 'refunded', 'credit_restored', 'disputed')`
  - `ck_bookings_platform_fee_cents`: `platform_fee_cents >= 0`
  - `ck_bookings_platform_fee_snapshot_cents`: `platform_fee_snapshot_cents >= 0`
  - `ck_bookings_price_per_player_snapshot_cents`: `price_per_player_snapshot_cents >= 0`
  - `ck_bookings_reservation_lifecycle`: `(booking_status = 'pending_payment' AND reservation_status = 'held' AND expires_at IS NOT NULL) OR (booking_status IN ('confirmed', 'partially_cancelled') AND reservation_status = 'confirmed' AND expires_at IS NULL) OR (booking_status = 'waitlisted' AND reservation_status = 'not_required' AND expires_at IS NULL) OR (booking_status IN ('expired', 'failed') AND reservation_status = 'released' AND expires_at IS NULL) OR (booking_status = 'capacity_conflict' AND reservation_status = 'capacity_conflict' AND expires_at IS NULL) OR (booking_status = 'cancelled' AND reservation_status IN ('released', 'not_required') AND expires_at IS NULL)`
  - `ck_bookings_reservation_status`: `reservation_status IN ('not_required', 'held', 'confirmed', 'released', 'capacity_conflict')`
  - `ck_bookings_subtotal_cents`: `subtotal_cents >= 0`
  - `ck_bookings_total_cents`: `total_cents >= 0`
  - `ck_bookings_total_cents_formula`: `total_cents = subtotal_cents + platform_fee_cents - discount_cents`
- **Indexes:**
  - `ix_bookings_booking_status`: `bookings.booking_status`
  - `ix_bookings_buyer_user_id`: `bookings.buyer_user_id`
  - `ix_bookings_buyer_user_id_booking_status`: `bookings.buyer_user_id, bookings.booking_status`
  - `ix_bookings_game_id`: `bookings.game_id`
  - `ix_bookings_game_id_booking_status`: `bookings.game_id, bookings.booking_status`
  - `ix_bookings_game_status_expires_payment`: `bookings.game_id, bookings.booking_status, bookings.expires_at, bookings.payment_status`
  - `ix_bookings_payment_status`: `bookings.payment_status`

### `booking_policy_acceptances`

Policy acceptance captured for a booking. Sources: [model](../../backend/models/booking_policy_acceptance_model.py), [canonical migration](../../backend/alembic/versions/0029_create_booking_policy_acceptances_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `booking_id` | `UUID` | No | — | FK → `bookings.id` |
| `policy_document_id` | `UUID` | No | — | FK → `policy_documents.id` |
| `accepted_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE CASCADE); `policy_document_id` → `policy_documents.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_booking_policy_acceptances_booking_id_policy_document_id`: `booking_id, policy_document_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_booking_policy_acceptances_accepted_at`: `booking_policy_acceptances.accepted_at`
  - `ix_booking_policy_acceptances_booking_id`: `booking_policy_acceptances.booking_id`
  - `ix_booking_policy_acceptances_policy_document_id`: `booking_policy_acceptances.policy_document_id`

### `booking_status_history`

Recorded booking state changes. Sources: [model](../../backend/models/booking_status_history_model.py), [canonical migration](../../backend/alembic/versions/0030_create_booking_status_history_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `booking_id` | `UUID` | No | — | FK → `bookings.id` |
| `old_booking_status` | `VARCHAR(30)` | Yes | — | — |
| `new_booking_status` | `VARCHAR(30)` | No | — | — |
| `old_payment_status` | `VARCHAR(30)` | Yes | — | — |
| `new_payment_status` | `VARCHAR(30)` | Yes | — | — |
| `old_reservation_status` | `VARCHAR(30)` | Yes | — | — |
| `new_reservation_status` | `VARCHAR(30)` | No | — | — |
| `changed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `change_source` | `VARCHAR(30)` | No | server `'system'` | — |
| `change_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE CASCADE); `changed_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `old_booking_status`: `pending_payment`, `confirmed`, `waitlisted`, `partially_cancelled`, `cancelled`, `expired`, `failed`, `capacity_conflict`; `new_booking_status`: `pending_payment`, `confirmed`, `waitlisted`, `partially_cancelled`, `cancelled`, `expired`, `failed`, `capacity_conflict`; `old_payment_status`: `not_required`, `unpaid`, `requires_action`, `processing`, `paid`, `failed`, `partially_refunded`, `refunded`, `credit_restored`, `disputed`; `new_payment_status`: `not_required`, `unpaid`, `requires_action`, `processing`, `paid`, `failed`, `partially_refunded`, `refunded`, `credit_restored`, `disputed`; `old_reservation_status`: `not_required`, `held`, `confirmed`, `released`, `capacity_conflict`; `new_reservation_status`: `not_required`, `held`, `confirmed`, `released`, `capacity_conflict`.
- **CHECK constraints:**
  - `ck_booking_status_history_change_source`: `change_source IN ('user', 'host', 'admin', 'system', 'payment_webhook', 'scheduled_job')`
  - `ck_booking_status_history_new_booking_status`: `new_booking_status IN ('pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', 'cancelled', 'expired', 'failed', 'capacity_conflict')`
  - `ck_booking_status_history_new_payment_status`: `(new_payment_status IS NULL OR new_payment_status IN ('not_required', 'unpaid', 'requires_action', 'processing', 'paid', 'failed', 'partially_refunded', 'refunded', 'credit_restored', 'disputed'))`
  - `ck_booking_status_history_new_reservation_status`: `new_reservation_status IN ('not_required', 'held', 'confirmed', 'released', 'capacity_conflict')`
  - `ck_booking_status_history_old_booking_status`: `(old_booking_status IS NULL OR old_booking_status IN ('pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', 'cancelled', 'expired', 'failed', 'capacity_conflict'))`
  - `ck_booking_status_history_old_payment_status`: `(old_payment_status IS NULL OR old_payment_status IN ('not_required', 'unpaid', 'requires_action', 'processing', 'paid', 'failed', 'partially_refunded', 'refunded', 'credit_restored', 'disputed'))`
  - `ck_booking_status_history_old_reservation_status`: `(old_reservation_status IS NULL OR old_reservation_status IN ('not_required', 'held', 'confirmed', 'released', 'capacity_conflict'))`
- **Indexes:**
  - `ix_booking_status_history_booking_id`: `booking_status_history.booking_id`
  - `ix_booking_status_history_booking_id_created_at`: `booking_status_history.booking_id, booking_status_history.created_at`
  - `ix_booking_status_history_change_source`: `booking_status_history.change_source`
  - `ix_booking_status_history_changed_by_user_id`: `booking_status_history.changed_by_user_id`
  - `ix_booking_status_history_created_at`: `booking_status_history.created_at`

### `game_participants`

Roster places for players and guests. Sources: [model](../../backend/models/game_participant_model.py), [canonical migration](../../backend/alembic/versions/0032_create_game_participants_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `participant_type` | `VARCHAR(20)` | No | — | — |
| `user_id` | `UUID` | Yes | — | FK → `users.id` |
| `guest_of_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `guest_name` | `VARCHAR(120)` | Yes | — | — |
| `guest_email` | `VARCHAR(255)` | Yes | — | — |
| `guest_phone` | `VARCHAR(30)` | Yes | — | — |
| `display_name_snapshot` | `VARCHAR(150)` | No | — | — |
| `participant_status` | `VARCHAR(30)` | No | server `'pending_payment'` | — |
| `attendance_status` | `VARCHAR(30)` | No | server `'unknown'` | — |
| `cancellation_type` | `VARCHAR(30)` | No | server `'none'` | — |
| `price_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `roster_order` | `INTEGER` | Yes | — | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `confirmed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `checked_in_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `marked_attendance_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `attendance_decided_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `attendance_notes` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE RESTRICT); `game_id` → `games.id` (ON DELETE RESTRICT); `guest_of_user_id` → `users.id` (ON DELETE SET NULL); `marked_attendance_by_user_id` → `users.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `notifications`, `participant_status_history`, `refunds`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `participant_type`: `registered_user`, `guest`, `host`, `admin_added`; `participant_status`: `pending_payment`, `confirmed`, `waitlisted`, `cancelled`, `late_cancelled`, `removed`, `refunded`; `attendance_status`: `unknown`, `attended`, `no_show`, `excused_absence`, `not_applicable`; `cancellation_type`: `none`, `on_time`, `late`, `host_cancelled`, `admin_cancelled`, `payment_failed`.
- **CHECK constraints:**
  - `ck_game_participants_attendance_requires_decided_at`: `(attendance_status NOT IN ('attended', 'no_show', 'excused_absence') OR attendance_decided_at IS NOT NULL)`
  - `ck_game_participants_attendance_status`: `attendance_status IN ('unknown', 'attended', 'no_show', 'excused_absence', 'not_applicable')`
  - `ck_game_participants_cancellation_type`: `cancellation_type IN ('none', 'on_time', 'late', 'host_cancelled', 'admin_cancelled', 'payment_failed')`
  - `ck_game_participants_cancelled_requires_cancelled_at`: `(participant_status NOT IN ('cancelled', 'late_cancelled', 'removed', 'refunded') OR cancelled_at IS NOT NULL)`
  - `ck_game_participants_confirmed_requires_confirmed_at`: `(participant_status <> 'confirmed' OR confirmed_at IS NOT NULL)`
  - `ck_game_participants_currency`: `currency = 'USD'`
  - `ck_game_participants_guest_requires_guest_name`: `(participant_type <> 'guest' OR guest_name IS NOT NULL)`
  - `ck_game_participants_guest_requires_owner`: `(participant_type <> 'guest' OR guest_of_user_id IS NOT NULL)`
  - `ck_game_participants_non_guest_requires_user`: `(participant_type NOT IN ('registered_user', 'host', 'admin_added') OR user_id IS NOT NULL)`
  - `ck_game_participants_owner_only_for_guest`: `(participant_type = 'guest' OR guest_of_user_id IS NULL)`
  - `ck_game_participants_participant_status`: `participant_status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled', 'late_cancelled', 'removed', 'refunded')`
  - `ck_game_participants_participant_type`: `participant_type IN ('registered_user', 'guest', 'host', 'admin_added')`
  - `ck_game_participants_price_cents`: `price_cents >= 0`
  - `ck_game_participants_roster_order`: `(roster_order IS NULL OR roster_order > 0)`
- **Indexes:**
  - `ix_game_participants_attendance_status`: `game_participants.attendance_status`
  - `ix_game_participants_booking_id`: `game_participants.booking_id`
  - `ix_game_participants_booking_id_participant_status`: `game_participants.booking_id, game_participants.participant_status`
  - `ix_game_participants_game_id`: `game_participants.game_id`
  - `ix_game_participants_game_id_participant_status`: `game_participants.game_id, game_participants.participant_status`
  - `ix_game_participants_game_status_booking`: `game_participants.game_id, game_participants.participant_status, game_participants.booking_id`
  - `ix_game_participants_guest_of_user_id`: `game_participants.guest_of_user_id`
  - `ix_game_participants_participant_status`: `game_participants.participant_status`
  - `ix_game_participants_user_id`: `game_participants.user_id`
  - `ix_game_participants_user_id_game_id`: `game_participants.user_id, game_participants.game_id`
  - `ix_game_participants_user_id_participant_status`: `game_participants.user_id, game_participants.participant_status`
  - `ux_game_participants_active_registered_user_per_game`: `game_participants.game_id, game_participants.user_id` (`UNIQUE`; `WHERE user_id IS NOT NULL AND participant_status IN ('pending_payment', 'confirmed', 'waitlisted')`)

### `participant_status_history`

Recorded participant state changes. Sources: [model](../../backend/models/participant_status_history_model.py), [canonical migration](../../backend/alembic/versions/0043_create_participant_status_history_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `participant_id` | `UUID` | No | — | FK → `game_participants.id` |
| `old_participant_status` | `VARCHAR(30)` | Yes | — | — |
| `new_participant_status` | `VARCHAR(30)` | No | — | — |
| `old_attendance_status` | `VARCHAR(30)` | Yes | — | — |
| `new_attendance_status` | `VARCHAR(30)` | Yes | — | — |
| `changed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `change_source` | `VARCHAR(30)` | No | server `'system'` | — |
| `change_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `changed_by_user_id` → `users.id` (ON DELETE SET NULL); `participant_id` → `game_participants.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `old_participant_status`: `pending_payment`, `confirmed`, `waitlisted`, `cancelled`, `late_cancelled`, `removed`, `refunded`; `new_participant_status`: `pending_payment`, `confirmed`, `waitlisted`, `cancelled`, `late_cancelled`, `removed`, `refunded`; `old_attendance_status`: `unknown`, `attended`, `no_show`, `excused_absence`, `not_applicable`; `new_attendance_status`: `unknown`, `attended`, `no_show`, `excused_absence`, `not_applicable`.
- **CHECK constraints:**
  - `ck_participant_status_history_change_source`: `change_source IN ('user', 'host', 'admin', 'system', 'payment_webhook', 'scheduled_job')`
  - `ck_participant_status_history_new_attendance_status`: `(new_attendance_status IS NULL OR new_attendance_status IN ('unknown', 'attended', 'no_show', 'excused_absence', 'not_applicable'))`
  - `ck_participant_status_history_new_participant_status`: `new_participant_status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled', 'late_cancelled', 'removed', 'refunded')`
  - `ck_participant_status_history_old_attendance_status`: `(old_attendance_status IS NULL OR old_attendance_status IN ('unknown', 'attended', 'no_show', 'excused_absence', 'not_applicable'))`
  - `ck_participant_status_history_old_participant_status`: `(old_participant_status IS NULL OR old_participant_status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled', 'late_cancelled', 'removed', 'refunded'))`
- **Indexes:**
  - `ix_participant_status_history_change_source`: `participant_status_history.change_source`
  - `ix_participant_status_history_changed_by_user_id`: `participant_status_history.changed_by_user_id`
  - `ix_participant_status_history_created_at`: `participant_status_history.created_at`
  - `ix_participant_status_history_participant_id`: `participant_status_history.participant_id`
  - `ix_participant_status_history_participant_id_created_at`: `participant_status_history.participant_id, participant_status_history.created_at`

### `waitlist_entries`

Waitlist order and promotion/payment state. Sources: [model](../../backend/models/waitlist_entry_model.py), [canonical migration](../../backend/alembic/versions/0037_create_waitlist_entries_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `party_size` | `INTEGER` | No | server `1` | — |
| `position` | `INTEGER` | No | — | — |
| `waitlist_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `promoted_booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `promotion_expires_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `auto_charge_consent_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `auto_charge_consent_version` | `VARCHAR(50)` | Yes | — | — |
| `authorized_payment_method_id` | `UUID` | Yes | — | FK → `user_payment_methods.id` |
| `authorized_stripe_payment_method_id` | `VARCHAR(255)` | Yes | — | — |
| `authorized_payment_method_brand` | `VARCHAR(50)` | Yes | — | — |
| `authorized_payment_method_last4` | `VARCHAR(4)` | Yes | — | — |
| `authorized_amount_cents` | `INTEGER` | Yes | — | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `promoted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `expired_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `authorized_payment_method_id` → `user_payment_methods.id` (ON DELETE SET NULL); `game_id` → `games.id` (ON DELETE RESTRICT); `promoted_booking_id` → `bookings.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `waitlist_status`: `active`, `promoted`, `accepted`, `declined`, `expired`, `cancelled`, `removed`, `payment_processing`, `payment_failed`.
- **CHECK constraints:**
  - `ck_waitlist_entries_authorized_amount_non_negative`: `(authorized_amount_cents IS NULL OR authorized_amount_cents >= 0)`
  - `ck_waitlist_entries_cancelled_requires_cancelled_at`: `(waitlist_status <> 'cancelled' OR cancelled_at IS NOT NULL)`
  - `ck_waitlist_entries_expired_requires_expired_at`: `(waitlist_status <> 'expired' OR expired_at IS NOT NULL)`
  - `ck_waitlist_entries_party_size`: `party_size > 0`
  - `ck_waitlist_entries_position`: `position > 0`
  - `ck_waitlist_entries_promoted_requires_promoted_at`: `(waitlist_status <> 'promoted' OR promoted_at IS NOT NULL)`
  - `ck_waitlist_entries_promoted_requires_promotion_expires_at`: `(waitlist_status <> 'promoted' OR promotion_expires_at IS NOT NULL)`
  - `ck_waitlist_entries_waitlist_status`: `waitlist_status IN ('active', 'promoted', 'accepted', 'declined', 'expired', 'cancelled', 'removed', 'payment_processing', 'payment_failed')`
- **Indexes:**
  - `ix_waitlist_entries_game_id`: `waitlist_entries.game_id`
  - `ix_waitlist_entries_game_id_waitlist_status_position`: `waitlist_entries.game_id, waitlist_entries.waitlist_status, waitlist_entries.position`
  - `ix_waitlist_entries_game_user_status`: `waitlist_entries.game_id, waitlist_entries.user_id, waitlist_entries.waitlist_status`
  - `ix_waitlist_entries_user_id`: `waitlist_entries.user_id`
  - `ix_waitlist_entries_user_id_waitlist_status`: `waitlist_entries.user_id, waitlist_entries.waitlist_status`
  - `ix_waitlist_entries_waitlist_status`: `waitlist_entries.waitlist_status`
  - `ux_waitlist_entries_active_position_per_game`: `waitlist_entries.game_id, waitlist_entries.position` (`UNIQUE`; `WHERE waitlist_status = 'active'`)
  - `ux_waitlist_entries_active_user_per_game`: `waitlist_entries.game_id, waitlist_entries.user_id` (`UNIQUE`; `WHERE waitlist_status IN ('active', 'payment_processing')`)

## Payments, refunds, credits, and financial records

### `payments`

Payment ledger and provider transaction state. Sources: [model](../../backend/models/payment_model.py), [canonical migration](../../backend/alembic/versions/0033_create_payments_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `payer_user_id` | `UUID` | No | — | FK → `users.id` |
| `booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `game_id` | `UUID` | Yes | — | FK → `games.id` |
| `payment_type` | `VARCHAR(30)` | No | — | — |
| `provider` | `VARCHAR(20)` | No | server `'stripe'` | — |
| `provider_payment_intent_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_charge_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_customer_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_status` | `VARCHAR(100)` | Yes | — | — |
| `idempotency_key` | `VARCHAR(255)` | No | — | — |
| `creation_fingerprint` | `VARCHAR(64)` | No | client `<lambda>` | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `payment_status` | `VARCHAR(30)` | No | — | — |
| `paid_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `failure_code` | `VARCHAR(100)` | Yes | — | — |
| `failure_message` | `TEXT` | Yes | — | — |
| `metadata` | `JSONB` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE SET NULL); `game_id` → `games.id` (ON DELETE SET NULL); `payer_user_id` → `users.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_payments_idempotency_key`: `idempotency_key`.
- **Other table relationships:** Referenced by `admin_financial_outcomes`, `admin_review_cases`, `admin_review_signals`, `community_publish_attempts`, `game_credit_usage`, `game_credits`, `host_publish_fees`, `money_issues`, `notifications`, `payment_compensations`, `payment_confirmation_attempts`, `payment_events`, `refunds`, `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `payment_type`: `booking`, `community_publish_fee`, `admin_charge`; `provider_status`: see CHECK constraints below; `payment_status`: `requires_payment_method`, `requires_confirmation`, `requires_action`, `processing`, `requires_capture`, `succeeded`, `failed`, `canceled`, `unknown`.
- **CHECK constraints:**
  - `ck_payments_amount_cents`: `amount_cents > 0`
  - `ck_payments_booking_requires_booking_id`: `(payment_type <> 'booking' OR booking_id IS NOT NULL)`
  - `ck_payments_community_publish_fee_no_booking`: `(payment_type <> 'community_publish_fee' OR booking_id IS NULL)`
  - `ck_payments_currency`: `currency = 'USD'`
  - `ck_payments_payment_status`: `payment_status IN ('requires_payment_method', 'requires_confirmation', 'requires_action', 'processing', 'requires_capture', 'succeeded', 'failed', 'canceled', 'unknown')`
  - `ck_payments_payment_type`: `payment_type IN ('booking', 'community_publish_fee', 'admin_charge')`
  - `ck_payments_provider`: `provider IN ('stripe')`
  - `ck_payments_provider_status`: `provider_status IS NULL OR char_length(btrim(provider_status)) > 0`
  - `ck_payments_succeeded_requires_paid_at`: `(payment_status <> 'succeeded' OR paid_at IS NOT NULL)`
- **Indexes:**
  - `ix_payments_booking_id`: `payments.booking_id`
  - `ix_payments_game_id`: `payments.game_id`
  - `ix_payments_payer_created`: `payments.payer_user_id, payments.created_at, payments.id`
  - `ix_payments_payment_status_created`: `payments.payment_status, payments.created_at, payments.id`
  - `ix_payments_payment_type_created`: `payments.payment_type, payments.created_at, payments.id`
  - `ix_payments_provider_charge_id`: `payments.provider_charge_id`
  - `ix_payments_provider_payment_intent_id`: `payments.provider_payment_intent_id`
  - `uq_payments_provider_charge_id`: `payments.provider, payments.provider_charge_id` (`UNIQUE`; `WHERE provider_charge_id IS NOT NULL`)
  - `uq_payments_provider_payment_intent_id`: `payments.provider, payments.provider_payment_intent_id` (`UNIQUE`; `WHERE provider_payment_intent_id IS NOT NULL`)

### `payment_events`

Provider and workflow events for payments. Sources: [model](../../backend/models/payment_event_model.py), [canonical migration](../../backend/alembic/versions/0044_create_payment_events_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `provider` | `VARCHAR(20)` | No | server `'stripe'` | — |
| `provider_event_id` | `VARCHAR(255)` | No | — | — |
| `event_type` | `VARCHAR(100)` | No | — | — |
| `event_envelope` | `JSONB` | No | — | — |
| `provider_created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `processing_status` | `VARCHAR(30)` | No | server `'pending'` | — |
| `processed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `processing_error_code` | `VARCHAR(100)` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `payment_id` → `payments.id` (ON DELETE SET NULL).
- **Unique constraints:** `uq_payment_events_provider_event_id`: `provider_event_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `event_type`: see CHECK constraints below; `processing_status`: `pending`, `processing`, `processed`, `failed`, `ignored`.
- **CHECK constraints:**
  - `ck_payment_events_event_type_not_empty`: `char_length(btrim(event_type)) > 0`
  - `ck_payment_events_failed_requires_processing_error`: `(processing_status <> 'failed' OR processing_error_code IS NOT NULL)`
  - `ck_payment_events_processed_requires_processed_at`: `(processing_status <> 'processed' OR processed_at IS NOT NULL)`
  - `ck_payment_events_processing_status`: `processing_status IN ('pending', 'processing', 'processed', 'failed', 'ignored')`
  - `ck_payment_events_provider`: `provider IN ('stripe')`
- **Indexes:**
  - `ix_payment_events_created_at`: `payment_events.created_at`
  - `ix_payment_events_event_type`: `payment_events.event_type`
  - `ix_payment_events_payment_id`: `payment_events.payment_id`
  - `ix_payment_events_payment_id_created_at`: `payment_events.payment_id, payment_events.created_at`
  - `ix_payment_events_processing_status`: `payment_events.processing_status`
  - `ix_payment_events_processing_status_created_at`: `payment_events.processing_status, payment_events.created_at`

### `payment_confirmation_attempts`

Attempts to confirm payment-dependent bookings. Sources: [model](../../backend/models/payment_confirmation_attempt_model.py), [canonical migration](../../backend/alembic/versions/0063_create_payment_confirmation_attempts_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `payment_id` | `UUID` | No | — | FK → `payments.id` |
| `booking_id` | `UUID` | No | — | FK → `bookings.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `provider_customer_id` | `VARCHAR(255)` | No | — | — |
| `provider_payment_method_id` | `VARCHAR(255)` | No | — | — |
| `confirmation_fingerprint` | `VARCHAR(64)` | No | — | — |
| `confirmation_idempotency_key` | `VARCHAR(255)` | No | — | — |
| `outcome` | `VARCHAR(30)` | No | server `'pending'` | — |
| `error_code` | `VARCHAR(100)` | Yes | — | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE CASCADE); `payment_id` → `payments.id` (ON DELETE CASCADE); `user_id` → `users.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `outcome`: `pending`, `provider_unknown`, `succeeded`, `failed`.
- **CHECK constraints:**
  - `ck_payment_confirmation_attempts_outcome`: `outcome IN ('pending', 'provider_unknown', 'succeeded', 'failed')`
- **Indexes:**
  - `ix_payment_confirmation_attempts_payment_created`: `payment_confirmation_attempts.payment_id, payment_confirmation_attempts.created_at, payment_confirmation_attempts.id`
  - `uq_payment_confirmation_attempts_fingerprint`: `payment_confirmation_attempts.payment_id, payment_confirmation_attempts.confirmation_fingerprint` (`UNIQUE`)
  - `uq_payment_confirmation_attempts_idempotency`: `payment_confirmation_attempts.confirmation_idempotency_key` (`UNIQUE`)

### `payment_compensations`

Compensation records for payment workflow failures. Sources: [model](../../backend/models/payment_compensation_model.py), [canonical migration](../../backend/alembic/versions/0064_create_payment_compensations_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `payment_id` | `UUID` | No | — | FK → `payments.id` |
| `booking_id` | `UUID` | No | — | FK → `bookings.id` |
| `refund_id` | `UUID` | Yes | — | FK → `refunds.id` |
| `action` | `VARCHAR(30)` | No | server `'refund'` | — |
| `reason` | `VARCHAR(50)` | No | — | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `status` | `VARCHAR(30)` | No | server `'required'` | — |
| `error_code` | `VARCHAR(100)` | Yes | — | — |
| `processing_started_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE RESTRICT); `refund_id` → `refunds.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `status`: `required`, `processing`, `succeeded`, `failed`.
- **CHECK constraints:**
  - `ck_payment_compensations_action`: `action = 'refund'`
  - `ck_payment_compensations_amount`: `amount_cents > 0`
  - `ck_payment_compensations_currency`: `currency = 'USD'`
  - `ck_payment_compensations_reason`: `reason IN ('reservation_expired', 'capacity_conflict', 'booking_cancelled')`
  - `ck_payment_compensations_status`: `status IN ('required', 'processing', 'succeeded', 'failed')`
- **Indexes:**
  - `ix_payment_compensations_booking`: `payment_compensations.booking_id, payment_compensations.created_at, payment_compensations.id`
  - `ix_payment_compensations_payment`: `payment_compensations.payment_id, payment_compensations.created_at, payment_compensations.id`
  - `uq_payment_compensations_payment_booking`: `payment_compensations.payment_id, payment_compensations.booking_id` (`UNIQUE`)

### `payment_method_operations`

Idempotent saved-card operation records. Sources: [model](../../backend/models/payment_method_operation_model.py), [canonical migration](../../backend/alembic/versions/0065_create_payment_method_operations_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `payment_method_id` | `UUID` | Yes | — | FK → `user_payment_methods.id` |
| `operation_kind` | `VARCHAR(40)` | No | — | — |
| `status` | `VARCHAR(30)` | No | server `'pending'` | — |
| `request_fingerprint` | `VARCHAR(64)` | No | — | — |
| `provider_idempotency_key` | `VARCHAR(255)` | No | — | — |
| `provider_object_id` | `VARCHAR(255)` | Yes | — | — |
| `error_code` | `VARCHAR(100)` | Yes | — | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `payment_method_id` → `user_payment_methods.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `operation_kind`: `setup_create`, `sync`, `set_default`, `detach`, `clear_default`; `status`: `pending`, `provider_unknown`, `succeeded`, `failed`.
- **CHECK constraints:**
  - `ck_payment_method_operations_kind`: `operation_kind IN ('setup_create', 'sync', 'set_default', 'detach', 'clear_default')`
  - `ck_payment_method_operations_status`: `status IN ('pending', 'provider_unknown', 'succeeded', 'failed')`
- **Indexes:**
  - `ix_payment_method_operations_user_created`: `payment_method_operations.user_id, payment_method_operations.created_at, payment_method_operations.id`
  - `uq_payment_method_operations_active_user`: `payment_method_operations.user_id` (`UNIQUE`; `WHERE status IN ('pending', 'provider_unknown')`)
  - `uq_payment_method_operations_fingerprint`: `payment_method_operations.user_id, payment_method_operations.operation_kind, payment_method_operations.request_fingerprint` (`UNIQUE`)
  - `uq_payment_method_operations_idempotency`: `payment_method_operations.provider_idempotency_key` (`UNIQUE`)

### `refunds`

Cash refund records and provider state. Sources: [model](../../backend/models/refund_model.py), [canonical migration](../../backend/alembic/versions/0048_create_refunds_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `payment_id` | `UUID` | No | — | FK → `payments.id` |
| `booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `participant_id` | `UUID` | Yes | — | FK → `game_participants.id` |
| `host_publish_fee_id` | `UUID` | Yes | — | FK → `host_publish_fees.id` |
| `provider_refund_id` | `VARCHAR(255)` | Yes | — | — |
| `origin_operation_key` | `VARCHAR(255)` | No | — | — |
| `current_attempt_number` | `INTEGER` | No | — | — |
| `stripe_request_key` | `VARCHAR(255)` | Yes | — | — |
| `provider_attempt_started_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `automatic_mutation_blocked_reason` | `VARCHAR(80)` | Yes | — | — |
| `automatic_mutation_blocked_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `origin_workflow` | `VARCHAR(80)` | No | server `'direct_admin_refund'` | — |
| `provider` | `VARCHAR(20)` | No | server `'stripe'` | — |
| `provider_status` | `VARCHAR(30)` | Yes | — | — |
| `provider_status_observed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `provider_charge_id` | `VARCHAR(255)` | Yes | — | — |
| `last_refund_event_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `refund_reason` | `VARCHAR(40)` | No | — | — |
| `refund_status` | `VARCHAR(30)` | No | server `'pending'` | — |
| `requested_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `approved_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `requested_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `approved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `refunded_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `approved_by_user_id` → `users.id` (ON DELETE SET NULL); `booking_id` → `bookings.id` (ON DELETE RESTRICT); `host_publish_fee_id` → `host_publish_fees.id` (ON DELETE RESTRICT); `participant_id` → `game_participants.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE RESTRICT); `requested_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_financial_outcomes`, `money_issues`, `notifications`, `payment_compensations`, `refund_events`, `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `provider_status`: `processing`, `succeeded`, `failed`, `cancelled`, `unknown`; `refund_status`: `pending`, `approved`, `processing`, `succeeded`, `failed`, `cancelled`.
- **CHECK constraints:**
  - `ck_refunds_amount_cents`: `amount_cents > 0`
  - `ck_refunds_approved_requires_approved_at`: `(refund_status <> 'approved' OR approved_at IS NOT NULL)`
  - `ck_refunds_attempt_identity`: `((current_attempt_number = 0 AND stripe_request_key IS NULL AND provider_refund_id IS NOT NULL) OR (current_attempt_number > 0 AND stripe_request_key = 'refund:' \|\| id::text \|\| ':attempt:' \|\| current_attempt_number::text))`
  - `ck_refunds_automatic_mutation_block`: `((automatic_mutation_blocked_reason IS NULL AND automatic_mutation_blocked_at IS NULL) OR (automatic_mutation_blocked_reason = 'historical_attempt_conflict' AND automatic_mutation_blocked_at IS NOT NULL))`
  - `ck_refunds_currency`: `currency = 'USD'`
  - `ck_refunds_origin_workflow`: `origin_workflow IN ('player_removal', 'official_game_cancellation', 'community_publish_fee_refund', 'direct_admin_refund', 'official_game_checkout', 'pending_checkout_expiration', 'pending_checkout_cancellation', 'admin_game_update')`
  - `ck_refunds_provider`: `provider IN ('stripe')`
  - `ck_refunds_provider_status`: `provider_status IS NULL OR provider_status IN ('processing', 'succeeded', 'failed', 'cancelled', 'unknown')`
  - `ck_refunds_refund_reason`: `refund_reason IN ('player_cancelled', 'late_cancel', 'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', 'duplicate_payment', 'dispute_resolution', 'publish_fee_refund', 'unfulfilled_booking')`
  - `ck_refunds_refund_status`: `refund_status IN ('pending', 'approved', 'processing', 'succeeded', 'failed', 'cancelled')`
  - `ck_refunds_succeeded_requires_refunded_at`: `(refund_status <> 'succeeded' OR refunded_at IS NOT NULL)`
  - `ck_refunds_target_required`: `booking_id IS NOT NULL OR participant_id IS NOT NULL OR host_publish_fee_id IS NOT NULL`
- **Indexes:**
  - `ix_refunds_amount_cents_id`: `refunds.amount_cents, refunds.id`
  - `ix_refunds_approved_by_user_id`: `refunds.approved_by_user_id`
  - `ix_refunds_booking_id`: `refunds.booking_id`
  - `ix_refunds_host_publish_fee_id`: `refunds.host_publish_fee_id`
  - `ix_refunds_last_refund_event_at`: `refunds.last_refund_event_at, refunds.id`
  - `ix_refunds_origin_workflow_created`: `refunds.origin_workflow, refunds.created_at, refunds.id`
  - `ix_refunds_participant_id`: `refunds.participant_id`
  - `ix_refunds_payment_id`: `refunds.payment_id`
  - `ix_refunds_provider_charge_id`: `refunds.provider_charge_id`
  - `ix_refunds_provider_refund_id`: `refunds.provider_refund_id`
  - `ix_refunds_provider_status_created`: `refunds.provider_status, refunds.created_at, refunds.id`
  - `ix_refunds_refund_reason`: `refunds.refund_reason`
  - `ix_refunds_refund_status_created`: `refunds.refund_status, refunds.created_at, refunds.id`
  - `ix_refunds_requested_by_user_id`: `refunds.requested_by_user_id`
  - `uq_refunds_origin_operation_key`: `refunds.origin_operation_key` (`UNIQUE`)
  - `uq_refunds_provider_refund_id`: `refunds.provider, refunds.provider_refund_id` (`UNIQUE`; `WHERE provider_refund_id IS NOT NULL`)
  - `uq_refunds_stripe_request_key`: `refunds.stripe_request_key` (`UNIQUE`; `WHERE stripe_request_key IS NOT NULL`)

### `refund_events`

Provider and workflow events for refunds. Sources: [model](../../backend/models/refund_event_model.py), [canonical migration](../../backend/alembic/versions/0052_create_refund_events_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `refund_id` | `UUID` | No | — | FK → `refunds.id` |
| `event_type` | `VARCHAR(40)` | No | — | — |
| `event_source` | `VARCHAR(30)` | No | — | — |
| `actor_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `idempotency_key` | `VARCHAR(255)` | Yes | — | — |
| `attempt_number` | `INTEGER` | No | — | — |
| `attempt_amount_cents` | `INTEGER` | No | — | — |
| `attempt_currency` | `CHAR(3)` | No | — | — |
| `attempt_request_key` | `VARCHAR(255)` | Yes | — | — |
| `provider` | `VARCHAR(20)` | Yes | — | — |
| `provider_event_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_refund_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_charge_id` | `VARCHAR(255)` | Yes | — | — |
| `provider_status` | `VARCHAR(30)` | Yes | — | — |
| `previous_refund_status` | `VARCHAR(30)` | Yes | — | — |
| `new_refund_status` | `VARCHAR(30)` | Yes | — | — |
| `reason_code` | `VARCHAR(80)` | Yes | — | — |
| `summary` | `TEXT` | Yes | — | — |
| `metadata` | `JSONB` | Yes | — | — |
| `occurred_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `actor_user_id` → `users.id` (ON DELETE SET NULL); `admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `refund_id` → `refunds.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `money_issue_events`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `event_type`: `provider_result_recorded`, `reconciliation_checked`, `local_status_changed`, `provider_outcome_unknown`; `provider_status`: `processing`, `succeeded`, `failed`, `cancelled`, `unknown`; `previous_refund_status`: no table-local value CHECK; application-defined or historical value; `new_refund_status`: no table-local value CHECK; application-defined or historical value.
- **CHECK constraints:**
  - `ck_refund_events_attempt_amount`: `attempt_amount_cents > 0`
  - `ck_refund_events_attempt_currency`: `attempt_currency = 'USD'`
  - `ck_refund_events_attempt_identity`: `((attempt_number = 0 AND attempt_request_key IS NULL) OR (attempt_number > 0 AND attempt_request_key = 'refund:' \|\| refund_id::text \|\| ':attempt:' \|\| attempt_number::text))`
  - `ck_refund_events_attempt_number`: `attempt_number >= 0`
  - `ck_refund_events_event_source`: `event_source IN ('system', 'webhook', 'reconciliation', 'admin')`
  - `ck_refund_events_event_type`: `event_type IN ('provider_result_recorded', 'reconciliation_checked', 'local_status_changed', 'provider_outcome_unknown')`
  - `ck_refund_events_provider`: `(provider IS NULL OR provider IN ('stripe'))`
  - `ck_refund_events_provider_status`: `provider_status IS NULL OR provider_status IN ('processing', 'succeeded', 'failed', 'cancelled', 'unknown')`
- **Indexes:**
  - `ix_refund_events_provider_charge_id`: `refund_events.provider_charge_id`
  - `ix_refund_events_provider_refund_id`: `refund_events.provider_refund_id`
  - `ix_refund_events_refund_id`: `refund_events.refund_id`
  - `ix_refund_events_refund_id_occurred_id`: `refund_events.refund_id, refund_events.occurred_at, refund_events.id`
  - `uq_refund_events_provider_event_id`: `refund_events.provider, refund_events.provider_event_id` (`UNIQUE`; `WHERE provider_event_id IS NOT NULL`)
  - `uq_refund_events_refund_id_idempotency_key`: `refund_events.refund_id, refund_events.idempotency_key` (`UNIQUE`; `WHERE idempotency_key IS NOT NULL`)

### `game_credits`

Player credit grants, balance, and lifecycle. Sources: [model](../../backend/models/game_credit_model.py), [canonical migration](../../backend/alembic/versions/0041_create_game_credits_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `amount_cents` | `INTEGER` | No | — | — |
| `available_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `credit_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `credit_reason` | `VARCHAR(40)` | No | — | — |
| `source_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `source_booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `source_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `issued_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `reversed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `idempotency_key` | `VARCHAR(255)` | No | — | — |
| `note` | `TEXT` | Yes | — | — |
| `reversed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `issued_by_user_id` → `users.id` (ON DELETE SET NULL); `reversed_by_user_id` → `users.id` (ON DELETE SET NULL); `source_booking_id` → `bookings.id` (ON DELETE SET NULL); `source_game_id` → `games.id` (ON DELETE SET NULL); `source_payment_id` → `payments.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_game_credits_idempotency_key`: `idempotency_key`.
- **Other table relationships:** Referenced by `admin_rejected_attempts`, `game_credit_usage`, `money_issues`, `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `credit_status`: `active`, `used`, `reversed`.
- **CHECK constraints:**
  - `ck_game_credits_amount_cents`: `amount_cents > 0`
  - `ck_game_credits_available_cents_non_negative`: `available_cents >= 0`
  - `ck_game_credits_available_not_above_amount`: `available_cents <= amount_cents`
  - `ck_game_credits_credit_reason`: `credit_reason IN ('official_game_cancelled', 'weather_cancelled', 'player_cancelled_on_time', 'admin_credit', 'support_adjustment')`
  - `ck_game_credits_credit_status`: `credit_status IN ('active', 'used', 'reversed')`
  - `ck_game_credits_currency`: `currency = 'USD'`
  - `ck_game_credits_reversal_fields_match_status`: `((credit_status = 'reversed') AND reversed_by_user_id IS NOT NULL AND reversed_at IS NOT NULL) OR ((credit_status <> 'reversed') AND reversed_by_user_id IS NULL AND reversed_at IS NULL)`
  - `ck_game_credits_reversed_has_no_available`: `(credit_status <> 'reversed' OR available_cents = 0)`
- **Indexes:**
  - `ix_game_credits_created_at`: `game_credits.created_at`
  - `ix_game_credits_credit_reason_created`: `game_credits.credit_reason, game_credits.created_at, game_credits.id`
  - `ix_game_credits_credit_status_created`: `game_credits.credit_status, game_credits.created_at, game_credits.id`
  - `ix_game_credits_source_booking_id`: `game_credits.source_booking_id`
  - `ix_game_credits_source_game_id`: `game_credits.source_game_id`
  - `ix_game_credits_source_payment_id`: `game_credits.source_payment_id`
  - `ix_game_credits_user_created`: `game_credits.user_id, game_credits.created_at, game_credits.id`
  - `ix_game_credits_user_id_credit_status`: `game_credits.user_id, game_credits.credit_status`

### `game_credit_usage`

Credit use and restoration against bookings or payments. Sources: [model](../../backend/models/game_credit_usage_model.py), [canonical migration](../../backend/alembic/versions/0046_create_game_credit_usage_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_credit_id` | `UUID` | No | — | FK → `game_credits.id` |
| `booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `game_id` | `UUID` | Yes | — | FK → `games.id` |
| `payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `original_usage_id` | `UUID` | Yes | — | FK → `game_credit_usage.id` |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `usage_type` | `VARCHAR(30)` | No | — | — |
| `usage_status` | `VARCHAR(30)` | No | — | — |
| `idempotency_key` | `VARCHAR(255)` | No | — | — |
| `reason_code` | `VARCHAR(80)` | Yes | — | — |
| `reserved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `redeemed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `released_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `booking_id` → `bookings.id` (ON DELETE SET NULL); `game_credit_id` → `game_credits.id` (ON DELETE RESTRICT); `game_id` → `games.id` (ON DELETE SET NULL); `original_usage_id` → `game_credit_usage.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE SET NULL).
- **Unique constraints:** `uq_game_credit_usage_idempotency_key`: `idempotency_key`.
- **Other table relationships:** Referenced by `game_credit_usage`, `money_issue_events`, `money_issues`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `usage_type`: `redeem`, `reverse`, `restore`; `usage_status`: `reserved`, `redeemed`, `released`, `reversed`, `restored`.
- **CHECK constraints:**
  - `ck_game_credit_usage_amount_cents`: `amount_cents > 0`
  - `ck_game_credit_usage_currency`: `currency = 'USD'`
  - `ck_game_credit_usage_redeem_requires_booking`: `(usage_type <> 'redeem' OR booking_id IS NOT NULL)`
  - `ck_game_credit_usage_redeemed_requires_redeemed_at`: `(usage_status <> 'redeemed' OR redeemed_at IS NOT NULL)`
  - `ck_game_credit_usage_released_requires_released_at`: `(usage_status <> 'released' OR released_at IS NOT NULL)`
  - `ck_game_credit_usage_reserved_requires_reserved_at`: `(usage_status <> 'reserved' OR reserved_at IS NOT NULL)`
  - `ck_game_credit_usage_restore_requires_original_usage`: `(usage_type <> 'restore' OR original_usage_id IS NOT NULL)`
  - `ck_game_credit_usage_type_status_match`: `((usage_type = 'redeem' AND usage_status IN ('reserved', 'redeemed', 'released')) OR (usage_type = 'reverse' AND usage_status = 'reversed') OR (usage_type = 'restore' AND usage_status = 'restored'))`
  - `ck_game_credit_usage_usage_status`: `usage_status IN ('reserved', 'redeemed', 'released', 'reversed', 'restored')`
  - `ck_game_credit_usage_usage_type`: `usage_type IN ('redeem', 'reverse', 'restore')`
- **Indexes:**
  - `ix_game_credit_usage_booking_id`: `game_credit_usage.booking_id`
  - `ix_game_credit_usage_created_at`: `game_credit_usage.created_at`
  - `ix_game_credit_usage_credit_created`: `game_credit_usage.game_credit_id, game_credit_usage.created_at, game_credit_usage.id`
  - `ix_game_credit_usage_credit_status`: `game_credit_usage.game_credit_id, game_credit_usage.usage_status`
  - `ix_game_credit_usage_game_credit_id`: `game_credit_usage.game_credit_id`
  - `ix_game_credit_usage_game_id`: `game_credit_usage.game_id`
  - `ix_game_credit_usage_original_usage_id`: `game_credit_usage.original_usage_id`
  - `ix_game_credit_usage_payment_id`: `game_credit_usage.payment_id`
  - `ix_game_credit_usage_usage_status`: `game_credit_usage.usage_status`
  - `ix_game_credit_usage_usage_type`: `game_credit_usage.usage_type`
  - `uq_game_credit_usage_one_restore_per_original`: `game_credit_usage.original_usage_id` (`UNIQUE`; `WHERE usage_type = 'restore' AND usage_status = 'restored' AND original_usage_id IS NOT NULL`)

### `admin_financial_outcomes`

Staff-recorded outcome for publish-fee financial decisions. Sources: [model](../../backend/models/admin_financial_outcome_model.py), [canonical migration](../../backend/alembic/versions/0049_create_admin_financial_outcomes_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_sub_post_id` | `UUID` | Yes | — | FK → `sub_posts.id` |
| `host_user_id` | `UUID` | No | — | FK → `users.id` |
| `host_publish_fee_id` | `UUID` | Yes | — | FK → `host_publish_fees.id` |
| `payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `refund_id` | `UUID` | Yes | — | FK → `refunds.id` |
| `host_publish_entitlement_id` | `UUID` | Yes | — | FK → `host_publish_entitlements.id` |
| `admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `review_case_id` | `UUID` | Yes | — | — |
| `outcome` | `VARCHAR(40)` | No | — | — |
| `applied_status` | `VARCHAR(30)` | No | — | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `reason` | `TEXT` | No | — | — |
| `internal_note` | `TEXT` | Yes | — | — |
| `failure_reason` | `TEXT` | Yes | — | — |
| `created_by_user_id` | `UUID` | No | — | FK → `users.id` |
| `applied_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `applied_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `superseded_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `applied_by_user_id` → `users.id` (ON DELETE SET NULL); `created_by_user_id` → `users.id` (ON DELETE RESTRICT); `host_publish_entitlement_id` → `host_publish_entitlements.id` (ON DELETE SET NULL); `host_publish_fee_id` → `host_publish_fees.id` (ON DELETE SET NULL); `host_user_id` → `users.id` (ON DELETE RESTRICT); `payment_id` → `payments.id` (ON DELETE SET NULL); `refund_id` → `refunds.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE SET NULL); `target_sub_post_id` → `sub_posts.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_review_cases`, `admin_review_signals`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `outcome`: `no_fee_charged`, `refund`, `credit`, `forfeit`, `manual_review`; `applied_status`: `pending`, `applied`, `failed`, `not_applicable`, `superseded`.
- **CHECK constraints:**
  - `ck_admin_financial_outcomes_amount_cents`: `amount_cents >= 0`
  - `ck_admin_financial_outcomes_applied_status`: `applied_status IN ('pending', 'applied', 'failed', 'not_applicable', 'superseded')`
  - `ck_admin_financial_outcomes_currency`: `currency = 'USD'`
  - `ck_admin_financial_outcomes_outcome`: `outcome IN ('no_fee_charged', 'refund', 'credit', 'forfeit', 'manual_review')`
  - `ck_admin_financial_outcomes_superseded_fields`: `((applied_status = 'superseded' AND superseded_at IS NOT NULL AND applied_at IS NULL AND applied_by_user_id IS NULL) OR (applied_status <> 'superseded' AND superseded_at IS NULL))`
  - `ck_admin_financial_outcomes_target_required`: `host_user_id IS NOT NULL AND (target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR host_publish_fee_id IS NOT NULL OR payment_id IS NOT NULL)`
  - `ck_admin_financial_outcomes_terminal_requires_applied_at`: `applied_status NOT IN ('applied', 'failed') OR applied_at IS NOT NULL`
- **Indexes:**
  - `ix_admin_financial_outcomes_admin_action_id`: `admin_financial_outcomes.admin_action_id`
  - `ix_admin_financial_outcomes_applied_status`: `admin_financial_outcomes.applied_status`
  - `ix_admin_financial_outcomes_created_by_user_id`: `admin_financial_outcomes.created_by_user_id`
  - `ix_admin_financial_outcomes_entitlement_id`: `admin_financial_outcomes.host_publish_entitlement_id`
  - `ix_admin_financial_outcomes_host_publish_fee_id`: `admin_financial_outcomes.host_publish_fee_id`
  - `ix_admin_financial_outcomes_host_user_id`: `admin_financial_outcomes.host_user_id`
  - `ix_admin_financial_outcomes_outcome`: `admin_financial_outcomes.outcome`
  - `ix_admin_financial_outcomes_payment_id`: `admin_financial_outcomes.payment_id`
  - `ix_admin_financial_outcomes_refund_id`: `admin_financial_outcomes.refund_id`
  - `ix_admin_financial_outcomes_review_case_id`: `admin_financial_outcomes.review_case_id`
  - `ix_admin_financial_outcomes_target_game_id`: `admin_financial_outcomes.target_game_id`
  - `ix_admin_financial_outcomes_target_sub_post_id`: `admin_financial_outcomes.target_sub_post_id`
  - `uq_admin_financial_outcomes_active_fee_decision`: `admin_financial_outcomes.host_publish_fee_id` (`UNIQUE`; `WHERE host_publish_fee_id IS NOT NULL AND applied_status IN ('pending', 'applied', 'not_applicable')`)
  - `uq_admin_financial_outcomes_active_game_no_fee_decision`: `admin_financial_outcomes.host_user_id, admin_financial_outcomes.target_game_id` (`UNIQUE`; `WHERE target_game_id IS NOT NULL AND host_publish_fee_id IS NULL AND applied_status IN ('pending', 'applied', 'not_applicable')`)

### `money_issues`

Financial exceptions requiring staff follow-up. Sources: [model](../../backend/models/money_issue_model.py), [canonical migration](../../backend/alembic/versions/0050_create_money_issues_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `operation_key` | `VARCHAR(255)` | No | — | — |
| `status` | `VARCHAR(20)` | No | — | — |
| `issue_type` | `VARCHAR(80)` | No | — | — |
| `origin_workflow` | `VARCHAR(80)` | No | — | — |
| `value_kind` | `VARCHAR(40)` | No | — | — |
| `amount_cents` | `INTEGER` | No | — | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `target_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `target_refund_id` | `UUID` | Yes | — | FK → `refunds.id` |
| `target_game_credit_id` | `UUID` | Yes | — | FK → `game_credits.id` |
| `target_credit_usage_id` | `UUID` | Yes | — | FK → `game_credit_usage.id` |
| `latest_reason_code` | `VARCHAR(80)` | Yes | — | — |
| `latest_summary` | `TEXT` | Yes | — | — |
| `recommended_action_code` | `VARCHAR(80)` | No | — | — |
| `occurrence_count` | `INTEGER` | No | — | — |
| `reopen_count` | `INTEGER` | No | — | — |
| `first_detected_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `last_detected_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `last_activity_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `resolved_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `resolution_reason_code` | `VARCHAR(80)` | Yes | — | — |
| `resolution_note` | `TEXT` | Yes | — | — |
| `resolution_external_reference` | `VARCHAR(255)` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `resolved_by_user_id` → `users.id` (ON DELETE SET NULL); `target_booking_id` → `bookings.id` (ON DELETE SET NULL); `target_credit_usage_id` → `game_credit_usage.id` (ON DELETE RESTRICT); `target_game_credit_id` → `game_credits.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE SET NULL); `target_payment_id` → `payments.id` (ON DELETE SET NULL); `target_refund_id` → `refunds.id` (ON DELETE RESTRICT); `target_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** `uq_money_issues_operation_key`: `operation_key`.
- **Other table relationships:** Referenced by `money_issue_events`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `status`: `open`, `resolved`; `issue_type`: `refund_missing_provider_reference`, `refund_processing_overdue`, `refund_failed`, `refund_cancelled`, `refund_outcome_unknown`, `credit_restore_failed`, `credit_release_failed`; `value_kind`: `cash_refund`, `game_credit_restore`, `game_credit_release`.
- **CHECK constraints:**
  - `ck_money_issues_amount_cents`: `amount_cents >= 0`
  - `ck_money_issues_credit_requires_usage`: `(issue_type NOT LIKE 'credit_%' OR target_credit_usage_id IS NOT NULL)`
  - `ck_money_issues_currency`: `currency = 'USD'`
  - `ck_money_issues_issue_type`: `issue_type IN ('refund_missing_provider_reference', 'refund_processing_overdue', 'refund_failed', 'refund_cancelled', 'refund_outcome_unknown', 'credit_restore_failed', 'credit_release_failed')`
  - `ck_money_issues_occurrence_count`: `occurrence_count >= 1`
  - `ck_money_issues_origin_workflow`: `origin_workflow IN ('player_removal', 'official_game_cancellation', 'community_publish_fee_refund', 'direct_admin_refund', 'official_game_checkout', 'pending_checkout_expiration', 'pending_checkout_cancellation', 'admin_game_update')`
  - `ck_money_issues_recommended_action_code`: `recommended_action_code IN ('recover_provider_reference', 'retry_refund', 'verify_provider_refund', 'retry_credit_restore', 'retry_credit_release', 'review_unknown_outcome', 'review_and_resolve_no_action', 'document_external_completion', 'reexecute_origin_workflow', 'review_superseding_financial_outcome')`
  - `ck_money_issues_refund_requires_refund`: `(issue_type NOT LIKE 'refund_%' OR target_refund_id IS NOT NULL)`
  - `ck_money_issues_reopen_count`: `reopen_count >= 0`
  - `ck_money_issues_resolution_fields_match_status`: `((status = 'open') AND resolved_at IS NULL AND resolved_by_user_id IS NULL AND resolution_reason_code IS NULL AND resolution_note IS NULL AND resolution_external_reference IS NULL) OR ((status = 'resolved') AND resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_reason_code IS NOT NULL)`
  - `ck_money_issues_resolution_reason_code`: `resolution_reason_code IS NULL OR resolution_reason_code IN ('retried_successfully', 'provider_completed_no_action_required', 'handled_externally', 'invalid_issue', 'unable_to_complete_documented', 'superseded_by_financial_outcome')`
  - `ck_money_issues_status`: `status IN ('open', 'resolved')`
  - `ck_money_issues_value_kind`: `value_kind IN ('cash_refund', 'game_credit_restore', 'game_credit_release')`
- **Indexes:**
  - `ix_money_issues_activity`: `money_issues.last_activity_at, money_issues.id`
  - `ix_money_issues_issue_type_status`: `money_issues.issue_type, money_issues.status`
  - `ix_money_issues_open_queue`: `money_issues.status, money_issues.first_detected_at, money_issues.id`
  - `ix_money_issues_origin_workflow_status`: `money_issues.origin_workflow, money_issues.status`
  - `ix_money_issues_resolved`: `money_issues.resolved_at, money_issues.id`
  - `ix_money_issues_target_booking_id`: `money_issues.target_booking_id`
  - `ix_money_issues_target_credit_usage_id`: `money_issues.target_credit_usage_id`
  - `ix_money_issues_target_game_credit_id`: `money_issues.target_game_credit_id`
  - `ix_money_issues_target_game_id`: `money_issues.target_game_id`
  - `ix_money_issues_target_payment_id`: `money_issues.target_payment_id`
  - `ix_money_issues_target_refund_id`: `money_issues.target_refund_id`
  - `ix_money_issues_target_user_id`: `money_issues.target_user_id`

### `money_issue_events`

Recorded money-issue state changes. Sources: [model](../../backend/models/money_issue_event_model.py), [canonical migration](../../backend/alembic/versions/0054_create_money_issue_events_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `money_issue_id` | `UUID` | No | — | FK → `money_issues.id` |
| `event_type` | `VARCHAR(60)` | No | — | — |
| `event_source` | `VARCHAR(20)` | No | — | — |
| `actor_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `refund_event_id` | `UUID` | Yes | — | FK → `refund_events.id` |
| `result_credit_usage_id` | `UUID` | Yes | — | FK → `game_credit_usage.id` |
| `previous_status` | `VARCHAR(20)` | Yes | — | — |
| `new_status` | `VARCHAR(20)` | Yes | — | — |
| `previous_issue_type` | `VARCHAR(80)` | Yes | — | — |
| `new_issue_type` | `VARCHAR(80)` | Yes | — | — |
| `previous_recommended_action_code` | `VARCHAR(80)` | Yes | — | — |
| `new_recommended_action_code` | `VARCHAR(80)` | Yes | — | — |
| `reason_code` | `VARCHAR(80)` | Yes | — | — |
| `summary` | `TEXT` | Yes | — | — |
| `metadata` | `JSONB` | Yes | — | — |
| `occurred_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `actor_user_id` → `users.id` (ON DELETE SET NULL); `admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `money_issue_id` → `money_issues.id` (ON DELETE CASCADE); `refund_event_id` → `refund_events.id` (ON DELETE SET NULL); `result_credit_usage_id` → `game_credit_usage.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `event_type`: `issue_opened`, `issue_reopened`, `classification_changed`, `recommended_action_changed`, `admin_retry_initiated`, `refund_outcome_linked`, `credit_restore_failed`, `credit_restore_succeeded`, `credit_release_failed`, `credit_release_succeeded`, `issue_resolved`; `previous_status`: no table-local value CHECK; application-defined or historical value; `new_status`: no table-local value CHECK; application-defined or historical value; `previous_issue_type`: no table-local value CHECK; application-defined or historical value; `new_issue_type`: no table-local value CHECK; application-defined or historical value.
- **CHECK constraints:**
  - `ck_money_issue_events_event_source`: `event_source IN ('system', 'admin')`
  - `ck_money_issue_events_event_type`: `event_type IN ('issue_opened', 'issue_reopened', 'classification_changed', 'recommended_action_changed', 'admin_retry_initiated', 'refund_outcome_linked', 'credit_restore_failed', 'credit_restore_succeeded', 'credit_release_failed', 'credit_release_succeeded', 'issue_resolved')`
- **Indexes:**
  - `ix_money_issue_events_issue_occurred_id`: `money_issue_events.money_issue_id, money_issue_events.occurred_at, money_issue_events.id`
  - `ix_money_issue_events_money_issue_id`: `money_issue_events.money_issue_id`
  - `ix_money_issue_events_refund_event_id`: `money_issue_events.refund_event_id`
  - `ix_money_issue_events_result_credit_usage_id`: `money_issue_events.result_credit_usage_id`

## Need a Sub posts and requests

### `sub_posts`

Need a Sub listing, owner, schedule, and lifecycle. Sources: [model](../../backend/models/sub_post_model.py), [canonical migration](../../backend/alembic/versions/0008_create_sub_posts_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `owner_user_id` | `UUID` | No | — | FK → `users.id` |
| `post_status` | `VARCHAR(30)` | No | — | — |
| `public_visibility_status` | `VARCHAR(20)` | No | server `'visible'` | — |
| `sport_type` | `VARCHAR(50)` | No | server `'soccer'` | — |
| `format_label` | `VARCHAR(20)` | No | — | — |
| `environment_type` | `VARCHAR(20)` | No | — | — |
| `skill_level` | `VARCHAR(30)` | No | — | — |
| `game_player_group` | `VARCHAR(30)` | No | — | — |
| `team_name` | `VARCHAR(120)` | Yes | — | — |
| `starts_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `ends_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `starts_on_local` | `DATE` | No | — | — |
| `timezone` | `VARCHAR(60)` | No | server `'America/Chicago'` | — |
| `location_name` | `VARCHAR(150)` | No | — | — |
| `address_line_1` | `VARCHAR(200)` | No | — | — |
| `city` | `VARCHAR(100)` | No | — | — |
| `state` | `VARCHAR(100)` | No | — | — |
| `postal_code` | `VARCHAR(20)` | No | — | — |
| `country_code` | `CHAR(2)` | No | server `'US'` | — |
| `neighborhood` | `VARCHAR(120)` | Yes | — | — |
| `subs_needed` | `INTEGER` | No | — | — |
| `price_due_at_venue_cents` | `INTEGER` | No | server `0` | — |
| `currency` | `CHAR(3)` | No | server `'USD'` | — |
| `payment_note` | `TEXT` | Yes | — | — |
| `notes` | `TEXT` | Yes | — | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `filled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `canceled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `canceled_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `cancel_reason` | `TEXT` | Yes | — | — |
| `removed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `removed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `remove_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `canceled_by_user_id` → `users.id` (ON DELETE SET NULL); `owner_user_id` → `users.id` (ON DELETE RESTRICT); `removed_by_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_financial_outcomes`, `admin_review_cases`, `admin_review_signals`, `admin_target_notices`, `sub_post_chats`, `sub_post_positions`, `sub_post_requests`, `sub_post_status_history`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `post_status`: `active`, `completed`, `cancelled`, `expired`, `removed`; `public_visibility_status`: `visible`, `hidden`; `sport_type`: `soccer`; `environment_type`: `indoor`, `outdoor`.
- **CHECK constraints:**
  - `ck_sub_posts_canceled_requires_canceled_at`: `post_status != 'cancelled' OR canceled_at IS NOT NULL`
  - `ck_sub_posts_completed_requires_filled_at`: `post_status != 'completed' OR filled_at IS NOT NULL`
  - `ck_sub_posts_currency`: `currency = 'USD'`
  - `ck_sub_posts_environment_type`: `environment_type IN ('indoor', 'outdoor')`
  - `ck_sub_posts_expires_not_after_starts`: `expires_at <= starts_at`
  - `ck_sub_posts_game_player_group`: `game_player_group IN ('men', 'women', 'coed')`
  - `ck_sub_posts_post_status`: `post_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')`
  - `ck_sub_posts_price_due_non_negative`: `price_due_at_venue_cents >= 0`
  - `ck_sub_posts_public_visibility_status`: `public_visibility_status IN ('visible', 'hidden')`
  - `ck_sub_posts_removed_requires_removed_at`: `post_status != 'removed' OR removed_at IS NOT NULL`
  - `ck_sub_posts_skill_level`: `skill_level IN ('any', 'beginner', 'recreational', 'intermediate', 'advanced', 'competitive')`
  - `ck_sub_posts_sport_type`: `sport_type IN ('soccer')`
  - `ck_sub_posts_starts_before_ends`: `starts_at < ends_at`
  - `ck_sub_posts_subs_needed_positive`: `subs_needed > 0`
- **Indexes:**
  - `ix_sub_posts_admin_city_trgm`: `sub_posts.city` (`USING gin`; `operator classes {'city': 'gin_trgm_ops'}`)
  - `ix_sub_posts_admin_location_name_trgm`: `sub_posts.location_name` (`USING gin`; `operator classes {'location_name': 'gin_trgm_ops'}`)
  - `ix_sub_posts_admin_state_trgm`: `sub_posts.state` (`USING gin`; `operator classes {'state': 'gin_trgm_ops'}`)
  - `ix_sub_posts_admin_status_local_starts_created_id`: `sub_posts.post_status, sub_posts.starts_on_local, sub_posts.starts_at, sub_posts.created_at, sub_posts.id`
  - `ix_sub_posts_admin_team_name_trgm`: `sub_posts.team_name` (`USING gin`; `operator classes {'team_name': 'gin_trgm_ops'}`)
  - `ix_sub_posts_browse_active_starts_at`: `sub_posts.starts_at` (`WHERE post_status = 'active' AND public_visibility_status = 'visible'`)
  - `ix_sub_posts_cards_active_local_starts_created_id`: `sub_posts.starts_on_local, sub_posts.starts_at, sub_posts.created_at, sub_posts.id` (`WHERE post_status = 'active' AND public_visibility_status = 'visible'`)
  - `ix_sub_posts_city_state_starts_at`: `sub_posts.city, sub_posts.state, sub_posts.starts_at`
  - `ix_sub_posts_expires_at`: `sub_posts.expires_at`
  - `ix_sub_posts_owner_cards_active_local_starts_created_id`: `sub_posts.owner_user_id, sub_posts.starts_on_local, sub_posts.starts_at, sub_posts.created_at, sub_posts.id` (`WHERE post_status = 'active' AND public_visibility_status = 'visible'`)
  - `ix_sub_posts_owner_user_id`: `sub_posts.owner_user_id`
  - `ix_sub_posts_post_status`: `sub_posts.post_status`
  - `ix_sub_posts_post_status_starts_at`: `sub_posts.post_status, sub_posts.starts_at`
  - `ix_sub_posts_starts_at`: `sub_posts.starts_at`
  - `ix_sub_posts_starts_on_local`: `sub_posts.starts_on_local`
  - `ux_sub_posts_owner_active_starts_on_local`: `sub_posts.owner_user_id, sub_posts.starts_on_local` (`UNIQUE`; `WHERE post_status = 'active'`)

### `sub_post_positions`

Requested openings within a Need a Sub post. Sources: [model](../../backend/models/sub_post_position_model.py), [canonical migration](../../backend/alembic/versions/0017_create_sub_post_positions_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `sub_post_id` | `UUID` | No | — | FK → `sub_posts.id` |
| `position_label` | `VARCHAR(50)` | No | — | — |
| `player_group` | `VARCHAR(30)` | No | server `'open'` | — |
| `spots_needed` | `INTEGER` | No | server `1` | — |
| `sort_order` | `INTEGER` | No | server `0` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `sub_post_id` → `sub_posts.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_sub_post_positions_id_sub_post_id`: `id, sub_post_id`; `uq_sub_post_positions_post_position_group`: `sub_post_id, position_label, player_group`.
- **Other table relationships:** Referenced by `sub_post_requests`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:**
  - `ck_sub_post_positions_player_group`: `player_group IN ('open', 'men', 'women')`
  - `ck_sub_post_positions_position_label`: `position_label IN ('field_player', 'goalkeeper')`
  - `ck_sub_post_positions_sort_order_non_negative`: `sort_order >= 0`
  - `ck_sub_post_positions_spots_needed_positive`: `spots_needed > 0`
- **Indexes:**
  - `ix_sub_post_positions_sub_post_id`: `sub_post_positions.sub_post_id`

### `sub_post_requests`

Player requests for Need a Sub openings. Sources: [model](../../backend/models/sub_post_request_model.py), [canonical migration](../../backend/alembic/versions/0027_create_sub_post_requests_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `sub_post_id` | `UUID` | No | — | FK → `sub_post_positions.sub_post_id`; FK → `sub_posts.id` |
| `sub_post_position_id` | `UUID` | No | — | FK → `sub_post_positions.id`; FK → `sub_post_positions.id` |
| `requester_user_id` | `UUID` | No | — | FK → `users.id` |
| `request_status` | `VARCHAR(30)` | No | server `'pending'` | — |
| `confirmed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `declined_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `sub_waitlisted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `canceled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `expired_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `no_show_reported_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `requester_user_id` → `users.id` (ON DELETE RESTRICT); `sub_post_id` → `sub_posts.id` (ON DELETE CASCADE); `sub_post_position_id` → `sub_post_positions.id` (ON DELETE RESTRICT); `sub_post_position_id, sub_post_id` → `sub_post_positions.id, sub_post_positions.sub_post_id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_review_cases`, `admin_review_signals`, `admin_target_notices`, `sub_post_request_status_history`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `request_status`: `pending`, `confirmed`, `declined`, `sub_waitlist`, `canceled_by_player`, `canceled_by_owner`, `no_show_reported`, `expired`, `closed_by_admin`.
- **CHECK constraints:**
  - `ck_sub_post_requests_canceled_requires_canceled_at`: `request_status NOT IN ('canceled_by_player', 'canceled_by_owner') OR canceled_at IS NOT NULL`
  - `ck_sub_post_requests_confirmed_requires_confirmed_at`: `request_status != 'confirmed' OR confirmed_at IS NOT NULL`
  - `ck_sub_post_requests_declined_requires_declined_at`: `request_status != 'declined' OR declined_at IS NOT NULL`
  - `ck_sub_post_requests_expired_requires_expired_at`: `request_status != 'expired' OR expired_at IS NOT NULL`
  - `ck_sub_post_requests_no_show_requires_reported_at`: `request_status != 'no_show_reported' OR no_show_reported_at IS NOT NULL`
  - `ck_sub_post_requests_request_status`: `request_status IN ('pending', 'confirmed', 'declined', 'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', 'no_show_reported', 'expired', 'closed_by_admin')`
  - `ck_sub_post_requests_waitlist_requires_waitlisted_at`: `request_status != 'sub_waitlist' OR sub_waitlisted_at IS NOT NULL`
- **Indexes:**
  - `ix_sub_post_requests_position_status`: `sub_post_requests.sub_post_position_id, sub_post_requests.request_status`
  - `ix_sub_post_requests_post_status`: `sub_post_requests.sub_post_id, sub_post_requests.request_status`
  - `ix_sub_post_requests_requester_status`: `sub_post_requests.requester_user_id, sub_post_requests.request_status`
  - `ix_sub_post_requests_requester_user_id`: `sub_post_requests.requester_user_id`
  - `ix_sub_post_requests_sub_post_id`: `sub_post_requests.sub_post_id`
  - `ix_sub_post_requests_sub_post_position_id`: `sub_post_requests.sub_post_position_id`
  - `uq_sub_post_requests_active_post_requester`: `sub_post_requests.sub_post_id, sub_post_requests.requester_user_id` (`UNIQUE`; `WHERE request_status IN ('pending', 'confirmed', 'sub_waitlist')`)

### `sub_post_status_history`

Recorded Need a Sub post state changes. Sources: [model](../../backend/models/sub_post_status_history_model.py), [canonical migration](../../backend/alembic/versions/0018_create_sub_post_status_history_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `sub_post_id` | `UUID` | No | — | FK → `sub_posts.id` |
| `old_status` | `VARCHAR(30)` | Yes | — | — |
| `new_status` | `VARCHAR(30)` | No | — | — |
| `changed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `change_source` | `VARCHAR(30)` | No | — | — |
| `change_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `changed_by_user_id` → `users.id` (ON DELETE SET NULL); `sub_post_id` → `sub_posts.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `old_status`: `active`, `completed`, `cancelled`, `expired`, `removed`; `new_status`: `active`, `completed`, `cancelled`, `expired`, `removed`.
- **CHECK constraints:**
  - `ck_sub_post_status_history_change_source`: `change_source IN ('owner', 'admin', 'system', 'scheduled_job')`
  - `ck_sub_post_status_history_new_status`: `new_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')`
  - `ck_sub_post_status_history_old_status`: `old_status IS NULL OR old_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')`
- **Indexes:**
  - `ix_sub_post_status_history_changed_by_user_id`: `sub_post_status_history.changed_by_user_id`
  - `ix_sub_post_status_history_post_created`: `sub_post_status_history.sub_post_id, sub_post_status_history.created_at`

### `sub_post_request_status_history`

Recorded Need a Sub request state changes. Sources: [model](../../backend/models/sub_post_request_status_history_model.py), [canonical migration](../../backend/alembic/versions/0036_create_sub_post_request_status_history_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `sub_post_request_id` | `UUID` | No | — | FK → `sub_post_requests.id` |
| `old_status` | `VARCHAR(30)` | Yes | — | — |
| `new_status` | `VARCHAR(30)` | No | — | — |
| `changed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `change_source` | `VARCHAR(30)` | No | — | — |
| `change_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `changed_by_user_id` → `users.id` (ON DELETE SET NULL); `sub_post_request_id` → `sub_post_requests.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `old_status`: `pending`, `confirmed`, `declined`, `sub_waitlist`, `canceled_by_player`, `canceled_by_owner`, `no_show_reported`, `expired`, `closed_by_admin`; `new_status`: `pending`, `confirmed`, `declined`, `sub_waitlist`, `canceled_by_player`, `canceled_by_owner`, `no_show_reported`, `expired`, `closed_by_admin`.
- **CHECK constraints:**
  - `ck_sub_post_request_status_history_change_source`: `change_source IN ('requester', 'owner', 'admin', 'system', 'scheduled_job')`
  - `ck_sub_post_request_status_history_new_status`: `new_status IN ('pending', 'confirmed', 'declined', 'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', 'no_show_reported', 'expired', 'closed_by_admin')`
  - `ck_sub_post_request_status_history_old_status`: `old_status IS NULL OR old_status IN ('pending', 'confirmed', 'declined', 'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', 'no_show_reported', 'expired', 'closed_by_admin')`
- **Indexes:**
  - `ix_sub_post_request_status_history_changed_by_user_id`: `sub_post_request_status_history.changed_by_user_id`
  - `ix_sub_post_request_status_history_request_created`: `sub_post_request_status_history.sub_post_request_id, sub_post_request_status_history.created_at`

### `sub_post_chats`

Chat threads attached to Need a Sub requests. Sources: [model](../../backend/models/sub_post_chat_model.py), [canonical migration](../../backend/alembic/versions/0016_create_sub_post_chats_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `sub_post_id` | `UUID` | No | — | FK → `sub_posts.id` |
| `chat_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `closed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `message_count` | `INTEGER` | No | server `0` | — |
| `needs_review_count` | `INTEGER` | No | server `0` | — |
| `removed_count` | `INTEGER` | No | server `0` | — |
| `latest_message_id` | `UUID` | Yes | — | — |
| `latest_message_preview` | `TEXT` | Yes | — | — |
| `latest_message_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `sub_post_id` → `sub_posts.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_sub_post_chats_sub_post_id`: `sub_post_id`.
- **Other table relationships:** Referenced by `sub_post_chat_messages`, `sub_post_chat_reads`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `chat_status`: `active`, `closed`.
- **CHECK constraints:**
  - `ck_sub_post_chats_chat_status`: `chat_status IN ('active', 'closed')`
  - `ck_sub_post_chats_closed_requires_closed_at`: `(chat_status = 'active' AND closed_at IS NULL) OR (chat_status = 'closed' AND closed_at IS NOT NULL)`
- **Indexes:**
  - `ix_sub_post_chats_chat_status`: `sub_post_chats.chat_status`
  - `ix_sub_post_chats_latest_message_at`: `sub_post_chats.latest_message_at`
  - `ix_sub_post_chats_needs_review_count`: `sub_post_chats.needs_review_count`
  - `ix_sub_post_chats_sub_post_id`: `sub_post_chats.sub_post_id`

### `sub_post_chat_messages`

Messages in Need a Sub chats. Sources: [model](../../backend/models/sub_post_chat_message_model.py), [canonical migration](../../backend/alembic/versions/0026_create_sub_post_chat_messages_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `chat_id` | `UUID` | No | — | FK → `sub_post_chats.id` |
| `sender_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `sender_display_name_snapshot` | `VARCHAR(120)` | No | — | — |
| `sender_initials_snapshot` | `VARCHAR(8)` | No | — | — |
| `message_type` | `VARCHAR(30)` | No | server `'text'` | — |
| `message_body` | `TEXT` | No | — | — |
| `visibility_status` | `VARCHAR(30)` | No | server `'visible'` | — |
| `review_status` | `VARCHAR(30)` | No | server `'clear'` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `reviewed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `reviewed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `removed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `removed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `removed_source` | `VARCHAR(30)` | Yes | — | — |
| `removed_reason` | `TEXT` | Yes | — | — |
| `restored_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `restored_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `restored_reason` | `TEXT` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `chat_id` → `sub_post_chats.id` (ON DELETE RESTRICT); `removed_by_user_id` → `users.id` (ON DELETE SET NULL); `restored_by_user_id` → `users.id` (ON DELETE SET NULL); `reviewed_by_user_id` → `users.id` (ON DELETE SET NULL); `sender_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `sub_post_chat_message_detections`, `sub_post_chat_reads`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `message_type`: `text`; `visibility_status`: `visible`, `removed`; `review_status`: `clear`, `needs_review`, `reviewed`.
- **CHECK constraints:**
  - `ck_sub_post_chat_messages_body_max_length`: `char_length(message_body) <= 300`
  - `ck_sub_post_chat_messages_body_not_empty`: `char_length(btrim(message_body)) > 0`
  - `ck_sub_post_chat_messages_message_type`: `message_type IN ('text')`
  - `ck_sub_post_chat_messages_removed_requires_removed_at`: `(visibility_status <> 'removed' OR removed_at IS NOT NULL)`
  - `ck_sub_post_chat_messages_removed_requires_source`: `(visibility_status <> 'removed' OR removed_source IS NOT NULL)`
  - `ck_sub_post_chat_messages_removed_source`: `removed_source IS NULL OR removed_source IN ('admin', 'sender', 'system')`
  - `ck_sub_post_chat_messages_review_status`: `review_status IN ('clear', 'needs_review', 'reviewed')`
  - `ck_sub_post_chat_messages_reviewed_requires_reviewed_at`: `(review_status <> 'reviewed' OR reviewed_at IS NOT NULL)`
  - `ck_sub_post_chat_messages_sender_initials_not_empty`: `char_length(btrim(sender_initials_snapshot)) > 0`
  - `ck_sub_post_chat_messages_sender_name_not_empty`: `char_length(btrim(sender_display_name_snapshot)) > 0`
  - `ck_sub_post_chat_messages_visibility_status`: `visibility_status IN ('visible', 'removed')`
- **Indexes:**
  - `ix_sub_post_chat_messages_chat_id`: `sub_post_chat_messages.chat_id`
  - `ix_sub_post_chat_messages_chat_id_created_at`: `sub_post_chat_messages.chat_id, sub_post_chat_messages.created_at`
  - `ix_sub_post_chat_messages_chat_id_review_status`: `sub_post_chat_messages.chat_id, sub_post_chat_messages.review_status`
  - `ix_sub_post_chat_messages_chat_id_visibility_status`: `sub_post_chat_messages.chat_id, sub_post_chat_messages.visibility_status`
  - `ix_sub_post_chat_messages_removed_by_user_id`: `sub_post_chat_messages.removed_by_user_id`
  - `ix_sub_post_chat_messages_restored_by_user_id`: `sub_post_chat_messages.restored_by_user_id`
  - `ix_sub_post_chat_messages_review_status`: `sub_post_chat_messages.review_status`
  - `ix_sub_post_chat_messages_reviewed_by_user_id`: `sub_post_chat_messages.reviewed_by_user_id`
  - `ix_sub_post_chat_messages_sender_user_id`: `sub_post_chat_messages.sender_user_id`
  - `ix_sub_post_chat_messages_visibility_status`: `sub_post_chat_messages.visibility_status`

### `sub_post_chat_reads`

Per-user read position in Need a Sub chats. Sources: [model](../../backend/models/sub_post_chat_read_model.py), [canonical migration](../../backend/alembic/versions/0035_create_sub_post_chat_reads_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `chat_id` | `UUID` | No | — | FK → `sub_post_chats.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `last_read_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `last_read_message_id` | `UUID` | Yes | — | FK → `sub_post_chat_messages.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `chat_id` → `sub_post_chats.id` (ON DELETE CASCADE); `last_read_message_id` → `sub_post_chat_messages.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_sub_post_chat_reads_chat_user`: `chat_id, user_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_sub_post_chat_reads_chat_id`: `sub_post_chat_reads.chat_id`
  - `ix_sub_post_chat_reads_user_id`: `sub_post_chat_reads.user_id`

### `sub_post_chat_message_detections`

Moderation detection records for Need a Sub messages. Sources: [model](../../backend/models/sub_post_chat_message_detection_model.py), [canonical migration](../../backend/alembic/versions/0034_create_sub_post_chat_message_detections_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `message_id` | `UUID` | No | — | FK → `sub_post_chat_messages.id` |
| `category` | `VARCHAR(50)` | No | — | — |
| `severity` | `VARCHAR(20)` | No | — | — |
| `rule_key` | `VARCHAR(80)` | No | — | — |
| `matched_preview` | `VARCHAR(240)` | Yes | — | — |
| `scanner_id` | `VARCHAR(80)` | No | — | — |
| `scanner_version` | `VARCHAR(80)` | No | — | — |
| `taxonomy_version` | `VARCHAR(40)` | No | — | — |
| `configuration_hash` | `VARCHAR(64)` | No | — | — |
| `canonicalization_version` | `VARCHAR(80)` | No | — | — |
| `evidence_format_version` | `VARCHAR(40)` | No | — | — |
| `target_context` | `VARCHAR(60)` | No | — | — |
| `field_purpose` | `VARCHAR(40)` | No | — | — |
| `source_field` | `VARCHAR(80)` | No | — | — |
| `source_content_hash` | `VARCHAR(64)` | No | — | — |
| `matched_rule_versions` | `JSONB` | No | — | — |
| `declared_limits` | `JSONB` | No | — | — |
| `evidence_fingerprint` | `VARCHAR(64)` | No | — | — |
| `evidence` | `JSONB` | No | — | — |
| `scanned_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `detection_identity_hash` | `VARCHAR(64)` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `message_id` → `sub_post_chat_messages.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_sub_post_chat_message_detections_message_identity`: `message_id, detection_identity_hash`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `category`: `phone_number`, `email`, `link`, `off_platform_contact`, `payment_discussion`, `harassment_or_abuse`, `threat_or_safety`, `slur_or_hate`, `spam_or_repeated_message`.
- **CHECK constraints:**
  - `ck_sub_post_chat_message_detections_category`: `category IN ('phone_number', 'email', 'link', 'off_platform_contact', 'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', 'slur_or_hate', 'spam_or_repeated_message')`
  - `ck_sub_post_chat_message_detections_configuration_hash`: `configuration_hash ~ '^[0-9a-f]{64}$'`
  - `ck_sub_post_chat_message_detections_declared_limits_nonempty`: `jsonb_typeof(declared_limits) = 'array' AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16`
  - `ck_sub_post_chat_message_detections_evidence_fingerprint`: `evidence_fingerprint ~ '^[0-9a-f]{64}$'`
  - `ck_sub_post_chat_message_detections_evidence_shape`: `jsonb_typeof(evidence) = 'object' AND jsonb_typeof(evidence->'evidence_kind') = 'string' AND COALESCE(evidence->>'evidence_kind', '') IN ('span', 'context_predicate')`
  - `ck_sub_post_chat_message_detections_identity_hash`: `detection_identity_hash ~ '^[0-9a-f]{64}$'`
  - `ck_sub_post_chat_message_detections_provenance_present`: `length(trim(scanner_id)) > 0 AND length(trim(scanner_version)) > 0 AND length(trim(taxonomy_version)) > 0 AND length(trim(canonicalization_version)) > 0 AND length(trim(evidence_format_version)) > 0 AND length(trim(target_context)) > 0 AND length(trim(field_purpose)) > 0 AND length(trim(source_field)) > 0`
  - `ck_sub_post_chat_message_detections_rule_key_present`: `length(trim(rule_key)) > 0`
  - `ck_sub_post_chat_message_detections_rule_versions_nonempty`: `jsonb_typeof(matched_rule_versions) = 'array' AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32`
  - `ck_sub_post_chat_message_detections_severity`: `severity IN ('low', 'medium', 'high')`
  - `ck_sub_post_chat_message_detections_source_hash`: `source_content_hash ~ '^[0-9a-f]{64}$'`
- **Indexes:**
  - `ix_sub_post_chat_message_detections_category`: `sub_post_chat_message_detections.category`
  - `ix_sub_post_chat_message_detections_created_at`: `sub_post_chat_message_detections.created_at`
  - `ix_sub_post_chat_message_detections_message_id`: `sub_post_chat_message_detections.message_id`

## Notifications and communications

### `notifications`

Individual user notification feed records. Sources: [model](../../backend/models/notification_model.py), [canonical migration](../../backend/alembic/versions/0051_create_notifications_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `notification_type` | `VARCHAR(50)` | No | — | — |
| `notification_category` | `VARCHAR(30)` | No | — | — |
| `notification_domain` | `VARCHAR(40)` | No | — | — |
| `source_type` | `VARCHAR(40)` | No | — | — |
| `title` | `VARCHAR(150)` | No | — | — |
| `subject_label` | `VARCHAR(160)` | No | — | — |
| `summary` | `TEXT` | No | — | — |
| `body` | `TEXT` | No | — | — |
| `action_key` | `VARCHAR(40)` | Yes | — | — |
| `subject_starts_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `subject_ends_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `subject_timezone` | `VARCHAR(80)` | Yes | — | — |
| `event_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `aggregation_key` | `VARCHAR(180)` | Yes | — | — |
| `aggregate_count` | `INTEGER` | Yes | — | — |
| `actor_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `related_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `related_chat_id` | `UUID` | Yes | — | FK → `game_chats.id` |
| `related_booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `related_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `related_refund_id` | `UUID` | Yes | — | FK → `refunds.id` |
| `related_participant_id` | `UUID` | Yes | — | FK → `game_participants.id` |
| `related_message_id` | `UUID` | Yes | — | FK → `chat_messages.id` |
| `related_sub_post_id` | `UUID` | Yes | — | — |
| `related_sub_post_chat_id` | `UUID` | Yes | — | — |
| `related_sub_post_chat_message_id` | `UUID` | Yes | — | — |
| `related_sub_post_request_id` | `UUID` | Yes | — | — |
| `related_sub_post_position_id` | `UUID` | Yes | — | — |
| `is_read` | `BOOLEAN` | No | server `false` | — |
| `read_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `actor_user_id` → `users.id` (ON DELETE SET NULL); `related_booking_id` → `bookings.id` (ON DELETE SET NULL); `related_chat_id` → `game_chats.id` (ON DELETE SET NULL); `related_game_id` → `games.id` (ON DELETE SET NULL); `related_message_id` → `chat_messages.id` (ON DELETE SET NULL); `related_participant_id` → `game_participants.id` (ON DELETE SET NULL); `related_payment_id` → `payments.id` (ON DELETE SET NULL); `related_refund_id` → `refunds.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `notification_type`: `admin_enforcement_notice`, `policy_update`, `booking_confirmed`, `booking_cancelled`, `booking_refunded`, `payment_failed`, `game_cancelled`, `game_updated`, `game_reminder`, `waitlist_joined`, `waitlist_promoted`, `waitlist_expired`, `host_update`, `chat_message`, `deposit_paid`, `deposit_released`, `deposit_forfeited`, `support_reply`, `account_security`, `game_player_added_by_admin`, `game_player_removed_by_admin`, `game_host_assigned`, `game_host_removed`, `game_roster_update`, `sub_request_received`, `sub_request_confirmed`, `sub_request_declined`, `sub_waitlist_promoted_to_pending`, `sub_request_canceled_by_player`, `sub_request_canceled_by_owner`, `sub_post_canceled`, `sub_post_removed`, `sub_post_updated`, `sub_chat_message`; `notification_category`: `app`, `game_activity`; `source_type`: `need_a_sub`, `official_game`, `community_game`, `game`, `pickup_lane`, `policy`, `support`, `account`, `payment`.
- **CHECK constraints:**
  - `ck_notifications_action_key`: `action_key IS NULL OR action_key IN ('view_game', 'view_sub_post', 'view_policy', 'payment_methods', 'view_profile')`
  - `ck_notifications_aggregate_count_positive`: `aggregate_count IS NULL OR aggregate_count >= 1`
  - `ck_notifications_aggregate_count_requires_key`: `aggregate_count IS NULL OR aggregation_key IS NOT NULL`
  - `ck_notifications_aggregation_key_not_empty`: `aggregation_key IS NULL OR char_length(btrim(aggregation_key)) > 0`
  - `ck_notifications_body_not_empty`: `char_length(btrim(body)) > 0`
  - `ck_notifications_category_domain_match`: `((notification_category = 'app' AND notification_domain IN ('app', 'account', 'admin', 'support')) OR (notification_category = 'game_activity' AND notification_domain IN ('game', 'need_a_sub')))`
  - `ck_notifications_notification_category`: `notification_category IN ('app', 'game_activity')`
  - `ck_notifications_notification_domain`: `notification_domain IN ('app', 'account', 'admin', 'support', 'game', 'need_a_sub')`
  - `ck_notifications_notification_type`: `notification_type IN ('booking_confirmed', 'booking_cancelled', 'booking_refunded', 'payment_failed', 'game_cancelled', 'game_updated', 'game_reminder', 'waitlist_joined', 'waitlist_promoted', 'waitlist_expired', 'host_update', 'chat_message', 'deposit_paid', 'deposit_released', 'deposit_forfeited', 'admin_enforcement_notice', 'support_reply', 'account_security', 'policy_update', 'game_player_added_by_admin', 'game_player_removed_by_admin', 'game_host_assigned', 'game_host_removed', 'game_roster_update', 'sub_request_received', 'sub_request_confirmed', 'sub_request_declined', 'sub_waitlist_promoted_to_pending', 'sub_request_canceled_by_player', 'sub_request_canceled_by_owner', 'sub_post_canceled', 'sub_post_removed', 'sub_post_updated', 'sub_chat_message')`
  - `ck_notifications_read_state_matches_read_at`: `((is_read = true AND read_at IS NOT NULL) OR (is_read = false AND read_at IS NULL))`
  - `ck_notifications_source_domain_match`: `((notification_domain = 'need_a_sub' AND source_type = 'need_a_sub') OR (notification_domain = 'game' AND source_type IN ('official_game', 'community_game', 'game')) OR (notification_domain = 'support' AND source_type = 'support') OR (notification_domain = 'account' AND source_type IN ('account', 'payment')) OR (notification_domain IN ('app', 'admin') AND source_type IN ('pickup_lane', 'policy', 'payment')))`
  - `ck_notifications_source_type`: `source_type IN ('need_a_sub', 'official_game', 'community_game', 'game', 'pickup_lane', 'policy', 'support', 'account', 'payment')`
  - `ck_notifications_subject_label_not_empty`: `char_length(btrim(subject_label)) > 0`
  - `ck_notifications_subject_start_requires_timezone`: `subject_starts_at IS NULL OR subject_timezone IS NOT NULL`
  - `ck_notifications_subject_time_order`: `subject_ends_at IS NULL OR subject_starts_at IS NULL OR subject_ends_at >= subject_starts_at`
  - `ck_notifications_subject_timezone_not_empty`: `subject_timezone IS NULL OR char_length(btrim(subject_timezone)) > 0`
  - `ck_notifications_summary_not_empty`: `char_length(btrim(summary)) > 0`
  - `ck_notifications_title_not_empty`: `char_length(btrim(title)) > 0`
  - `ck_notifications_type_category_domain_match`: `((notification_type IN ('admin_enforcement_notice', 'policy_update') AND notification_category = 'app' AND notification_domain IN ('app', 'admin')) OR (notification_type = 'support_reply' AND notification_category = 'app' AND notification_domain = 'support') OR (notification_type = 'account_security' AND notification_category = 'app' AND notification_domain = 'account') OR (notification_type IN ('sub_request_received', 'sub_request_confirmed', 'sub_request_declined', 'sub_waitlist_promoted_to_pending', 'sub_request_canceled_by_player', 'sub_request_canceled_by_owner', 'sub_post_canceled', 'sub_post_removed', 'sub_post_updated', 'sub_chat_message') AND notification_category = 'game_activity' AND notification_domain = 'need_a_sub') OR (notification_type IN ('booking_confirmed', 'booking_cancelled', 'booking_refunded', 'payment_failed', 'game_cancelled', 'game_updated', 'game_reminder', 'waitlist_joined', 'waitlist_promoted', 'waitlist_expired', 'host_update', 'chat_message', 'deposit_paid', 'deposit_released', 'deposit_forfeited', 'game_player_added_by_admin', 'game_player_removed_by_admin', 'game_host_assigned', 'game_host_removed', 'game_roster_update') AND notification_category = 'game_activity' AND notification_domain = 'game'))`
- **Indexes:**
  - `ix_notifications_action_key`: `notifications.action_key`
  - `ix_notifications_actor_user_id`: `notifications.actor_user_id`
  - `ix_notifications_aggregation_key`: `notifications.aggregation_key`
  - `ix_notifications_created_at`: `notifications.created_at`
  - `ix_notifications_event_at`: `notifications.event_at`
  - `ix_notifications_is_read`: `notifications.is_read`
  - `ix_notifications_notification_category`: `notifications.notification_category`
  - `ix_notifications_notification_domain`: `notifications.notification_domain`
  - `ix_notifications_notification_type`: `notifications.notification_type`
  - `ix_notifications_related_booking_id`: `notifications.related_booking_id`
  - `ix_notifications_related_chat_id`: `notifications.related_chat_id`
  - `ix_notifications_related_game_id`: `notifications.related_game_id`
  - `ix_notifications_related_message_id`: `notifications.related_message_id`
  - `ix_notifications_related_participant_id`: `notifications.related_participant_id`
  - `ix_notifications_related_payment_id`: `notifications.related_payment_id`
  - `ix_notifications_related_refund_id`: `notifications.related_refund_id`
  - `ix_notifications_related_sub_post_chat_id`: `notifications.related_sub_post_chat_id`
  - `ix_notifications_related_sub_post_chat_message_id`: `notifications.related_sub_post_chat_message_id`
  - `ix_notifications_related_sub_post_id`: `notifications.related_sub_post_id`
  - `ix_notifications_related_sub_post_position_id`: `notifications.related_sub_post_position_id`
  - `ix_notifications_related_sub_post_request_id`: `notifications.related_sub_post_request_id`
  - `ix_notifications_source_type`: `notifications.source_type`
  - `ix_notifications_user_category_created_at`: `notifications.user_id, notifications.notification_category, notifications.created_at`
  - `ix_notifications_user_category_event_at`: `notifications.user_id, notifications.notification_category, notifications.event_at`
  - `ix_notifications_user_created_id`: `notifications.user_id, created_at DESC, id DESC`
  - `ix_notifications_user_event_created_id`: `notifications.user_id, notifications.event_at, notifications.created_at, notifications.id`
  - `ix_notifications_user_id`: `notifications.user_id`
  - `ix_notifications_user_id_is_read_created_at`: `notifications.user_id, notifications.is_read, notifications.created_at`
  - `ix_notifications_user_id_is_read_event_at`: `notifications.user_id, notifications.is_read, notifications.event_at`
  - `ux_notifications_user_aggregation_key`: `notifications.user_id, notifications.aggregation_key` (`UNIQUE`; `WHERE aggregation_key IS NOT NULL`)

### `platform_notices`

Staff-authored platform announcements. Sources: [model](../../backend/models/platform_notice_model.py), [canonical migration](../../backend/alembic/versions/0006_create_platform_notices_table.py#L15).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `title` | `VARCHAR(150)` | No | — | — |
| `message` | `TEXT` | No | — | — |
| `audience_type` | `VARCHAR(30)` | No | — | — |
| `global_sequence` | `BIGINT` | Yes | — | — |
| `published_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `created_by_admin_id` | `UUID` | Yes | — | FK → `users.id` |
| `idempotency_key_hash` | `VARCHAR(64)` | No | — | — |
| `request_fingerprint` | `VARCHAR(64)` | No | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_by_admin_id` | `UUID` | Yes | — | FK → `users.id` |
| `cancellation_reason` | `TEXT` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `cancelled_by_admin_id` → `users.id` (ON DELETE SET NULL); `created_by_admin_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `platform_notice_recipients`, `platform_notice_selected_reads`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `audience_type`: `all_eligible_users`, `selected_users`.
- **CHECK constraints:**
  - `ck_platform_notices_audience_type`: `audience_type IN ('all_eligible_users', 'selected_users')`
  - `ck_platform_notices_cancellation_integrity`: `(cancelled_at IS NULL AND cancelled_by_admin_id IS NULL AND cancellation_reason IS NULL) OR (cancelled_at IS NOT NULL AND cancelled_by_admin_id IS NOT NULL AND cancellation_reason IS NOT NULL)`
  - `ck_platform_notices_global_sequence_scope`: `(audience_type = 'all_eligible_users' AND global_sequence IS NOT NULL) OR (audience_type = 'selected_users' AND global_sequence IS NULL)`
  - `ck_platform_notices_message_not_empty`: `char_length(btrim(message)) > 0`
  - `ck_platform_notices_title_not_empty`: `char_length(btrim(title)) > 0`
- **Indexes:**
  - `ix_platform_notices_audience_cancelled_published_id`: `platform_notices.audience_type, platform_notices.cancelled_at, platform_notices.published_at, platform_notices.id`
  - `ix_platform_notices_cancelled_at`: `platform_notices.cancelled_at`
  - `ix_platform_notices_created_by_admin_id`: `platform_notices.created_by_admin_id`
  - `ix_platform_notices_history_order`: `published_at DESC, id DESC`
  - `ix_platform_notices_history_search_trgm`: `(coalesce(title, '') \|\| ' ' \|\| coalesce(message, '')) gin_trgm_ops` (`USING gin`)
  - `uq_platform_notices_admin_idempotency_key`: `platform_notices.created_by_admin_id, platform_notices.idempotency_key_hash` (`UNIQUE`)
  - `uq_platform_notices_global_sequence`: `platform_notices.global_sequence` (`UNIQUE`; `WHERE global_sequence IS NOT NULL`)

### `platform_notice_recipients`

Targeted recipients and delivery state for platform notices. Sources: [model](../../backend/models/platform_notice_recipient_model.py), [canonical migration](../../backend/alembic/versions/0014_create_platform_notice_recipients_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `notice_id` | `UUID` | No | — | PK; FK → `platform_notices.id` |
| `user_id` | `UUID` | No | — | PK; FK → `users.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `notice_id, user_id`.
- **Foreign keys:** `notice_id` → `platform_notices.id` (ON DELETE CASCADE); `user_id` → `users.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_platform_notice_recipients_user_notice`: `platform_notice_recipients.user_id, platform_notice_recipients.notice_id`

### `platform_notice_global_seen_states`

Per-user last-seen state for global notices. Sources: [model](../../backend/models/platform_notice_global_seen_state_model.py), [canonical migration](../../backend/alembic/versions/0005_create_platform_notice_global_seen_states_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `user_id` | `UUID` | No | — | PK; FK → `users.id` |
| `last_seen_global_sequence` | `BIGINT` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `user_id`.
- **Foreign keys:** `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:** None beyond the primary-key/unique-constraint backing indexes.

### `platform_notice_selected_reads`

Per-user read state for selected notices. Sources: [model](../../backend/models/platform_notice_selected_read_model.py), [canonical migration](../../backend/alembic/versions/0015_create_platform_notice_selected_reads_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `notice_id` | `UUID` | No | — | PK; FK → `platform_notices.id` |
| `user_id` | `UUID` | No | — | PK; FK → `users.id` |
| `read_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `notice_id, user_id`.
- **Foreign keys:** `notice_id` → `platform_notices.id` (ON DELETE CASCADE); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_platform_notice_selected_reads_user_notice`: `platform_notice_selected_reads.user_id, platform_notice_selected_reads.notice_id`

### `game_chats`

Chat rooms attached to games. Sources: [model](../../backend/models/game_chat_model.py), [canonical migration](../../backend/alembic/versions/0023_create_game_chats_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `game_id` | `UUID` | No | — | FK → `games.id` |
| `chat_status` | `VARCHAR(30)` | No | server `'active'` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `closed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `message_count` | `INTEGER` | No | server `0` | — |
| `needs_review_count` | `INTEGER` | No | server `0` | — |
| `removed_count` | `INTEGER` | No | server `0` | — |
| `latest_message_id` | `UUID` | Yes | — | — |
| `latest_message_preview` | `TEXT` | Yes | — | — |
| `latest_message_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `game_id` → `games.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_game_chats_game_id`: `game_id`.
- **Other table relationships:** Referenced by `chat_messages`, `game_chat_reads`, `notifications`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `chat_status`: `active`, `closed`.
- **CHECK constraints:**
  - `ck_game_chats_chat_status`: `chat_status IN ('active', 'closed')`
  - `ck_game_chats_closed_requires_closed_at`: `(chat_status = 'active' AND closed_at IS NULL) OR (chat_status = 'closed' AND closed_at IS NOT NULL)`
- **Indexes:**
  - `ix_game_chats_chat_status`: `game_chats.chat_status`
  - `ix_game_chats_latest_message_at`: `game_chats.latest_message_at`
  - `ix_game_chats_needs_review_count`: `game_chats.needs_review_count`

### `chat_messages`

Messages in game chats. Sources: [model](../../backend/models/chat_message_model.py), [canonical migration](../../backend/alembic/versions/0031_create_chat_messages_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `chat_id` | `UUID` | No | — | FK → `game_chats.id` |
| `sender_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `message_type` | `VARCHAR(30)` | No | server `'text'` | — |
| `message_body` | `TEXT` | No | — | — |
| `is_pinned` | `BOOLEAN` | No | server `false` | — |
| `pinned_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `pinned_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `visibility_status` | `VARCHAR(30)` | No | server `'visible'` | — |
| `review_status` | `VARCHAR(30)` | No | server `'clear'` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `reviewed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `reviewed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `removed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `removed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `removed_source` | `VARCHAR(30)` | Yes | — | — |
| `removed_reason` | `TEXT` | Yes | — | — |
| `restored_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `restored_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `restored_reason` | `TEXT` | Yes | — | — |

- **Primary key:** `id`.
- **Foreign keys:** `chat_id` → `game_chats.id` (ON DELETE RESTRICT); `pinned_by_user_id` → `users.id` (ON DELETE SET NULL); `removed_by_user_id` → `users.id` (ON DELETE SET NULL); `restored_by_user_id` → `users.id` (ON DELETE SET NULL); `reviewed_by_user_id` → `users.id` (ON DELETE SET NULL); `sender_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `game_chat_message_detections`, `game_chat_reads`, `notifications`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `message_type`: `text`, `system`, `pinned_update`; `visibility_status`: `visible`, `removed`; `review_status`: `clear`, `needs_review`, `reviewed`.
- **CHECK constraints:**
  - `ck_chat_messages_message_body_max_length`: `char_length(message_body) <= 300`
  - `ck_chat_messages_message_body_not_empty`: `char_length(btrim(message_body)) > 0`
  - `ck_chat_messages_message_type`: `message_type IN ('text', 'system', 'pinned_update')`
  - `ck_chat_messages_pinned_requires_pinned_at`: `(is_pinned = false OR pinned_at IS NOT NULL)`
  - `ck_chat_messages_pinned_requires_pinned_by_user`: `(is_pinned = false OR pinned_by_user_id IS NOT NULL)`
  - `ck_chat_messages_removed_requires_removed_at`: `(visibility_status <> 'removed' OR removed_at IS NOT NULL)`
  - `ck_chat_messages_removed_requires_source`: `(visibility_status <> 'removed' OR removed_source IS NOT NULL)`
  - `ck_chat_messages_removed_source`: `removed_source IS NULL OR removed_source IN ('admin', 'sender', 'system')`
  - `ck_chat_messages_review_status`: `review_status IN ('clear', 'needs_review', 'reviewed')`
  - `ck_chat_messages_reviewed_requires_reviewed_at`: `(review_status <> 'reviewed' OR reviewed_at IS NOT NULL)`
  - `ck_chat_messages_user_messages_require_sender`: `(message_type NOT IN ('text', 'pinned_update') OR sender_user_id IS NOT NULL)`
  - `ck_chat_messages_visibility_status`: `visibility_status IN ('visible', 'removed')`
- **Indexes:**
  - `ix_chat_messages_chat_id`: `chat_messages.chat_id`
  - `ix_chat_messages_chat_id_created_at`: `chat_messages.chat_id, chat_messages.created_at`
  - `ix_chat_messages_chat_id_is_pinned`: `chat_messages.chat_id, chat_messages.is_pinned`
  - `ix_chat_messages_chat_id_review_status`: `chat_messages.chat_id, chat_messages.review_status`
  - `ix_chat_messages_chat_id_visibility_status`: `chat_messages.chat_id, chat_messages.visibility_status`
  - `ix_chat_messages_pinned_by_user_id`: `chat_messages.pinned_by_user_id`
  - `ix_chat_messages_removed_by_user_id`: `chat_messages.removed_by_user_id`
  - `ix_chat_messages_restored_by_user_id`: `chat_messages.restored_by_user_id`
  - `ix_chat_messages_review_status`: `chat_messages.review_status`
  - `ix_chat_messages_reviewed_by_user_id`: `chat_messages.reviewed_by_user_id`
  - `ix_chat_messages_sender_user_id`: `chat_messages.sender_user_id`
  - `ix_chat_messages_visibility_status`: `chat_messages.visibility_status`

### `game_chat_reads`

Per-user read position in game chats. Sources: [model](../../backend/models/game_chat_read_model.py), [canonical migration](../../backend/alembic/versions/0040_create_game_chat_reads_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `chat_id` | `UUID` | No | — | FK → `game_chats.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `last_read_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `last_read_message_id` | `UUID` | Yes | — | FK → `chat_messages.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `chat_id` → `game_chats.id` (ON DELETE CASCADE); `last_read_message_id` → `chat_messages.id` (ON DELETE SET NULL); `user_id` → `users.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_game_chat_reads_chat_user`: `chat_id, user_id`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_game_chat_reads_chat_id`: `game_chat_reads.chat_id`
  - `ix_game_chat_reads_user_id`: `game_chat_reads.user_id`

### `game_chat_message_detections`

Moderation detection records for game messages. Sources: [model](../../backend/models/game_chat_message_detection_model.py), [canonical migration](../../backend/alembic/versions/0039_create_game_chat_message_detections_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `message_id` | `UUID` | No | — | FK → `chat_messages.id` |
| `category` | `VARCHAR(50)` | No | — | — |
| `severity` | `VARCHAR(20)` | No | — | — |
| `rule_key` | `VARCHAR(80)` | No | — | — |
| `matched_preview` | `VARCHAR(240)` | Yes | — | — |
| `scanner_id` | `VARCHAR(80)` | No | — | — |
| `scanner_version` | `VARCHAR(80)` | No | — | — |
| `taxonomy_version` | `VARCHAR(40)` | No | — | — |
| `configuration_hash` | `VARCHAR(64)` | No | — | — |
| `canonicalization_version` | `VARCHAR(80)` | No | — | — |
| `evidence_format_version` | `VARCHAR(40)` | No | — | — |
| `target_context` | `VARCHAR(60)` | No | — | — |
| `field_purpose` | `VARCHAR(40)` | No | — | — |
| `source_field` | `VARCHAR(80)` | No | — | — |
| `source_content_hash` | `VARCHAR(64)` | No | — | — |
| `matched_rule_versions` | `JSONB` | No | — | — |
| `declared_limits` | `JSONB` | No | — | — |
| `evidence_fingerprint` | `VARCHAR(64)` | No | — | — |
| `evidence` | `JSONB` | No | — | — |
| `scanned_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `detection_identity_hash` | `VARCHAR(64)` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `message_id` → `chat_messages.id` (ON DELETE CASCADE).
- **Unique constraints:** `uq_game_chat_message_detections_message_identity`: `message_id, detection_identity_hash`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `category`: `phone_number`, `email`, `link`, `off_platform_contact`, `payment_discussion`, `harassment_or_abuse`, `threat_or_safety`, `slur_or_hate`, `spam_or_repeated_message`.
- **CHECK constraints:**
  - `ck_game_chat_message_detections_category`: `category IN ('phone_number', 'email', 'link', 'off_platform_contact', 'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', 'slur_or_hate', 'spam_or_repeated_message')`
  - `ck_game_chat_message_detections_configuration_hash`: `configuration_hash ~ '^[0-9a-f]{64}$'`
  - `ck_game_chat_message_detections_declared_limits_nonempty`: `jsonb_typeof(declared_limits) = 'array' AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16`
  - `ck_game_chat_message_detections_evidence_fingerprint`: `evidence_fingerprint ~ '^[0-9a-f]{64}$'`
  - `ck_game_chat_message_detections_evidence_shape`: `jsonb_typeof(evidence) = 'object' AND jsonb_typeof(evidence->'evidence_kind') = 'string' AND COALESCE(evidence->>'evidence_kind', '') IN ('span', 'context_predicate')`
  - `ck_game_chat_message_detections_identity_hash`: `detection_identity_hash ~ '^[0-9a-f]{64}$'`
  - `ck_game_chat_message_detections_provenance_present`: `length(trim(scanner_id)) > 0 AND length(trim(scanner_version)) > 0 AND length(trim(taxonomy_version)) > 0 AND length(trim(canonicalization_version)) > 0 AND length(trim(evidence_format_version)) > 0 AND length(trim(target_context)) > 0 AND length(trim(field_purpose)) > 0 AND length(trim(source_field)) > 0`
  - `ck_game_chat_message_detections_rule_key_present`: `length(trim(rule_key)) > 0`
  - `ck_game_chat_message_detections_rule_versions_nonempty`: `jsonb_typeof(matched_rule_versions) = 'array' AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32`
  - `ck_game_chat_message_detections_severity`: `severity IN ('low', 'medium', 'high')`
  - `ck_game_chat_message_detections_source_hash`: `source_content_hash ~ '^[0-9a-f]{64}$'`
- **Indexes:**
  - `ix_game_chat_message_detections_category`: `game_chat_message_detections.category`
  - `ix_game_chat_message_detections_created_at`: `game_chat_message_detections.created_at`
  - `ix_game_chat_message_detections_message_id`: `game_chat_message_detections.message_id`

### `admin_target_notices`

Account-facing notices created by staff actions. Sources: [model](../../backend/models/admin_target_notice_model.py), [canonical migration](../../backend/alembic/versions/0028_create_admin_target_notices_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `recipient_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_sub_post_id` | `UUID` | Yes | — | FK → `sub_posts.id` |
| `target_sub_post_request_id` | `UUID` | Yes | — | FK → `sub_post_requests.id` |
| `admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `notice_type` | `VARCHAR(60)` | No | — | — |
| `notice_status` | `VARCHAR(20)` | No | server `'active'` | — |
| `title` | `VARCHAR(160)` | No | — | — |
| `body` | `TEXT` | No | — | — |
| `user_safe_reason` | `TEXT` | Yes | — | — |
| `notice_metadata` | `JSONB` | Yes | — | — |
| `created_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `read_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `dismissed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `created_by_user_id` → `users.id` (ON DELETE SET NULL); `recipient_user_id` → `users.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE CASCADE); `target_sub_post_id` → `sub_posts.id` (ON DELETE CASCADE); `target_sub_post_request_id` → `sub_post_requests.id` (ON DELETE CASCADE); `target_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `notice_type`: `community_game_hidden`, `community_game_restored`, `community_game_joining_paused`, `community_game_joining_resumed`, `community_game_payment_info_hidden`, `community_game_payment_info_restored`, `community_game_cancelled`, `need_sub_post_hidden`, `need_sub_post_restored`, `need_sub_post_removed`, `game_chat_message_removed`, `game_chat_message_restored`, `need_sub_chat_message_removed`, `need_sub_chat_message_restored`, `publish_fee_refunded`, `publish_credit_added`; `notice_status`: `active`, `dismissed`.
- **CHECK constraints:**
  - `ck_admin_target_notices_game_enforcement_target`: `notice_type NOT IN ('community_game_hidden', 'community_game_restored', 'community_game_joining_paused', 'community_game_joining_resumed', 'community_game_payment_info_hidden', 'community_game_payment_info_restored', 'community_game_cancelled', 'game_chat_message_removed', 'game_chat_message_restored') OR (target_game_id IS NOT NULL AND target_sub_post_id IS NULL AND target_sub_post_request_id IS NULL)`
  - `ck_admin_target_notices_notice_status`: `notice_status IN ('active', 'dismissed')`
  - `ck_admin_target_notices_notice_type`: `notice_type IN ('community_game_hidden', 'community_game_restored', 'community_game_joining_paused', 'community_game_joining_resumed', 'community_game_payment_info_hidden', 'community_game_payment_info_restored', 'community_game_cancelled', 'need_sub_post_hidden', 'need_sub_post_restored', 'need_sub_post_removed', 'game_chat_message_removed', 'game_chat_message_restored', 'need_sub_chat_message_removed', 'need_sub_chat_message_restored', 'publish_fee_refunded', 'publish_credit_added')`
  - `ck_admin_target_notices_sub_enforcement_target`: `notice_type NOT IN ('need_sub_post_hidden', 'need_sub_post_restored', 'need_sub_chat_message_removed', 'need_sub_chat_message_restored') OR (target_sub_post_id IS NOT NULL AND target_game_id IS NULL AND target_sub_post_request_id IS NULL)`
  - `ck_admin_target_notices_sub_removal_target`: `notice_type != 'need_sub_post_removed' OR (target_sub_post_id IS NOT NULL AND target_game_id IS NULL)`
  - `ck_admin_target_notices_target_required`: `target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_user_id IS NOT NULL`
- **Indexes:**
  - `ix_admin_target_notices_admin_action_id`: `admin_target_notices.admin_action_id`
  - `ix_admin_target_notices_created_at`: `admin_target_notices.created_at`
  - `ix_admin_target_notices_notice_type`: `admin_target_notices.notice_type`
  - `ix_admin_target_notices_recipient_user_id`: `admin_target_notices.recipient_user_id`
  - `ix_admin_target_notices_target_game_id`: `admin_target_notices.target_game_id`
  - `ix_admin_target_notices_target_sub_post_id`: `admin_target_notices.target_sub_post_id`
  - `ix_admin_target_notices_target_sub_post_request_id`: `admin_target_notices.target_sub_post_request_id`
  - `ix_admin_target_notices_target_user_id`: `admin_target_notices.target_user_id`

## Administration, moderation, and auditing

### `admin_actions`

Audit ledger of successful or attempted staff actions. Sources: [model](../../backend/models/admin_action_model.py), [canonical migration](../../backend/alembic/versions/0004_create_admin_actions_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `admin_user_id` | `UUID` | No | — | FK → `users.id` |
| `action_type` | `VARCHAR(60)` | No | — | — |
| `outcome` | `VARCHAR(20)` | No | — | — |
| `correlation_id` | `UUID` | No | — | — |
| `target_user_id` | `UUID` | Yes | — | — |
| `target_game_id` | `UUID` | Yes | — | — |
| `target_booking_id` | `UUID` | Yes | — | — |
| `target_participant_id` | `UUID` | Yes | — | — |
| `target_payment_id` | `UUID` | Yes | — | — |
| `target_payment_event_id` | `UUID` | Yes | — | — |
| `target_refund_id` | `UUID` | Yes | — | — |
| `target_game_credit_id` | `UUID` | Yes | — | — |
| `target_credit_usage_id` | `UUID` | Yes | — | — |
| `target_venue_id` | `UUID` | Yes | — | — |
| `target_venue_image_id` | `UUID` | Yes | — | — |
| `target_message_id` | `UUID` | Yes | — | — |
| `target_sub_post_id` | `UUID` | Yes | — | — |
| `target_sub_post_request_id` | `UUID` | Yes | — | — |
| `target_sub_post_position_id` | `UUID` | Yes | — | — |
| `target_sub_chat_message_id` | `UUID` | Yes | — | — |
| `target_notification_id` | `UUID` | Yes | — | — |
| `target_platform_notice_id` | `UUID` | Yes | — | — |
| `target_admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `target_support_flag_id` | `UUID` | Yes | — | — |
| `target_money_issue_id` | `UUID` | Yes | — | — |
| `target_review_case_id` | `UUID` | Yes | — | — |
| `target_financial_outcome_id` | `UUID` | Yes | — | — |
| `target_host_publish_fee_id` | `UUID` | Yes | — | — |
| `target_host_publish_entitlement_id` | `UUID` | Yes | — | — |
| `target_waitlist_entry_id` | `UUID` | Yes | — | — |
| `reason` | `TEXT` | Yes | — | — |
| `metadata` | `JSONB` | Yes | — | — |
| `idempotency_key` | `VARCHAR(160)` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `admin_user_id` → `users.id` (ON DELETE RESTRICT); `target_admin_action_id` → `admin_actions.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_actions`, `admin_financial_outcomes`, `admin_review_case_events`, `admin_target_notices`, `host_publish_entitlements`, `money_issue_events`, `refund_events`, `support_flags`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `action_type`: `cancel_game`, `refund_booking`, `create_refund`, `update_refund`, `mark_no_show`, `create_payment`, `update_payment`, `reverse_no_show`, `suspend_user`, `unsuspend_user`, `restrict_hosting`, `restore_hosting`, `approve_venue`, `delete_user`, `reject_venue`, `create_venue_image`, `update_venue_image`, `remove_venue_image`, `mark_chat_message_reviewed`, `remove_chat_message`, `restore_chat_message`, `update_game`, `create_game_chat`, `update_game_chat`, `update_booking`, `update_participant`, `issue_credit`, `reverse_credit`, `create_financial_outcome`, `apply_financial_outcome`, `resolve_manual_review`, `create_official_game`, `update_official_game`, `assign_official_host`, `remove_official_host`, `admin_add_player`, `admin_remove_player`, `waive_payment`, `remove_sub_post`, `hide_unsafe_community_payment_text`, `hide_need_sub_post`, `restore_need_sub_post`, `hide_community_game`, `restore_community_game`, `pause_community_game_joining`, `resume_community_game_joining`, `admin_cancel_community_game`, `restore_community_payment_text`, `create_notification`, `update_notification`, `publish_platform_notice`, `cancel_platform_notice`, `user_role_changed`, `append_audit_note`, `resolve_support_flag`, `resolve_money_issue`, `retry_money_issue_credit`, `reconcile_refund`, `create_review_case`, `close_review_case`, `add_review_case_note`, `read_game_chat_moderation`, `reveal_game_chat_message_content`, `read_need_sub_chat_moderation`, `reveal_need_sub_chat_message_content`, `read_review_case_sensitive_detail`, `read_admin_money_financial_outcome_detail`, `read_admin_money_user_detail`, `read_admin_money_issue_detail`, `read_admin_money_credit_detail`, `read_admin_money_payment_detail`, `read_admin_money_refund_detail`, `read_admin_money_refund_events`, `read_admin_money_issue_list_item`, `read_admin_money_credit_list_item`, `read_admin_money_payment_list_item`, `read_admin_money_refund_list_item`, `read_admin_official_game_money`, `read_admin_official_game_bookings`, `read_admin_official_game_waitlist`, `read_admin_official_game_cancel_preview`, `read_admin_official_game_remove_preview`, `read_admin_community_game_payment_detail`, `read_staff_payment_detail`, `read_staff_refund_detail`, `read_staff_payment_list_item`, `read_staff_refund_list_item`, `read_staff_game_credit_list_item`, `read_staff_booking_detail`, `read_staff_booking_list_item`, `read_staff_waitlist_entry_detail`, `read_staff_waitlist_entry_list_item`, `read_staff_host_publish_fee_detail`, `read_staff_host_publish_fee_list_item`, `read_staff_checkout_status`, `read_staff_hidden_community_payment_detail`, `read_staff_hidden_community_payment_list`, `create_community_game_detail`, `update_community_game_detail`, `delete_game`, `delete_venue`, `update_payment_event`; `outcome`: `succeeded`, `failed`, `pending`.
- **CHECK constraints:**
  - `ck_admin_actions_action_type`: `action_type IN ('cancel_game', 'refund_booking', 'create_refund', 'update_refund', 'mark_no_show', 'create_payment', 'update_payment', 'reverse_no_show', 'suspend_user', 'unsuspend_user', 'restrict_hosting', 'restore_hosting', 'approve_venue', 'delete_user', 'reject_venue', 'create_venue_image', 'update_venue_image', 'remove_venue_image', 'mark_chat_message_reviewed', 'remove_chat_message', 'restore_chat_message', 'update_game', 'create_game_chat', 'update_game_chat', 'update_booking', 'update_participant', 'issue_credit', 'reverse_credit', 'create_financial_outcome', 'apply_financial_outcome', 'resolve_manual_review', 'create_official_game', 'update_official_game', 'assign_official_host', 'remove_official_host', 'admin_add_player', 'admin_remove_player', 'waive_payment', 'remove_sub_post', 'hide_unsafe_community_payment_text', 'hide_need_sub_post', 'restore_need_sub_post', 'hide_community_game', 'restore_community_game', 'pause_community_game_joining', 'resume_community_game_joining', 'admin_cancel_community_game', 'restore_community_payment_text', 'create_notification', 'update_notification', 'publish_platform_notice', 'cancel_platform_notice', 'user_role_changed', 'append_audit_note', 'resolve_support_flag', 'resolve_money_issue', 'retry_money_issue_credit', 'reconcile_refund', 'create_review_case', 'close_review_case', 'add_review_case_note', 'read_game_chat_moderation', 'reveal_game_chat_message_content', 'read_need_sub_chat_moderation', 'reveal_need_sub_chat_message_content', 'read_review_case_sensitive_detail', 'read_admin_money_financial_outcome_detail', 'read_admin_money_user_detail', 'read_admin_money_issue_detail', 'read_admin_money_credit_detail', 'read_admin_money_payment_detail', 'read_admin_money_refund_detail', 'read_admin_money_refund_events', 'read_admin_money_issue_list_item', 'read_admin_money_credit_list_item', 'read_admin_money_payment_list_item', 'read_admin_money_refund_list_item', 'read_admin_official_game_money', 'read_admin_official_game_bookings', 'read_admin_official_game_waitlist', 'read_admin_official_game_cancel_preview', 'read_admin_official_game_remove_preview', 'read_admin_community_game_payment_detail', 'read_staff_payment_detail', 'read_staff_refund_detail', 'read_staff_payment_list_item', 'read_staff_refund_list_item', 'read_staff_game_credit_list_item', 'read_staff_booking_detail', 'read_staff_booking_list_item', 'read_staff_waitlist_entry_detail', 'read_staff_waitlist_entry_list_item', 'read_staff_host_publish_fee_detail', 'read_staff_host_publish_fee_list_item', 'read_staff_checkout_status', 'read_staff_hidden_community_payment_detail', 'read_staff_hidden_community_payment_list', 'create_community_game_detail', 'update_community_game_detail', 'delete_game', 'delete_venue', 'update_payment_event')`
  - `ck_admin_actions_outcome`: `outcome IN ('succeeded', 'failed', 'pending')`
  - `ck_admin_actions_target_required`: `target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_booking_id IS NOT NULL OR target_participant_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_payment_event_id IS NOT NULL OR target_refund_id IS NOT NULL OR target_game_credit_id IS NOT NULL OR target_credit_usage_id IS NOT NULL OR target_venue_id IS NOT NULL OR target_venue_image_id IS NOT NULL OR target_message_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_sub_post_position_id IS NOT NULL OR target_sub_chat_message_id IS NOT NULL OR target_notification_id IS NOT NULL OR target_platform_notice_id IS NOT NULL OR target_admin_action_id IS NOT NULL OR target_support_flag_id IS NOT NULL OR target_money_issue_id IS NOT NULL OR target_review_case_id IS NOT NULL OR target_financial_outcome_id IS NOT NULL OR target_host_publish_fee_id IS NOT NULL OR target_host_publish_entitlement_id IS NOT NULL OR target_waitlist_entry_id IS NOT NULL`
- **Indexes:**
  - `ix_admin_actions_action_type`: `admin_actions.action_type`
  - `ix_admin_actions_admin_user_id`: `admin_actions.admin_user_id`
  - `ix_admin_actions_correlation_id`: `admin_actions.correlation_id`
  - `ix_admin_actions_idempotency_key`: `admin_actions.idempotency_key`
  - `ix_admin_actions_log_action_created_id`: `admin_actions.action_type, created_at DESC, id DESC`
  - `ix_admin_actions_log_admin_action_created_id`: `admin_actions.admin_user_id, admin_actions.action_type, created_at DESC, id DESC`
  - `ix_admin_actions_log_admin_created_id`: `admin_actions.admin_user_id, created_at DESC, id DESC`
  - `ix_admin_actions_log_created_id`: `created_at DESC, id DESC`
  - `ix_admin_actions_target_admin_action_id`: `admin_actions.target_admin_action_id`
  - `ix_admin_actions_target_booking_id`: `admin_actions.target_booking_id`
  - `ix_admin_actions_target_credit_usage_id`: `admin_actions.target_credit_usage_id`
  - `ix_admin_actions_target_financial_outcome_id`: `admin_actions.target_financial_outcome_id`
  - `ix_admin_actions_target_game_credit_id`: `admin_actions.target_game_credit_id`
  - `ix_admin_actions_target_game_id`: `admin_actions.target_game_id`
  - `ix_admin_actions_target_host_publish_entitlement_id`: `admin_actions.target_host_publish_entitlement_id`
  - `ix_admin_actions_target_host_publish_fee_id`: `admin_actions.target_host_publish_fee_id`
  - `ix_admin_actions_target_message_id`: `admin_actions.target_message_id`
  - `ix_admin_actions_target_money_issue_id`: `admin_actions.target_money_issue_id`
  - `ix_admin_actions_target_notification_id`: `admin_actions.target_notification_id`
  - `ix_admin_actions_target_participant_id`: `admin_actions.target_participant_id`
  - `ix_admin_actions_target_payment_event_id`: `admin_actions.target_payment_event_id`
  - `ix_admin_actions_target_payment_id`: `admin_actions.target_payment_id`
  - `ix_admin_actions_target_platform_notice_id`: `admin_actions.target_platform_notice_id`
  - `ix_admin_actions_target_refund_id`: `admin_actions.target_refund_id`
  - `ix_admin_actions_target_review_case_id`: `admin_actions.target_review_case_id`
  - `ix_admin_actions_target_sub_chat_message_id`: `admin_actions.target_sub_chat_message_id`
  - `ix_admin_actions_target_sub_post_id`: `admin_actions.target_sub_post_id`
  - `ix_admin_actions_target_sub_post_position_id`: `admin_actions.target_sub_post_position_id`
  - `ix_admin_actions_target_sub_post_request_id`: `admin_actions.target_sub_post_request_id`
  - `ix_admin_actions_target_support_flag_id`: `admin_actions.target_support_flag_id`
  - `ix_admin_actions_target_user_id`: `admin_actions.target_user_id`
  - `ix_admin_actions_target_venue_id`: `admin_actions.target_venue_id`
  - `ix_admin_actions_target_venue_image_id`: `admin_actions.target_venue_image_id`
  - `ix_admin_actions_target_waitlist_entry_id`: `admin_actions.target_waitlist_entry_id`
  - `uq_admin_actions_audit_note_idempotency`: `admin_actions.admin_user_id, admin_actions.target_admin_action_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'append_audit_note' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_community_game_enforcement_idempotency`: `admin_actions.admin_user_id, admin_actions.target_game_id, admin_actions.action_type, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type IN ('hide_community_game', 'restore_community_game', 'pause_community_game_joining', 'resume_community_game_joining', 'admin_cancel_community_game', 'restore_community_payment_text') AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_create_financial_outcome_idempotency`: `admin_actions.admin_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'create_financial_outcome' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_delete_user_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'delete_user' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_hide_unsafe_community_payment_text_idempotency`: `admin_actions.admin_user_id, admin_actions.target_game_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'hide_unsafe_community_payment_text' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_mark_reviewed_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'mark_chat_message_reviewed' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_mark_reviewed_sub_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_sub_chat_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'mark_chat_message_reviewed' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_money_issue_idempotency`: `admin_actions.admin_user_id, admin_actions.target_money_issue_id, admin_actions.action_type, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type IN ('resolve_money_issue', 'retry_money_issue_credit') AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_need_sub_enforcement_idempotency`: `admin_actions.admin_user_id, admin_actions.target_sub_post_id, admin_actions.action_type, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type IN ('hide_need_sub_post', 'restore_need_sub_post') AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_reconcile_refund_idempotency`: `admin_actions.admin_user_id, admin_actions.target_refund_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'reconcile_refund' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_remove_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'remove_chat_message' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_remove_sub_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_sub_chat_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'remove_chat_message' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_remove_sub_post_idempotency`: `admin_actions.admin_user_id, admin_actions.target_sub_post_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'remove_sub_post' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_resolve_manual_review_idempotency`: `admin_actions.admin_user_id, admin_actions.target_financial_outcome_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'resolve_manual_review' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_restore_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'restore_chat_message' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_restore_hosting_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'restore_hosting' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_restore_sub_chat_message_idempotency`: `admin_actions.admin_user_id, admin_actions.target_sub_chat_message_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'restore_chat_message' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_restrict_hosting_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'restrict_hosting' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_review_case_idempotency`: `admin_actions.admin_user_id, admin_actions.target_review_case_id, admin_actions.action_type, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type IN ('create_review_case', 'close_review_case', 'add_review_case_note') AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_suspend_user_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'suspend_user' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_unsuspend_user_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'unsuspend_user' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_update_refund_idempotency`: `admin_actions.admin_user_id, admin_actions.target_refund_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'update_refund' AND idempotency_key IS NOT NULL`)
  - `uq_admin_actions_user_role_changed_idempotency`: `admin_actions.admin_user_id, admin_actions.target_user_id, admin_actions.idempotency_key` (`UNIQUE`; `WHERE action_type = 'user_role_changed' AND idempotency_key IS NOT NULL`)

### `admin_rejected_attempts`

Immutable records of rejected privileged actions. Sources: [model](../../backend/models/admin_rejected_attempt_model.py), [canonical migration](../../backend/alembic/versions/0045_create_admin_rejected_attempts_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `admin_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `attempt_type` | `VARCHAR(80)` | No | — | — |
| `rejection_mode` | `VARCHAR(40)` | No | — | — |
| `response_status_code` | `INTEGER` | No | — | — |
| `route_method` | `VARCHAR(10)` | No | — | — |
| `route_path` | `VARCHAR(240)` | No | — | — |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_credit_id` | `UUID` | Yes | — | FK → `game_credits.id` |
| `metadata` | `JSONB` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `admin_user_id` → `users.id` (ON DELETE SET NULL); `target_game_credit_id` → `game_credits.id` (ON DELETE SET NULL); `target_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `attempt_type`: `issue_credit_rejected`, `reverse_credit_rejected`, `suspend_user_rejected`, `delete_user_rejected`; `rejection_mode`: `domain_rejected_postload`.
- **CHECK constraints:**
  - `ck_admin_rejected_attempts_attempt_type`: `attempt_type IN ('issue_credit_rejected', 'reverse_credit_rejected', 'suspend_user_rejected', 'delete_user_rejected')`
  - `ck_admin_rejected_attempts_rejection_mode`: `rejection_mode IN ('domain_rejected_postload')`
  - `ck_admin_rejected_attempts_response_status_code`: `response_status_code BETWEEN 400 AND 599`
- **Indexes:**
  - `ix_admin_rejected_attempts_admin_user_id`: `admin_rejected_attempts.admin_user_id`
  - `ix_admin_rejected_attempts_attempt_type`: `admin_rejected_attempts.attempt_type`
  - `ix_admin_rejected_attempts_created_at`: `admin_rejected_attempts.created_at`
  - `ix_admin_rejected_attempts_rejection_mode`: `admin_rejected_attempts.rejection_mode`
  - `ix_admin_rejected_attempts_target_game_credit_id`: `admin_rejected_attempts.target_game_credit_id`
  - `ix_admin_rejected_attempts_target_user_id`: `admin_rejected_attempts.target_user_id`

### `admin_review_cases`

Staff review cases for flagged content or conduct. Sources: [model](../../backend/models/admin_review_case_model.py), [canonical migration](../../backend/alembic/versions/0053_create_admin_review_cases_table.py#L40).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `case_type` | `VARCHAR(40)` | No | — | — |
| `case_status` | `VARCHAR(30)` | No | server `'open'` | — |
| `case_category` | `VARCHAR(60)` | No | — | — |
| `case_version` | `INTEGER` | No | server `1`; client `1` | — |
| `priority` | `VARCHAR(30)` | No | server `'attention'` | — |
| `title` | `VARCHAR(180)` | No | — | — |
| `summary` | `TEXT` | No | — | — |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_sub_post_id` | `UUID` | Yes | — | FK → `sub_posts.id` |
| `target_sub_post_request_id` | `UUID` | Yes | — | FK → `sub_post_requests.id` |
| `target_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `target_financial_outcome_id` | `UUID` | Yes | — | FK → `admin_financial_outcomes.id` |
| `opened_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `closed_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `closure_outcome` | `VARCHAR(60)` | Yes | — | — |
| `closure_reason` | `TEXT` | Yes | — | — |
| `closed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `closed_by_user_id` → `users.id` (ON DELETE SET NULL); `opened_by_user_id` → `users.id` (ON DELETE SET NULL); `target_financial_outcome_id` → `admin_financial_outcomes.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE RESTRICT); `target_payment_id` → `payments.id` (ON DELETE SET NULL); `target_sub_post_id` → `sub_posts.id` (ON DELETE RESTRICT); `target_sub_post_request_id` → `sub_post_requests.id` (ON DELETE SET NULL); `target_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_content_moderation_findings`, `admin_review_case_events`, `admin_review_case_notes`, `admin_review_signals`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `case_type`: `community_game`, `need_a_sub`, `money`, `user`, `system`; `case_status`: `open`, `closed`; `case_category`: `content_moderation`, `chat_moderation`; `closure_outcome`: `enforcement_applied`, `no_action_needed`, `invalid_signal`.
- **CHECK constraints:**
  - `ck_admin_review_cases_case_category`: `case_category IN ('content_moderation', 'chat_moderation')`
  - `ck_admin_review_cases_case_status`: `case_status IN ('open', 'closed')`
  - `ck_admin_review_cases_case_type`: `case_type IN ('community_game', 'need_a_sub', 'money', 'user', 'system')`
  - `ck_admin_review_cases_case_version_positive`: `case_version > 0`
  - `ck_admin_review_cases_closure_outcome`: `closure_outcome IS NULL OR closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal')`
  - `ck_admin_review_cases_closure_state`: `(case_status = 'open' AND closed_by_user_id IS NULL AND closure_outcome IS NULL AND closure_reason IS NULL AND closed_at IS NULL) OR (case_status = 'closed' AND closure_outcome IS NOT NULL AND closure_reason IS NOT NULL AND closed_at IS NOT NULL)`
  - `ck_admin_review_cases_priority`: `priority IN ('attention', 'urgent', 'critical')`
  - `ck_admin_review_cases_target_shape`: `(case_type = 'community_game' AND target_game_id IS NOT NULL AND target_user_id IS NULL AND target_sub_post_id IS NULL AND target_sub_post_request_id IS NULL AND target_payment_id IS NULL AND target_financial_outcome_id IS NULL) OR (case_type = 'need_a_sub' AND target_sub_post_id IS NOT NULL AND target_user_id IS NULL AND target_game_id IS NULL AND target_sub_post_request_id IS NULL AND target_payment_id IS NULL AND target_financial_outcome_id IS NULL) OR (case_type NOT IN ('community_game', 'need_a_sub') AND (target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_financial_outcome_id IS NOT NULL))`
- **Indexes:**
  - `ix_admin_review_cases_case_category`: `admin_review_cases.case_category`
  - `ix_admin_review_cases_case_status`: `admin_review_cases.case_status`
  - `ix_admin_review_cases_case_type`: `admin_review_cases.case_type`
  - `ix_admin_review_cases_closed_at`: `admin_review_cases.closed_at`
  - `ix_admin_review_cases_created_at`: `admin_review_cases.created_at`
  - `ix_admin_review_cases_priority`: `admin_review_cases.priority`
  - `ix_admin_review_cases_status_updated_id`: `admin_review_cases.case_status, admin_review_cases.updated_at, admin_review_cases.id`
  - `ix_admin_review_cases_target_financial_outcome_id`: `admin_review_cases.target_financial_outcome_id`
  - `ix_admin_review_cases_target_game_id`: `admin_review_cases.target_game_id`
  - `ix_admin_review_cases_target_payment_id`: `admin_review_cases.target_payment_id`
  - `ix_admin_review_cases_target_sub_post_id`: `admin_review_cases.target_sub_post_id`
  - `ix_admin_review_cases_target_sub_post_request_id`: `admin_review_cases.target_sub_post_request_id`
  - `ix_admin_review_cases_target_user_id`: `admin_review_cases.target_user_id`
  - `uq_admin_review_cases_open_community_game_moderation`: `admin_review_cases.target_game_id, admin_review_cases.case_category` (`UNIQUE`; `WHERE target_game_id IS NOT NULL AND case_type = 'community_game' AND case_category IN ('content_moderation', 'chat_moderation') AND case_status = 'open'`)
  - `uq_admin_review_cases_open_need_sub_moderation`: `admin_review_cases.target_sub_post_id, admin_review_cases.case_category` (`UNIQUE`; `WHERE target_sub_post_id IS NOT NULL AND case_type = 'need_a_sub' AND case_category IN ('content_moderation', 'chat_moderation') AND case_status = 'open'`)

### `admin_review_case_events`

Review-case timeline events. Sources: [model](../../backend/models/admin_review_case_event_model.py), [canonical migration](../../backend/alembic/versions/0059_create_admin_review_case_events_table.py#L31).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `review_case_id` | `UUID` | No | — | FK → `admin_review_cases.id` |
| `case_version` | `INTEGER` | No | — | — |
| `event_type` | `VARCHAR(60)` | No | — | — |
| `actor_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `signal_id` | `UUID` | Yes | — | FK → `admin_review_signals.id` |
| `content_moderation_finding_id` | `UUID` | Yes | — | FK → `admin_content_moderation_findings.id` |
| `note_id` | `UUID` | Yes | — | FK → `admin_review_case_notes.id` |
| `event_metadata` | `JSONB` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `actor_user_id` → `users.id` (ON DELETE RESTRICT); `admin_action_id` → `admin_actions.id` (ON DELETE RESTRICT); `content_moderation_finding_id` → `admin_content_moderation_findings.id` (ON DELETE RESTRICT); `note_id` → `admin_review_case_notes.id` (ON DELETE RESTRICT); `review_case_id` → `admin_review_cases.id` (ON DELETE RESTRICT); `signal_id` → `admin_review_signals.id` (ON DELETE RESTRICT).
- **Unique constraints:** `uq_admin_review_case_events_case_version`: `review_case_id, case_version`.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `event_type`: `case_created`, `signal_attached`, `signal_superseded`, `signal_reactivated`, `finding_attached`, `finding_cleared`, `note_added`, `enforcement_action_linked`, `closed`.
- **CHECK constraints:**
  - `ck_admin_review_case_events_case_version_positive`: `case_version > 0`
  - `ck_admin_review_case_events_event_type`: `event_type IN ('case_created', 'signal_attached', 'signal_superseded', 'signal_reactivated', 'finding_attached', 'finding_cleared', 'note_added', 'enforcement_action_linked', 'closed')`
  - `ck_admin_review_case_events_metadata_scope`: `event_type = 'closed' OR event_metadata IS NULL`
  - `ck_admin_review_case_events_reference_shape`: `(event_type = 'case_created' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type IN ('signal_attached', 'signal_superseded', 'signal_reactivated') AND signal_id IS NOT NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type IN ('finding_attached', 'finding_cleared') AND signal_id IS NULL AND content_moderation_finding_id IS NOT NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type = 'note_added' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NOT NULL AND admin_action_id IS NOT NULL) OR (event_type = 'enforcement_action_linked' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NOT NULL) OR (event_type = 'closed' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL)`
- **Indexes:**
  - `ix_admin_review_case_events_actor_user_id`: `admin_review_case_events.actor_user_id`
  - `ix_admin_review_case_events_admin_action_id`: `admin_review_case_events.admin_action_id`
  - `ix_admin_review_case_events_content_moderation_finding_id`: `admin_review_case_events.content_moderation_finding_id`
  - `ix_admin_review_case_events_created_at`: `admin_review_case_events.created_at`
  - `ix_admin_review_case_events_event_type`: `admin_review_case_events.event_type`
  - `ix_admin_review_case_events_note_id`: `admin_review_case_events.note_id`
  - `ix_admin_review_case_events_review_case_id`: `admin_review_case_events.review_case_id`
  - `ix_admin_review_case_events_signal_id`: `admin_review_case_events.signal_id`

### `admin_review_case_notes`

Staff notes attached to review cases. Sources: [model](../../backend/models/admin_review_case_note_model.py), [canonical migration](../../backend/alembic/versions/0057_create_admin_review_case_notes_table.py#L31).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `review_case_id` | `UUID` | No | — | FK → `admin_review_cases.id` |
| `author_user_id` | `UUID` | No | — | FK → `users.id` |
| `body` | `TEXT` | No | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `author_user_id` → `users.id` (ON DELETE RESTRICT); `review_case_id` → `admin_review_cases.id` (ON DELETE RESTRICT).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_review_case_events`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** No status, outcome, type, kind, role, mode, category, or visibility column.
- **CHECK constraints:** None.
- **Indexes:**
  - `ix_admin_review_case_notes_author_user_id`: `admin_review_case_notes.author_user_id`
  - `ix_admin_review_case_notes_created_at`: `admin_review_case_notes.created_at`
  - `ix_admin_review_case_notes_review_case_id`: `admin_review_case_notes.review_case_id`

### `admin_review_signals`

Signals that create or relate to review cases. Sources: [model](../../backend/models/admin_review_signal_model.py), [canonical migration](../../backend/alembic/versions/0058_create_admin_review_signals_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `review_case_id` | `UUID` | Yes | — | FK → `admin_review_cases.id` |
| `signal_category` | `VARCHAR(60)` | No | — | — |
| `source` | `VARCHAR(60)` | No | — | — |
| `signal_status` | `VARCHAR(30)` | No | server `'open'` | — |
| `priority` | `VARCHAR(30)` | No | server `'attention'` | — |
| `title` | `VARCHAR(180)` | No | — | — |
| `summary` | `TEXT` | No | — | — |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_sub_post_id` | `UUID` | Yes | — | FK → `sub_posts.id` |
| `target_sub_post_request_id` | `UUID` | Yes | — | FK → `sub_post_requests.id` |
| `target_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `target_financial_outcome_id` | `UUID` | Yes | — | FK → `admin_financial_outcomes.id` |
| `metadata` | `JSONB` | Yes | — | — |
| `idempotency_key` | `VARCHAR(160)` | Yes | — | — |
| `created_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `created_by_user_id` → `users.id` (ON DELETE SET NULL); `review_case_id` → `admin_review_cases.id` (ON DELETE SET NULL); `target_financial_outcome_id` → `admin_financial_outcomes.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE SET NULL); `target_payment_id` → `payments.id` (ON DELETE SET NULL); `target_sub_post_id` → `sub_posts.id` (ON DELETE SET NULL); `target_sub_post_request_id` → `sub_post_requests.id` (ON DELETE SET NULL); `target_user_id` → `users.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_review_case_events`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `signal_category`: `chat_moderation`; `signal_status`: `open`, `attached`, `dismissed`.
- **CHECK constraints:**
  - `ck_admin_review_signals_priority`: `priority IN ('attention', 'urgent', 'critical')`
  - `ck_admin_review_signals_signal_category`: `signal_category IN ('chat_moderation')`
  - `ck_admin_review_signals_signal_status`: `signal_status IN ('open', 'attached', 'dismissed')`
  - `ck_admin_review_signals_source`: `source IN ('chat_moderation')`
- **Indexes:**
  - `ix_admin_review_signals_created_at`: `admin_review_signals.created_at`
  - `ix_admin_review_signals_priority`: `admin_review_signals.priority`
  - `ix_admin_review_signals_review_case_id`: `admin_review_signals.review_case_id`
  - `ix_admin_review_signals_signal_category`: `admin_review_signals.signal_category`
  - `ix_admin_review_signals_signal_status`: `admin_review_signals.signal_status`
  - `ix_admin_review_signals_target_financial_outcome_id`: `admin_review_signals.target_financial_outcome_id`
  - `ix_admin_review_signals_target_game_id`: `admin_review_signals.target_game_id`
  - `ix_admin_review_signals_target_payment_id`: `admin_review_signals.target_payment_id`
  - `ix_admin_review_signals_target_sub_post_id`: `admin_review_signals.target_sub_post_id`
  - `ix_admin_review_signals_target_sub_post_request_id`: `admin_review_signals.target_sub_post_request_id`
  - `ix_admin_review_signals_target_user_id`: `admin_review_signals.target_user_id`
  - `uq_admin_review_signals_source_idempotency_key`: `admin_review_signals.source, admin_review_signals.idempotency_key` (`UNIQUE`; `WHERE idempotency_key IS NOT NULL`)

### `admin_content_moderation_findings`

Recorded moderation findings and enforcement context. Sources: [model](../../backend/models/admin_content_moderation_finding_model.py), [canonical migration](../../backend/alembic/versions/0056_create_admin_content_moderation_findings_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `review_case_id` | `UUID` | No | — | FK → `admin_review_cases.id` |
| `risk_area` | `VARCHAR(60)` | No | — | — |
| `finding_type` | `VARCHAR(60)` | No | — | — |
| `priority` | `VARCHAR(30)` | No | server `'attention'` | — |
| `source_field` | `VARCHAR(80)` | No | — | — |
| `source_content_hash` | `VARCHAR(64)` | No | — | — |
| `evidence_fingerprint` | `VARCHAR(64)` | No | — | — |
| `evidence` | `JSONB` | No | — | — |
| `scanner_id` | `VARCHAR(80)` | No | — | — |
| `taxonomy_version` | `VARCHAR(40)` | No | — | — |
| `configuration_hash` | `VARCHAR(64)` | No | — | — |
| `canonicalization_version` | `VARCHAR(80)` | No | — | — |
| `evidence_format_version` | `VARCHAR(40)` | No | — | — |
| `target_context` | `VARCHAR(60)` | No | — | — |
| `field_purpose` | `VARCHAR(40)` | No | — | — |
| `matched_rule_versions` | `JSONB` | No | — | — |
| `declared_limits` | `JSONB` | No | — | — |
| `scanned_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `finding_identity_hash` | `VARCHAR(64)` | No | — | — |
| `current_match` | `BOOLEAN` | No | server `true` | — |
| `first_detected_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `last_detected_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — |
| `cleared_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `scanner_version` | `VARCHAR(80)` | No | — | — |
| `metadata` | `JSONB` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `review_case_id` → `admin_review_cases.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by `admin_review_case_events`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `finding_type`: `off_app_contact`, `payment_pressure`, `spam_or_scam`, `threat_or_violence`, `harassment_or_abuse`, `slur_or_hate`, `sexual_or_explicit`.
- **CHECK constraints:**
  - `ck_admin_content_moderation_findings_configuration_hash`: `configuration_hash ~ '^[0-9a-f]{64}$'`
  - `ck_admin_content_moderation_findings_current_clear_state`: `(current_match = true AND cleared_at IS NULL) OR (current_match = false AND cleared_at IS NOT NULL)`
  - `ck_admin_content_moderation_findings_declared_limits_nonempty`: `jsonb_typeof(declared_limits) = 'array' AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16`
  - `ck_admin_content_moderation_findings_detected_order`: `first_detected_at <= last_detected_at`
  - `ck_admin_content_moderation_findings_evidence_nonempty`: `jsonb_typeof(evidence) = 'array' AND jsonb_array_length(evidence) BETWEEN 1 AND 8`
  - `ck_admin_content_moderation_findings_finding_type`: `finding_type IN ('off_app_contact', 'payment_pressure', 'spam_or_scam', 'threat_or_violence', 'harassment_or_abuse', 'slur_or_hate', 'sexual_or_explicit')`
  - `ck_admin_content_moderation_findings_fingerprint_present`: `evidence_fingerprint ~ '^[0-9a-f]{64}$'`
  - `ck_admin_content_moderation_findings_identity_hash`: `finding_identity_hash ~ '^[0-9a-f]{64}$'`
  - `ck_admin_content_moderation_findings_priority`: `priority IN ('attention', 'urgent', 'critical')`
  - `ck_admin_content_moderation_findings_provenance_present`: `length(trim(scanner_id)) > 0 AND length(trim(scanner_version)) > 0 AND length(trim(taxonomy_version)) > 0 AND length(trim(canonicalization_version)) > 0 AND length(trim(evidence_format_version)) > 0 AND length(trim(target_context)) > 0 AND length(trim(field_purpose)) > 0`
  - `ck_admin_content_moderation_findings_risk_area`: `risk_area IN ('unsafe_post_text', 'unsafe_payment_text')`
  - `ck_admin_content_moderation_findings_rule_versions_nonempty`: `jsonb_typeof(matched_rule_versions) = 'array' AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32`
  - `ck_admin_content_moderation_findings_source_field_present`: `length(trim(source_field)) > 0`
  - `ck_admin_content_moderation_findings_source_hash_present`: `source_content_hash ~ '^[0-9a-f]{64}$'`
- **Indexes:**
  - `ix_admin_content_moderation_findings_case_current_type`: `admin_content_moderation_findings.review_case_id, admin_content_moderation_findings.current_match, admin_content_moderation_findings.finding_type`
  - `ix_admin_content_moderation_findings_current_match`: `admin_content_moderation_findings.current_match`
  - `ix_admin_content_moderation_findings_finding_type`: `admin_content_moderation_findings.finding_type`
  - `ix_admin_content_moderation_findings_review_case_id`: `admin_content_moderation_findings.review_case_id`
  - `uq_admin_content_moderation_findings_current_identity`: `admin_content_moderation_findings.review_case_id, admin_content_moderation_findings.finding_identity_hash` (`UNIQUE`; `WHERE current_match = true`)

### `support_flags`

Support exceptions and resolution state. Sources: [model](../../backend/models/support_flag_model.py), [canonical migration](../../backend/alembic/versions/0055_create_support_flags_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `flag_type` | `VARCHAR(80)` | No | — | — |
| `flag_status` | `VARCHAR(30)` | No | server `'open'` | — |
| `severity` | `VARCHAR(30)` | No | server `'attention'` | — |
| `source` | `VARCHAR(40)` | No | — | — |
| `title` | `VARCHAR(180)` | No | — | — |
| `summary` | `TEXT` | No | — | — |
| `target_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `target_game_id` | `UUID` | Yes | — | FK → `games.id` |
| `target_booking_id` | `UUID` | Yes | — | FK → `bookings.id` |
| `target_payment_id` | `UUID` | Yes | — | FK → `payments.id` |
| `target_refund_id` | `UUID` | Yes | — | FK → `refunds.id` |
| `target_game_credit_id` | `UUID` | Yes | — | FK → `game_credits.id` |
| `target_venue_id` | `UUID` | Yes | — | FK → `venues.id` |
| `target_venue_image_id` | `UUID` | Yes | — | FK → `venue_images.id` |
| `target_notification_id` | `UUID` | Yes | — | FK → `notifications.id` |
| `metadata` | `JSONB` | Yes | — | — |
| `idempotency_key` | `VARCHAR(160)` | Yes | — | — |
| `source_admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `created_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `resolved_by_user_id` | `UUID` | Yes | — | FK → `users.id` |
| `resolution_outcome` | `VARCHAR(60)` | Yes | — | — |
| `resolution_reason` | `TEXT` | Yes | — | — |
| `resolution_admin_action_id` | `UUID` | Yes | — | FK → `admin_actions.id` |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `created_by_user_id` → `users.id` (ON DELETE SET NULL); `resolution_admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `resolved_by_user_id` → `users.id` (ON DELETE SET NULL); `source_admin_action_id` → `admin_actions.id` (ON DELETE SET NULL); `target_booking_id` → `bookings.id` (ON DELETE SET NULL); `target_game_credit_id` → `game_credits.id` (ON DELETE SET NULL); `target_game_id` → `games.id` (ON DELETE SET NULL); `target_notification_id` → `notifications.id` (ON DELETE SET NULL); `target_payment_id` → `payments.id` (ON DELETE SET NULL); `target_refund_id` → `refunds.id` (ON DELETE SET NULL); `target_user_id` → `users.id` (ON DELETE SET NULL); `target_venue_id` → `venues.id` (ON DELETE SET NULL); `target_venue_image_id` → `venue_images.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `flag_type`: `venue_image_upload_failed`, `venue_image_readiness_failed`, `account_delete_partial_failure`, `community_game_review_required`; `flag_status`: `open`, `resolved`; `resolution_outcome`: `handled_externally`, `retried_successfully`, `no_action_needed`, `duplicate`, `invalid_flag`.
- **CHECK constraints:**
  - `ck_support_flags_flag_status`: `flag_status IN ('open', 'resolved')`
  - `ck_support_flags_flag_type`: `flag_type IN ('venue_image_upload_failed', 'venue_image_readiness_failed', 'account_delete_partial_failure', 'community_game_review_required')`
  - `ck_support_flags_resolution_outcome`: `resolution_outcome IS NULL OR resolution_outcome IN ('handled_externally', 'retried_successfully', 'no_action_needed', 'duplicate', 'invalid_flag')`
  - `ck_support_flags_resolution_state`: `(flag_status = 'open' AND resolved_at IS NULL AND resolved_by_user_id IS NULL AND resolution_outcome IS NULL AND resolution_reason IS NULL) OR (flag_status = 'resolved' AND resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_outcome IS NOT NULL AND resolution_reason IS NOT NULL)`
  - `ck_support_flags_severity`: `severity IN ('attention', 'urgent', 'critical')`
  - `ck_support_flags_source`: `source IN ('system', 'admin', 'stripe', 'venue_image', 'account', 'official_game')`
  - `ck_support_flags_target_required`: `target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_booking_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_refund_id IS NOT NULL OR target_game_credit_id IS NOT NULL OR target_venue_id IS NOT NULL OR target_venue_image_id IS NOT NULL OR target_notification_id IS NOT NULL`
- **Indexes:**
  - `ix_support_flags_created_at`: `support_flags.created_at`
  - `ix_support_flags_flag_status`: `support_flags.flag_status`
  - `ix_support_flags_flag_type`: `support_flags.flag_type`
  - `ix_support_flags_resolution_admin_action_id`: `support_flags.resolution_admin_action_id`
  - `ix_support_flags_resolved_at`: `support_flags.resolved_at`
  - `ix_support_flags_source_admin_action_id`: `support_flags.source_admin_action_id`
  - `ix_support_flags_target_booking_id`: `support_flags.target_booking_id`
  - `ix_support_flags_target_game_credit_id`: `support_flags.target_game_credit_id`
  - `ix_support_flags_target_game_id`: `support_flags.target_game_id`
  - `ix_support_flags_target_notification_id`: `support_flags.target_notification_id`
  - `ix_support_flags_target_payment_id`: `support_flags.target_payment_id`
  - `ix_support_flags_target_refund_id`: `support_flags.target_refund_id`
  - `ix_support_flags_target_user_id`: `support_flags.target_user_id`
  - `ix_support_flags_target_venue_id`: `support_flags.target_venue_id`
  - `ix_support_flags_target_venue_image_id`: `support_flags.target_venue_image_id`
  - `uq_support_flags_flag_type_idempotency_key`: `support_flags.flag_type, support_flags.idempotency_key` (`UNIQUE`; `WHERE idempotency_key IS NOT NULL`)

## Durable jobs and worker operations

### `durable_jobs`

Persisted background work queue. Sources: [model](../../backend/models/durable_job_model.py), [canonical migration](../../backend/alembic/versions/0060_create_durable_jobs_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `job_type` | `VARCHAR(100)` | No | — | — |
| `payload_version` | `INTEGER` | No | — | — |
| `payload` | `JSONB` | No | server `'{}'::jsonb` | — |
| `protected_identity` | `JSONB` | No | server `'{}'::jsonb` | — |
| `priority` | `INTEGER` | No | server `0` | — |
| `available_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `status` | `VARCHAR(20)` | No | server `'pending'` | — |
| `attempt_count` | `INTEGER` | No | server `0` | — |
| `maximum_attempts` | `INTEGER` | No | — | — |
| `lease_token` | `UUID` | Yes | — | — |
| `lease_owner` | `VARCHAR(120)` | Yes | — | — |
| `lease_expires_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `heartbeat_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `correlation_id` | `VARCHAR(120)` | No | — | — |
| `origin_reference_type` | `VARCHAR(80)` | Yes | — | — |
| `origin_reference_id` | `VARCHAR(120)` | Yes | — | — |
| `idempotency_key` | `VARCHAR(255)` | No | — | — |
| `last_error_code` | `VARCHAR(80)` | Yes | — | — |
| `result_metadata` | `JSONB` | No | server `'{}'::jsonb` | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `exhausted_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** None.
- **Unique constraints:** `uq_durable_jobs_idempotency_key`: `idempotency_key`.
- **Other table relationships:** Referenced by `durable_job_events`, `durable_worker_heartbeats`. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `job_type`: no table-local value CHECK; application-defined or historical value; `status`: `pending`, `retry_waiting`, `leased`, `succeeded`, `exhausted`, `cancelled`; `origin_reference_type`: no table-local value CHECK; application-defined or historical value.
- **CHECK constraints:**
  - `ck_durable_jobs_attempt_count`: `attempt_count >= 0`
  - `ck_durable_jobs_attempt_count_within_maximum`: `attempt_count <= maximum_attempts`
  - `ck_durable_jobs_lease_fields_match_status`: `((status = 'leased') AND lease_token IS NOT NULL AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL) OR ((status <> 'leased') AND lease_token IS NULL AND lease_owner IS NULL AND lease_expires_at IS NULL AND heartbeat_at IS NULL)`
  - `ck_durable_jobs_maximum_attempts`: `maximum_attempts >= 1`
  - `ck_durable_jobs_payload_object`: `jsonb_typeof(payload) = 'object'`
  - `ck_durable_jobs_payload_version`: `payload_version >= 1`
  - `ck_durable_jobs_priority`: `priority >= 0`
  - `ck_durable_jobs_protected_identity_object`: `jsonb_typeof(protected_identity) = 'object'`
  - `ck_durable_jobs_result_metadata_object`: `jsonb_typeof(result_metadata) = 'object'`
  - `ck_durable_jobs_status`: `status IN ('pending', 'retry_waiting', 'leased', 'succeeded', 'exhausted', 'cancelled')`
  - `ck_durable_jobs_terminal_fields_match_status`: `((status = 'succeeded') AND completed_at IS NOT NULL AND exhausted_at IS NULL AND cancelled_at IS NULL) OR ((status = 'exhausted') AND exhausted_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR ((status = 'cancelled') AND cancelled_at IS NOT NULL AND completed_at IS NULL AND exhausted_at IS NULL) OR ((status NOT IN ('succeeded', 'exhausted', 'cancelled')) AND completed_at IS NULL AND exhausted_at IS NULL AND cancelled_at IS NULL)`
- **Indexes:**
  - `ix_durable_jobs_claimable`: `durable_jobs.status, durable_jobs.available_at, durable_jobs.priority, durable_jobs.created_at, durable_jobs.id`
  - `ix_durable_jobs_correlation_id`: `durable_jobs.correlation_id`
  - `ix_durable_jobs_lease_expiry`: `durable_jobs.status, durable_jobs.lease_expires_at, durable_jobs.id`
  - `ix_durable_jobs_origin_reference`: `durable_jobs.origin_reference_type, durable_jobs.origin_reference_id`
  - `ix_durable_jobs_type_version_status`: `durable_jobs.job_type, durable_jobs.payload_version, durable_jobs.status`

### `durable_job_events`

State and attempt history for durable jobs. Sources: [model](../../backend/models/durable_job_event_model.py), [canonical migration](../../backend/alembic/versions/0061_create_durable_job_events_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `id` | `UUID` | No | — | PK |
| `job_id` | `UUID` | No | — | FK → `durable_jobs.id` |
| `event_type` | `VARCHAR(60)` | No | — | — |
| `previous_status` | `VARCHAR(20)` | Yes | — | — |
| `new_status` | `VARCHAR(20)` | Yes | — | — |
| `attempt_count` | `INTEGER` | Yes | — | — |
| `lease_owner` | `VARCHAR(120)` | Yes | — | — |
| `lease_token` | `UUID` | Yes | — | — |
| `safe_error_code` | `VARCHAR(80)` | Yes | — | — |
| `event_metadata` | `JSONB` | No | server `'{}'::jsonb` | — |
| `occurred_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `id`.
- **Foreign keys:** `job_id` → `durable_jobs.id` (ON DELETE CASCADE).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `event_type`: `enqueued`, `claimed`, `heartbeat`, `lease_recovered`, `lease_expired_exhausted`, `succeeded`, `retry_scheduled`, `exhausted`, `cancelled`, `released`, `repair_requeued`, `repair_cancelled`; `previous_status`: no table-local value CHECK; application-defined or historical value; `new_status`: no table-local value CHECK; application-defined or historical value.
- **CHECK constraints:**
  - `ck_durable_job_events_event_type`: `event_type IN ('enqueued', 'claimed', 'heartbeat', 'lease_recovered', 'lease_expired_exhausted', 'succeeded', 'retry_scheduled', 'exhausted', 'cancelled', 'released', 'repair_requeued', 'repair_cancelled')`
  - `ck_durable_job_events_metadata_object`: `jsonb_typeof(event_metadata) = 'object'`
- **Indexes:**
  - `ix_durable_job_events_event_type`: `durable_job_events.event_type`
  - `ix_durable_job_events_job_id`: `durable_job_events.job_id`
  - `ix_durable_job_events_job_occurred_id`: `durable_job_events.job_id, durable_job_events.occurred_at, durable_job_events.id`

### `durable_worker_heartbeats`

Worker liveness and ownership records. Sources: [model](../../backend/models/durable_worker_heartbeat_model.py), [canonical migration](../../backend/alembic/versions/0062_create_durable_worker_heartbeats_table.py#L14).

| Column | PostgreSQL type | Null | Default | Flags / references |
|---|---|:---:|---|---|
| `worker_identity` | `VARCHAR(120)` | No | — | PK |
| `worker_version` | `VARCHAR(80)` | No | — | — |
| `status` | `VARCHAR(20)` | No | server `'starting'` | — |
| `current_job_id` | `UUID` | Yes | — | FK → `durable_jobs.id` |
| `last_started_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `last_heartbeat_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `stopped_at` | `TIMESTAMP WITH TIME ZONE` | Yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | server `now()` | — |

- **Primary key:** `worker_identity`.
- **Foreign keys:** `current_job_id` → `durable_jobs.id` (ON DELETE SET NULL).
- **Unique constraints:** None; see UNIQUE indexes below if present.
- **Other table relationships:** Referenced by no other mapped table. Outbound references are listed under foreign keys.
- **Lifecycle/value fields:** `status`: `starting`, `running`, `stopping`, `stopped`.
- **CHECK constraints:**
  - `ck_durable_worker_heartbeats_status`: `status IN ('starting', 'running', 'stopping', 'stopped')`
  - `ck_durable_worker_heartbeats_stopped_at`: `((status = 'stopped') AND stopped_at IS NOT NULL) OR ((status <> 'stopped') AND stopped_at IS NULL)`
- **Indexes:**
  - `ix_durable_worker_heartbeats_current_job_id`: `durable_worker_heartbeats.current_job_id`
  - `ix_durable_worker_heartbeats_status`: `durable_worker_heartbeats.status, durable_worker_heartbeats.last_heartbeat_at`
