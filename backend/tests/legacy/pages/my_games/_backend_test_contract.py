CONTRACT = {
    "schema_version": 1,
    "review": {
        "sources": [
            {
                "id": "backend-testing",
                "kind": "platform_rule",
                "path": "docs/agent-notes/backend-testing.md",
                "summary": "Backend test compliance, assertion, source-of-truth, runtime evidence, repository, and local test-running rules.",
            },
            {
                "id": "my-games-spec",
                "kind": "feature_spec",
                "path": "docs/agent-notes/my-games.md",
                "summary": "Final My Games backend/page behavior for Games and Need a Sub Upcoming and History.",
            },
            {
                "id": "browse-games-spec",
                "kind": "owning_domain_spec",
                "path": "docs/agent-notes/browse-games.md",
                "summary": "Normal game discovery, hidden access, capacity, and card vocabulary that My Games must keep separate unless explicitly reused.",
            },
            {
                "id": "game-details-spec",
                "kind": "owning_domain_spec",
                "path": "docs/agent-notes/game-details.md",
                "summary": "Normal game cancellation lifecycle and participant cancellation semantics used by My Games History.",
            },
            {
                "id": "need-a-sub-spec",
                "kind": "owning_domain_spec",
                "path": "docs/agent-notes/need-a-sub.md",
                "summary": "Need a Sub post/request lifecycle, status meanings, visibility, cancellation, and My Games history expectations.",
            },
            {
                "id": "my-games-routes",
                "kind": "route",
                "path": "backend/routes/my_game_routes.py",
                "summary": "Authenticated My Games and My Games Need a Sub route definitions and query validation.",
            },
            {
                "id": "game-service",
                "kind": "service",
                "path": "backend/services/game_service.py",
                "summary": "Normal Games My Games eligibility, cursor, sorting, card status, and metadata loading implementation.",
            },
            {
                "id": "need-a-sub-service",
                "kind": "service",
                "path": "backend/services/need_a_sub_post_service.py",
                "summary": "Need a Sub My Games eligibility, cleanup, cursor, sorting, card status, and metadata loading implementation.",
            },
            {
                "id": "game-rules",
                "kind": "service_constant",
                "path": "backend/services/game_rules.py",
                "summary": "Normal game shared lifecycle constants, including OPEN_GAME_STATUSES.",
            },
            {
                "id": "need-a-sub-rules",
                "kind": "service_constant",
                "path": "backend/services/need_a_sub_rules.py",
                "summary": "Need a Sub source constants and now_utc time utility.",
            },
            {
                "id": "game-model",
                "kind": "model",
                "path": "backend/models/game_model.py",
                "summary": "Game lifecycle, publish, visibility, enforcement, and schedule constraints.",
            },
            {
                "id": "game-participant-model",
                "kind": "model",
                "path": "backend/models/game_participant_model.py",
                "summary": "Game participant status and cancellation type constraints.",
            },
            {
                "id": "participant-history-model",
                "kind": "model",
                "path": "backend/models/participant_status_history_model.py",
                "summary": "Participant status history status and change source constraints.",
            },
            {
                "id": "sub-post-model",
                "kind": "model",
                "path": "backend/models/sub_post_model.py",
                "summary": "Need a Sub post lifecycle, visibility, and schedule constraints.",
            },
            {
                "id": "sub-request-model",
                "kind": "model",
                "path": "backend/models/sub_post_request_model.py",
                "summary": "Need a Sub request lifecycle constraints.",
            },
            {
                "id": "sub-request-history-model",
                "kind": "model",
                "path": "backend/models/sub_post_request_status_history_model.py",
                "summary": "Need a Sub request history status and change source constraints.",
            },
            {
                "id": "game-schema",
                "kind": "schema",
                "path": "backend/schemas/game_schema.py",
                "summary": "MyGameCardRead and MyGamesListRead response models.",
            },
            {
                "id": "sub-post-schema",
                "kind": "schema",
                "path": "backend/schemas/sub_post_schema.py",
                "summary": "MyNeedASubCardRead, MyNeedASubListRead, and SubPostPublicRead response models.",
            },
            {
                "id": "my-games-tests",
                "kind": "existing_tests",
                "path": "backend/tests/pages/my_games",
                "summary": "Existing target leaf tests used only as coverage evidence, not as behavior authority.",
            },
            {
                "id": "my-games-fixtures",
                "kind": "fixture",
                "path": "backend/tests/pages/my_games/conftest.py",
                "summary": "Target-local My Games factories and time freezing helper.",
            },
            {
                "id": "backend-test-fixtures",
                "kind": "fixture",
                "path": "backend/tests/conftest.py",
                "summary": "Backend test client, safe test database check, database cleanup, and dependency override cleanup.",
            },
            {
                "id": "backend-test-support",
                "kind": "support",
                "path": "backend/tests/support",
                "summary": "Directly used auth, assertion, cursor, constraint, and user factory helpers for this target.",
            },
            {
                "id": "shared-active-auth-tests",
                "kind": "shared_tests",
                "path": "backend/tests/shared/authentication/test_active_user_dependency.py",
                "summary": "Shared require_active_user dependency coverage for malformed, invalid, expired, revoked, missing-user, suspended, deleted, and pending-deletion actors.",
            },
        ],
        "conflicts": [
            {
                "id": "CONFLICT-NAS-CLOSED-BY-ADMIN",
                "status": "resolved",
                "summary": "need-a-sub.md Status Meanings omits closed_by_admin, while the real request constraint and My Games checklist include it.",
                "resolution": "Use the SQLAlchemy CheckConstraint and the finalized My Games checklist as authoritative for the current backend request-status universe.",
            }
        ],
        "stop_conditions": [],
    },
    "requirements": [
        {
            "id": "MG-API-001",
            "source_id": "my-games-spec",
            "behavior": "Both My Games endpoints require authentication, accept only upcoming/history views, and reject invalid views with the documented client error.",
            "status": "covered",
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_require_authentication",
                "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
            ],
            "reason": "Malformed, invalid, expired, revoked, missing local app-user, suspended, deleted, soft-deleted, and pending-deletion active-user dependency cases are covered in backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_malformed_credentials, backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_invalid_expired_and_revoked_credentials, backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_verified_identity_without_app_user, and backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_inactive_product_account_states.",
        },
        {
            "id": "MG-API-002",
            "source_id": "my-games-spec",
            "behavior": "Both endpoints return the {items, next_cursor, has_more, limit} envelope, default limit 40, cap above 100, accept 100, reject below 1, and return item buckets matching the requested view.",
            "status": "covered",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
            ],
        },
        {
            "id": "MG-GAMES-UPCOMING-001",
            "source_id": "my-games-spec",
            "behavior": "Games Upcoming includes only hosted games or real confirmed current-user participant relationships, including admin-added confirmed rows, and excludes waitlisted-only, pending-payment-only, created-only, guest-only, and old terminal relationships.",
            "status": "covered",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
            ],
        },
        {
            "id": "MG-GAMES-UPCOMING-002",
            "source_id": "my-games-spec",
            "behavior": "Games Upcoming requires non-deleted, non-cancelled active games with ends_at after the captured clock; hidden and paused qualifying personal games remain visible.",
            "status": "covered",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                "test_games_eligibility.py::test_games_upcoming_confirmed_hidden_and_paused_relationships_appear",
                "test_games_eligibility.py::test_games_in_progress_stays_upcoming_until_ends_at",
            ],
        },
        {
            "id": "MG-GAMES-HISTORY-001",
            "source_id": "my-games-spec",
            "behavior": "Games History includes recent ended hosted or confirmed relationships for active, completed, and expired games, prioritizes host cards, and excludes non-confirmed/terminal participant-only relationships.",
            "status": "covered",
            "test_refs": [
                "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                "test_games_eligibility.py::test_games_history_excludes_past_guest_only_relationship",
                "test_games_eligibility.py::test_games_history_uses_host_priority_and_returns_one_card",
            ],
        },
        {
            "id": "MG-GAMES-CANCEL-001",
            "source_id": "my-games-spec",
            "behavior": "Cancelled Games move to History immediately, host qualification is direct, and participant qualification requires current durable game-cancellation proof from a latest confirmed-to-cancelled host/admin transition matching the game cancellation.",
            "status": "partial",
            "test_refs": [
                "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
            ],
            "reason": "The target covers host, host-cancelled confirmed proof, stale still-confirmed rows, wrong old status, wrong source, mismatched timestamp, newer history, and rejected cancellation type; it lacks direct admin-cancelled proof and every rejected source/status variant from the checklist.",
        },
        {
            "id": "MG-GAMES-TIME-001",
            "source_id": "my-games-spec",
            "behavior": "Normal games use one captured UTC clock for upcoming/history boundaries, exact ends_at equality, and the 60-day scheduled history window, including future cancelled items.",
            "status": "partial",
            "test_refs": [
                "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
            "reason": "A frozen-clock behavior test exists, but independent runtime evidence has not recorded controlled before/at/after boundary assertions or one-captured-clock proof.",
        },
        {
            "id": "MG-SUB-UPCOMING-001",
            "source_id": "my-games-spec",
            "behavior": "Need a Sub Upcoming includes only owned posts or current confirmed requester relationships and excludes pending, sub-waitlist, declined, player-cancelled, no-show, closed-by-admin, expired-only, different-user, and request-only relationships.",
            "status": "covered",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_owner_priority_returns_one_card",
                "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
            ],
        },
        {
            "id": "MG-SUB-UPCOMING-002",
            "source_id": "my-games-spec",
            "behavior": "Need a Sub Upcoming excludes cancelled/removed posts, allows active/completed/expired posts until ends_at, keeps hidden qualifying owner/requester posts visible, and does not move in-progress owner/confirmed posts out merely because cleanup changed post_status at starts_at.",
            "status": "covered",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle",
            ],
        },
        {
            "id": "MG-SUB-HISTORY-001",
            "source_id": "my-games-spec",
            "behavior": "Need a Sub History includes recent ended owned or still-confirmed requester relationships, prioritizes owner cards, and excludes pending, sub-waitlist, declined, player-cancelled, expired-only, no-show, closed-by-admin, removed, and admin-removed posts.",
            "status": "covered",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_admin_removed_owned_and_confirmed_requester_posts",
                "test_need_a_sub_eligibility.py::test_need_a_sub_owner_priority_returns_one_card",
            ],
        },
        {
            "id": "MG-SUB-CANCEL-001",
            "source_id": "my-games-spec",
            "behavior": "Owner-cancelled Need a Sub posts move to History immediately for owners and for requesters only when whole-post cancellation proof shows latest confirmed-to-canceled_by_owner owner transition matching sub_post.canceled_at and request.canceled_at.",
            "status": "partial",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
            ],
            "reason": "The target covers owner, valid requester proof, stale still-confirmed rows, wrong old status, wrong source, mismatched history timestamp, mismatched request canceled_at, and newer history; it lacks every rejected source/status variant and admin-removed cancelled variants from the checklist.",
        },
        {
            "id": "MG-SUB-TIME-001",
            "source_id": "my-games-spec",
            "behavior": "Need a Sub uses one captured UTC clock for upcoming/history boundaries, exact ends_at equality, and the 60-day scheduled history window, including future owner-cancelled items.",
            "status": "partial",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
            "reason": "A frozen-clock behavior test exists, but independent runtime evidence has not recorded controlled before/at/after boundary assertions or one-captured-clock proof.",
        },
        {
            "id": "MG-PAGINATION-001",
            "source_id": "my-games-spec",
            "behavior": "Both My Games domains page unique item ids, sort Upcoming by starts_at/created_at/id ascending and History descending, include all cursor comparison keys, reject invalid or cross-domain/cross-view cursors, avoid skips/duplicates, and keep has_more/next_cursor semantics stable.",
            "status": "covered",
            "test_refs": [
                "test_pagination_and_card_data.py::test_exact_limit_page_has_no_next_cursor_for_both_my_games_domains",
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_games_history_pagination_sorts_descending_and_survives_limit_change",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error",
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view",
            ],
        },
        {
            "id": "MG-CARD-DATA-001",
            "source_id": "my-games-spec",
            "behavior": "Games card metadata and Need a Sub card data are loaded after paging without duplicate cards; Games use MyGameCardRead around GameCardRead, Need a Sub uses MyNeedASubCardRead around SubPostPublicRead, and counts/images/positions use the same eligibility filters as the item query.",
            "status": "partial",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards",
                "test_pagination_and_card_data.py::test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards",
            ],
            "reason": "The target covers duplicate-prone participants, images, positions, pending/confirmed counts, and response shape; fallback venue images and every aggregate summary/count filter are not directly covered.",
        },
        {
            "id": "MG-PRIVACY-001",
            "source_id": "backend-testing",
            "behavior": "Authenticated personal-list responses must prove required privacy/cache headers and must not leak hidden or personal records to unrelated users.",
            "status": "covered",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
            ],
        },
        {
            "id": "MG-REGRESSION-001",
            "source_id": "backend-testing",
            "behavior": "Every confirmed My Games production or pre-production bug must have a regression test or a written exception.",
            "status": "not_applicable",
            "reason": "No reviewed finalized source identified any confirmed production or pre-production My Games bug for this pilot target.",
        },
    ],
    "state_matrices": [
        {
            "id": "STATE-GAME-STATUS",
            "source_id": "game-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.game_model",
                "constraint_name": "ck_games_game_status",
            },
            "classifications": [
                {
                    "value": "active",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_in_progress_stays_upcoming_until_ends_at",
                        "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                    ],
                },
                {
                    "value": "completed",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                        "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                    ],
                },
                {
                    "value": "cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only"
                    ],
                },
                {
                    "value": "expired",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                        "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                    ],
                },
                {
                    "value": "removed",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters"
                    ],
                },
            ],
        },
        {
            "id": "STATE-GAME-VISIBILITY",
            "source_id": "game-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.game_model",
                "constraint_name": "ck_games_public_visibility_status",
            },
            "classifications": [
                {
                    "value": "visible",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only"
                    ],
                },
                {
                    "value": "hidden",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters"
                    ],
                },
            ],
        },
        {
            "id": "STATE-GAME-JOIN-ENFORCEMENT",
            "source_id": "game-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.game_model",
                "constraint_name": "ck_games_join_enforcement_status",
            },
            "classifications": [
                {
                    "value": "open",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only"
                    ],
                },
                {
                    "value": "paused",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters"
                    ],
                },
            ],
        },
        {
            "id": "STATE-GAME-PARTICIPANT-STATUS",
            "source_id": "game-participant-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.game_participant_model",
                "constraint_name": "ck_game_participants_participant_status",
            },
            "classifications": [
                {
                    "value": "confirmed",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                    ],
                },
                {
                    "value": "pending_payment",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                    ],
                },
                {
                    "value": "waitlisted",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                    ],
                },
                {
                    "value": "cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                    ],
                },
                {
                    "value": "late_cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                    ],
                },
                {
                    "value": "removed",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                    ],
                },
                {
                    "value": "refunded",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                    ],
                },
            ],
        },
        {
            "id": "STATE-GAME-CANCELLATION-TYPE",
            "source_id": "game-participant-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.game_participant_model",
                "constraint_name": "ck_game_participants_cancellation_type",
            },
            "classifications": [
                {
                    "value": "none",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "on_time",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                    ],
                },
                {
                    "value": "late",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "host_cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                    ],
                },
                {
                    "value": "admin_cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "payment_failed",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                    ],
                },
            ],
        },
        {
            "id": "STATE-GAME-PARTICIPANT-HISTORY-SOURCE",
            "source_id": "participant-history-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.participant_status_history_model",
                "constraint_name": "ck_participant_status_history_change_source",
            },
            "classifications": [
                {
                    "value": "user",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                    ],
                },
                {
                    "value": "host",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
                        "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                    ],
                },
                {
                    "value": "admin",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "system",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "payment_webhook",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "scheduled_job",
                    "classification": "covered",
                    "test_refs": [
                        "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values"
                    ],
                },
            ],
        },
        {
            "id": "STATE-SUB-POST-STATUS",
            "source_id": "sub-post-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.sub_post_model",
                "constraint_name": "ck_sub_posts_post_status",
            },
            "classifications": [
                {
                    "value": "active",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                    ],
                },
                {
                    "value": "completed",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
                    ],
                },
                {
                    "value": "cancelled",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                    ],
                },
                {
                    "value": "expired",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
                    ],
                },
                {
                    "value": "removed",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                    ],
                },
            ],
        },
        {
            "id": "STATE-SUB-POST-VISIBILITY",
            "source_id": "sub-post-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.sub_post_model",
                "constraint_name": "ck_sub_posts_public_visibility_status",
            },
            "classifications": [
                {
                    "value": "visible",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only"
                    ],
                },
                {
                    "value": "hidden",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear"
                    ],
                },
            ],
        },
        {
            "id": "STATE-SUB-REQUEST-STATUS",
            "source_id": "sub-request-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.sub_post_request_model",
                "constraint_name": "ck_sub_post_requests_request_status",
            },
            "classifications": [
                {
                    "value": "pending",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "confirmed",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "declined",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "sub_waitlist",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "canceled_by_player",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "canceled_by_owner",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                    ],
                },
                {
                    "value": "no_show_reported",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "expired",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
                {
                    "value": "closed_by_admin",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                    ],
                },
            ],
        },
        {
            "id": "STATE-SUB-REQUEST-HISTORY-SOURCE",
            "source_id": "sub-request-history-model",
            "authoritative_source": {
                "kind": "sqlalchemy_check_constraint",
                "module": "backend.models.sub_post_request_status_history_model",
                "constraint_name": "ck_sub_post_request_status_history_change_source",
            },
            "classifications": [
                {
                    "value": "requester",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                    ],
                },
                {
                    "value": "owner",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
                        "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                    ],
                },
                {
                    "value": "admin",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "system",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values"
                    ],
                },
                {
                    "value": "scheduled_job",
                    "classification": "covered",
                    "test_refs": [
                        "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values"
                    ],
                },
            ],
        },
    ],
    "scenarios": [
        {
            "id": "SCN-NORMAL-VALID",
            "category": "normal",
            "item": "Valid request succeeds.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
            ],
        },
        {
            "id": "SCN-NORMAL-CONTRACT",
            "category": "normal",
            "item": "Response matches the final API contract.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards",
                "test_pagination_and_card_data.py::test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards",
            ],
        },
        {
            "id": "SCN-NORMAL-DB-STATE",
            "category": "normal",
            "item": "Expected database state is produced.",
            "applicability": "required",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle"
            ],
        },
        {
            "id": "SCN-VAL-MISSING-FIELDS",
            "category": "validation",
            "item": "Missing required fields.",
            "applicability": "not_relevant",
            "reason": "These are GET list endpoints with no required request body fields; required query fields have defaults.",
        },
        {
            "id": "SCN-VAL-INVALID-TYPES",
            "category": "validation",
            "item": "Invalid types.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error"
            ],
        },
        {
            "id": "SCN-VAL-INVALID-ENUM",
            "category": "validation",
            "item": "Invalid enum values.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_reject_invalid_view"
            ],
        },
        {
            "id": "SCN-VAL-DATETIME-FORMAT",
            "category": "validation",
            "item": "Invalid date or timestamp formats.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error"
            ],
        },
        {
            "id": "SCN-VAL-LIMITS",
            "category": "validation",
            "item": "Values below or above allowed limits.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max"
            ],
        },
        {
            "id": "SCN-VAL-CONFLICTING-FIELDS",
            "category": "validation",
            "item": "Conflicting fields.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view"
            ],
        },
        {
            "id": "SCN-VAL-MALFORMED-CURSOR",
            "category": "validation",
            "item": "Malformed cursor or token.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error"
            ],
        },
        {
            "id": "SCN-AUTH-ANON",
            "category": "authentication",
            "item": "Anonymous request where authentication is required.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_require_authentication"
            ],
        },
        {
            "id": "SCN-AUTH-VALID",
            "category": "authentication",
            "item": "Valid authenticated request.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit"
            ],
        },
        {
            "id": "SCN-AUTH-INVALID",
            "category": "authentication",
            "item": "Invalid or malformed credentials.",
            "applicability": "covered_elsewhere",
            "reason": "Covered by the shared active-user dependency tests at backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_malformed_credentials and backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_invalid_expired_and_revoked_credentials.",
        },
        {
            "id": "SCN-AUTH-EXPIRED",
            "category": "authentication",
            "item": "Expired credentials when relevant.",
            "applicability": "covered_elsewhere",
            "reason": "Covered by the shared active-user dependency test at backend/tests/shared/authentication/test_active_user_dependency.py::test_active_user_dependency_rejects_invalid_expired_and_revoked_credentials, which distinguishes invalid, expired, and revoked verifier failures while exercising require_active_user.",
        },
        {
            "id": "SCN-AZ-OWNER",
            "category": "authorization_visibility",
            "item": "Owner or host access.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
            ],
        },
        {
            "id": "SCN-AZ-RELATIONSHIP",
            "category": "authorization_visibility",
            "item": "Participant or relationship-based access.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
            ],
        },
        {
            "id": "SCN-AZ-STALE-DENIAL",
            "category": "authorization_visibility",
            "item": "Stale, expired, cancelled, removed, or no-longer-active relationship denial.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                "test_games_eligibility.py::test_games_history_excludes_past_guest_only_relationship",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
            ],
        },
        {
            "id": "SCN-AZ-UNRELATED-DENIAL",
            "category": "authorization_visibility",
            "item": "Unrelated-user denial.",
            "applicability": "required",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
            ],
        },
        {
            "id": "SCN-AZ-ADMIN-ACCESS",
            "category": "authorization_visibility",
            "item": "Admin or privileged-role access.",
            "applicability": "not_relevant",
            "reason": "My Games list endpoints are personal authenticated user lists and the finalized My Games spec does not define admin bypass or privileged listing behavior.",
        },
        {
            "id": "SCN-AZ-INVALID-ADMIN",
            "category": "authorization_visibility",
            "item": "Invalid privileged actor denial, including inactive, suspended, deleted, or revoked actors when those states exist.",
            "applicability": "not_relevant",
            "reason": "The My Games endpoints do not expose privileged actor behavior.",
        },
        {
            "id": "SCN-AZ-HORIZONTAL",
            "category": "authorization_visibility",
            "item": "Horizontal authorization using another user's resource ID.",
            "applicability": "not_relevant",
            "reason": "The list endpoints accept no resource ID; relationship filtering covers records owned by or connected to other users.",
        },
        {
            "id": "SCN-AZ-VERTICAL",
            "category": "authorization_visibility",
            "item": "Vertical authorization using a lower-privilege user.",
            "applicability": "not_relevant",
            "reason": "The My Games endpoints have no higher-privilege operation or admin path.",
        },
        {
            "id": "SCN-AZ-HIDDEN",
            "category": "authorization_visibility",
            "item": "Hidden or private resource behavior.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                "test_games_eligibility.py::test_games_upcoming_confirmed_hidden_and_paused_relationships_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
            ],
        },
        {
            "id": "SCN-AZ-HIDDEN-ENUMERATION",
            "category": "authorization_visibility",
            "item": "Hidden or private resource enumeration through detail, list, lookup, and helper routes that accept resource identifiers.",
            "applicability": "covered_elsewhere",
            "reason": "Hidden detail/lookup routes with identifiers are owned by Game Details, Browse hidden access, and Need a Sub detail; this target covers hidden records only in the personal list.",
        },
        {
            "id": "SCN-AZ-HTTP-POLICY",
            "category": "authorization_visibility",
            "item": "Correct 401, 403, or 404 response according to policy.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_require_authentication"
            ],
        },
        {
            "id": "SCN-AZ-CACHE",
            "category": "authorization_visibility",
            "item": "Required privacy and cache headers.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
            ],
        },
        {
            "id": "SCN-STATE-ALLOWED",
            "category": "state_lifecycle",
            "item": "Allowed state transitions.",
            "applicability": "not_relevant",
            "reason": "My Games list endpoints do not expose lifecycle transition commands; they classify already-existing states.",
        },
        {
            "id": "SCN-STATE-PROHIBITED",
            "category": "state_lifecycle",
            "item": "Prohibited state transitions.",
            "applicability": "not_relevant",
            "reason": "My Games list endpoints do not expose lifecycle transition commands.",
        },
        {
            "id": "SCN-STATE-REPEATED",
            "category": "state_lifecycle",
            "item": "Repeated transition attempts.",
            "applicability": "not_relevant",
            "reason": "My Games list endpoints do not expose transition attempts.",
        },
        {
            "id": "SCN-STATE-TERMINAL",
            "category": "state_lifecycle",
            "item": "Terminal-state behavior.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
            ],
        },
        {
            "id": "SCN-STATE-HISTORICAL-ROWS",
            "category": "state_lifecycle",
            "item": "Historical rows not granting active privileges.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
            ],
        },
        {
            "id": "SCN-TIME-BEFORE",
            "category": "dates_times_expiration",
            "item": "Before the boundary.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_in_progress_stays_upcoming_until_ends_at",
                "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle",
            ],
        },
        {
            "id": "SCN-TIME-AT",
            "category": "dates_times_expiration",
            "item": "At the exact boundary.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
                "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
        },
        {
            "id": "SCN-TIME-AFTER",
            "category": "dates_times_expiration",
            "item": "After the boundary.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
            ],
        },
        {
            "id": "SCN-TIME-UTC",
            "category": "dates_times_expiration",
            "item": "UTC handling.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
                "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
        },
        {
            "id": "SCN-TIME-ZONE",
            "category": "dates_times_expiration",
            "item": "Configured timezone behavior.",
            "applicability": "not_relevant",
            "reason": "My Games backend eligibility and pagination use captured UTC now and starts_at/ends_at; the finalized spec assigns date grouping to the frontend and does not make configured application timezone a backend list predicate.",
        },
        {
            "id": "SCN-TIME-DST",
            "category": "dates_times_expiration",
            "item": "Daylight-saving transitions when relevant.",
            "applicability": "not_relevant",
            "reason": "The backend My Games eligibility boundaries are UTC ends_at comparisons; frontend date grouping owns display by local date.",
        },
        {
            "id": "SCN-TIME-EXPIRED-UNCLEANED",
            "category": "dates_times_expiration",
            "item": "Expired records that cleanup has not processed yet.",
            "applicability": "required",
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle"
            ],
        },
        {
            "id": "SCN-CAPACITY-EMPTY",
            "category": "capacity_concurrency",
            "item": "Empty capacity.",
            "applicability": "not_relevant",
            "reason": "My Games is a personal list and does not expose join capacity decisions; card counts are covered under pagination/card data.",
        },
        {
            "id": "SCN-CAPACITY-ONE-LEFT",
            "category": "capacity_concurrency",
            "item": "One remaining spot.",
            "applicability": "not_relevant",
            "reason": "Capacity admission is owned by Browse/Game Details checkout, not My Games list eligibility.",
        },
        {
            "id": "SCN-CAPACITY-FULL",
            "category": "capacity_concurrency",
            "item": "Exactly full.",
            "applicability": "not_relevant",
            "reason": "Full/open admission is not a My Games list decision.",
        },
        {
            "id": "SCN-CAPACITY-OVER",
            "category": "capacity_concurrency",
            "item": "Over-capacity defensive behavior.",
            "applicability": "not_relevant",
            "reason": "Over-capacity writes are outside this read/list target.",
        },
        {
            "id": "SCN-CAPACITY-HOLDS",
            "category": "capacity_concurrency",
            "item": "Expired temporary holds.",
            "applicability": "required",
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
            ],
        },
        {
            "id": "SCN-CAPACITY-PARTY",
            "category": "capacity_concurrency",
            "item": "Multiple participant rows under one booking.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards"
            ],
        },
        {
            "id": "SCN-CAPACITY-FINAL-SPOT",
            "category": "capacity_concurrency",
            "item": "Competing requests for the final spot.",
            "applicability": "not_relevant",
            "reason": "Concurrent admission to a final spot is owned by checkout and Need a Sub request lifecycle, not My Games list reads.",
        },
        {
            "id": "SCN-CAPACITY-LOCKS",
            "category": "capacity_concurrency",
            "item": "Required transaction and row-lock behavior.",
            "applicability": "not_relevant",
            "reason": "The target list endpoints do not allocate capacity or require final-spot row locks.",
        },
        {
            "id": "SCN-PAGE-FIRST",
            "category": "pagination_sorting_counts",
            "item": "First page.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
            ],
        },
        {
            "id": "SCN-PAGE-MIDDLE",
            "category": "pagination_sorting_counts",
            "item": "Middle page.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
            ],
        },
        {
            "id": "SCN-PAGE-FINAL",
            "category": "pagination_sorting_counts",
            "item": "Final page.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
            ],
        },
        {
            "id": "SCN-PAGE-EXACT",
            "category": "pagination_sorting_counts",
            "item": "Exact-limit page.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_exact_limit_page_has_no_next_cursor_for_both_my_games_domains"
            ],
        },
        {
            "id": "SCN-PAGE-EMPTY",
            "category": "pagination_sorting_counts",
            "item": "Empty page.",
            "applicability": "required",
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit"
            ],
        },
        {
            "id": "SCN-PAGE-STABLE",
            "category": "pagination_sorting_counts",
            "item": "Stable ordering when primary sort values match.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
            ],
        },
        {
            "id": "SCN-PAGE-CURSOR-MISMATCH",
            "category": "pagination_sorting_counts",
            "item": "Cursor mismatch.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view"
            ],
        },
        {
            "id": "SCN-PAGE-INVALID-CURSOR",
            "category": "pagination_sorting_counts",
            "item": "Invalid cursor.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error"
            ],
        },
        {
            "id": "SCN-PAGE-NO-DUPES",
            "category": "pagination_sorting_counts",
            "item": "No duplicates across pages.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
            ],
        },
        {
            "id": "SCN-PAGE-AGGREGATES",
            "category": "pagination_sorting_counts",
            "item": "Aggregate totals, grouped counts, summaries, and available-count fields use the same authorization, visibility, lifecycle, cutoff, and status filters as the item query.",
            "applicability": "required",
            "test_refs": [
                "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards",
                "test_pagination_and_card_data.py::test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards",
            ],
        },
        {
            "id": "SCN-EXT-SUCCESS",
            "category": "external_webhooks",
            "item": "Successful provider response.",
            "applicability": "not_relevant",
            "reason": "My Games list endpoints do not call external providers or receive webhooks.",
        },
        {
            "id": "SCN-EXT-FAILURE",
            "category": "external_webhooks",
            "item": "Provider failure.",
            "applicability": "not_relevant",
            "reason": "No provider request is part of this target.",
        },
        {
            "id": "SCN-EXT-TIMEOUT",
            "category": "external_webhooks",
            "item": "Timeout or exception.",
            "applicability": "not_relevant",
            "reason": "No external-provider call is part of this target.",
        },
        {
            "id": "SCN-EXT-DUPLICATE",
            "category": "external_webhooks",
            "item": "Duplicate webhook.",
            "applicability": "not_relevant",
            "reason": "Webhook idempotency belongs to payment/notification webhook targets, not My Games list reads.",
        },
        {
            "id": "SCN-EXT-OUT-OF-ORDER",
            "category": "external_webhooks",
            "item": "Out-of-order webhook.",
            "applicability": "not_relevant",
            "reason": "This target has no webhook handler.",
        },
        {
            "id": "SCN-EXT-LATE",
            "category": "external_webhooks",
            "item": "Late webhook.",
            "applicability": "not_relevant",
            "reason": "This target has no webhook handler.",
        },
        {
            "id": "SCN-EXT-SIGNATURE",
            "category": "external_webhooks",
            "item": "Invalid webhook signature.",
            "applicability": "not_relevant",
            "reason": "This target has no webhook signature validation.",
        },
        {
            "id": "SCN-EXT-IDEMPOTENT",
            "category": "external_webhooks",
            "item": "Idempotent retry behavior.",
            "applicability": "not_relevant",
            "reason": "This target has no webhook retry operation.",
        },
        {
            "id": "SCN-REGRESSION",
            "category": "regression",
            "item": "Every confirmed production or pre-production bug has a regression test or written exception.",
            "applicability": "not_relevant",
            "reason": "No confirmed production or pre-production My Games bug exists in the reviewed finalized sources for this pilot target.",
        },
    ],
    "ownership": [
        {
            "test_ref": "test_api_contract.py::test_my_games_endpoints_require_authentication",
            "owner_kind": "page",
            "behavior_under_test": "My Games and Need a Sub My Games endpoint authentication.",
            "rationale": "The page/domain route owns rejecting unauthenticated list access.",
        },
        {
            "test_ref": "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
            "owner_kind": "page",
            "behavior_under_test": "My Games endpoint view validation.",
            "rationale": "The page/domain services own the upcoming/history view contract.",
        },
        {
            "test_ref": "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
            "owner_kind": "page",
            "behavior_under_test": "Empty response envelope and default limit.",
            "rationale": "The My Games page endpoints own the list envelope.",
        },
        {
            "test_ref": "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
            "owner_kind": "page",
            "behavior_under_test": "Limit lower-bound validation and max cap.",
            "rationale": "The My Games page endpoints own their pagination limit API.",
        },
        {
            "test_ref": "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
            "owner_kind": "page",
            "behavior_under_test": "Games item bucket matches requested view.",
            "rationale": "The My Games Games list owns bucket labeling.",
        },
        {
            "test_ref": "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub item bucket matches requested view.",
            "rationale": "The My Games Need a Sub list owns bucket labeling.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_status_matrices_cover_authoritative_model_values",
            "owner_kind": "page",
            "behavior_under_test": "My Games classifications of participant statuses, cancellation types, and status-history sources.",
            "rationale": "The page owns how shared model values qualify or do not qualify for My Games.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
            "owner_kind": "page",
            "behavior_under_test": "Games Upcoming qualifying and excluded relationships.",
            "rationale": "My Games owns personal list eligibility separate from Browse.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
            "owner_kind": "page",
            "behavior_under_test": "Games Upcoming lifecycle, hidden, paused, and deletion filters.",
            "rationale": "The page owns personal eligibility for qualifying hidden/paused records.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_upcoming_confirmed_hidden_and_paused_relationships_appear",
            "owner_kind": "page",
            "behavior_under_test": "Games Upcoming hidden and join-paused confirmed participant eligibility.",
            "rationale": "The page owns personal visibility for qualifying confirmed records that public discovery may treat differently.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_in_progress_stays_upcoming_until_ends_at",
            "owner_kind": "page",
            "behavior_under_test": "Games in-progress boundary remains Upcoming until ends_at.",
            "rationale": "The My Games page owns upcoming/history bucket boundaries.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
            "owner_kind": "page",
            "behavior_under_test": "Games History ended host/confirmed relationships and labels.",
            "rationale": "The My Games page owns history eligibility and labels.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
            "owner_kind": "page",
            "behavior_under_test": "Games History terminal/non-confirmed exclusions.",
            "rationale": "The My Games page owns preventing stale relationships from granting history cards.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_history_excludes_past_guest_only_relationship",
            "owner_kind": "page",
            "behavior_under_test": "Games History guest-only relationship exclusion.",
            "rationale": "My Games requires a real current-user host or participant relationship, not a guest row owned by the user.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_history_uses_host_priority_and_returns_one_card",
            "owner_kind": "page",
            "behavior_under_test": "Games host priority and de-duplication.",
            "rationale": "The My Games page owns one-card personal list presentation.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
            "owner_kind": "page",
            "behavior_under_test": "Games cancelled History eligibility proof.",
            "rationale": "My Games owns durable participant cancellation proof for cancelled history cards.",
        },
        {
            "test_ref": "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
            "owner_kind": "page",
            "behavior_under_test": "Games exact ends_at and 60-day scheduled history window.",
            "rationale": "The My Games page owns list time boundaries.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_status_matrices_cover_authoritative_model_values",
            "owner_kind": "page",
            "behavior_under_test": "My Games Need a Sub status/source classifications.",
            "rationale": "The page owns how Need a Sub model statuses qualify for My Games.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub Upcoming qualifying/excluded relationships.",
            "rationale": "My Games owns personal Need a Sub eligibility.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_owner_priority_returns_one_card",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub owner priority and one-card behavior.",
            "rationale": "My Games owns personal card de-duplication and owner priority.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub Upcoming post lifecycle filters.",
            "rationale": "My Games owns how Need a Sub post lifecycle maps to list buckets.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear",
            "owner_kind": "page",
            "behavior_under_test": "Hidden Need a Sub owner/requester personal visibility.",
            "rationale": "My Games owns personal list visibility for qualifying hidden posts.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
            "owner_kind": "page",
            "behavior_under_test": "Hidden Need a Sub pending and sub-waitlist requester exclusions.",
            "rationale": "Hidden status does not promote non-confirmed request relationships into My Games.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub pre-read cleanup and in-progress Upcoming retention.",
            "rationale": "My Games owns preventing cleanup lifecycle changes from moving qualifying in-progress posts out early.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub History ended owner/confirmed relationships.",
            "rationale": "My Games owns Need a Sub history eligibility.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub History non-confirmed relationship exclusions.",
            "rationale": "My Games owns excluding stale or terminal request-only relationships.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_admin_removed_owned_and_confirmed_requester_posts",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub History admin-removed owner and confirmed-requester exclusions.",
            "rationale": "Removed/admin-removed posts are excluded from My Games even when the user otherwise has an owner or confirmed requester relationship.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub cancelled History whole-post cancellation proof.",
            "rationale": "My Games owns distinguishing whole-post cancellation from single requester removal.",
        },
        {
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub exact ends_at and 60-day scheduled history window.",
            "rationale": "My Games owns list time boundaries.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_exact_limit_page_has_no_next_cursor_for_both_my_games_domains",
            "owner_kind": "page",
            "behavior_under_test": "Exact-limit pagination for both My Games domains.",
            "rationale": "My Games owns cursor envelope semantics.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
            "owner_kind": "page",
            "behavior_under_test": "Games Upcoming sort, cursor, and no duplicates.",
            "rationale": "My Games owns Games pagination.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
            "owner_kind": "page",
            "behavior_under_test": "Three-page cursor pagination with genuine middle pages for both My Games domains.",
            "rationale": "My Games owns first, middle, final, cursor metadata, stable ordering, omitted-row, and duplicate prevention semantics for its list endpoints.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_games_history_pagination_sorts_descending_and_survives_limit_change",
            "owner_kind": "page",
            "behavior_under_test": "Games History descending pagination and limit change.",
            "rationale": "My Games owns Games history cursor behavior.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards",
            "owner_kind": "page",
            "behavior_under_test": "Games card metadata after paging without duplication.",
            "rationale": "My Games owns joining card metadata after unique paged games.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub Upcoming sort, cursor, and no duplicates.",
            "rationale": "My Games owns Need a Sub pagination.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub History descending sort and three-page cursor traversal.",
            "rationale": "My Games owns Need a Sub History first, middle, final, cursor metadata, omitted-row, and duplicate prevention semantics.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards",
            "owner_kind": "page",
            "behavior_under_test": "Need a Sub card data after paging without duplication.",
            "rationale": "My Games owns joining positions and counts after unique paged posts.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error",
            "owner_kind": "page",
            "behavior_under_test": "Invalid cursor payload errors for both domains.",
            "rationale": "My Games owns its cursor payload contract.",
        },
        {
            "test_ref": "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view",
            "owner_kind": "page",
            "behavior_under_test": "Cursor domain/view binding.",
            "rationale": "My Games owns preventing cross-domain and cross-view cursor reuse.",
        },
    ],
    "effects": [
        {
            "id": "EFF-SUB-PRE-READ-CLEANUP",
            "source_id": "my-games-spec",
            "phase": "successful_mutation",
            "kind": "field_changed",
            "model": "backend.models.sub_post_model.SubPost",
            "lookup": {
                "label": "need_a_sub_in_progress_cleanup_post",
                "field": "id",
            },
            "field": "post_status",
            "before": {
                "equals": "active"
            },
            "after": {
                "in": [
                    "completed",
                    "expired",
                ]
            },
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle",
            "why_runtime_evidence_is_required": "Running pytest alone does not prove the cleanup status change was observed from persisted before/after state.",
        }
    ],
    "constraints": [],
    "time_boundaries": [
        {
            "id": "TIME-GAMES-EXACT-AND-WINDOW",
            "source_id": "my-games-spec",
            "clock_strategy": "frozen",
            "boundary_cases": ["at_ends_at", "sixty_day_window", "older_than_sixty_days", "future_cancelled_immediate"],
            "test_ref": "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
        },
        {
            "id": "TIME-SUB-IN-PROGRESS-CLEANUP",
            "source_id": "my-games-spec",
            "clock_strategy": "frozen",
            "boundary_cases": ["after_starts_at", "before_ends_at", "expired_cleanup_due"],
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle",
        },
        {
            "id": "TIME-SUB-EXACT-AND-WINDOW",
            "source_id": "my-games-spec",
            "clock_strategy": "frozen",
            "boundary_cases": ["at_ends_at", "sixty_day_window", "older_than_sixty_days", "future_cancelled_immediate"],
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
        },
    ],
    "clock_controls": [
        {
            "id": "CLOCK-MY-GAMES-GENEROUS-OFFSETS",
            "source_id": "my-games-spec",
            "strategy": "captured_test_baseline",
            "reason": "These tests intentionally capture one local now value and use generous future/past offsets; they do not protect exact runtime time boundaries.",
            "test_refs": [
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_api_contract.py::test_my_need_a_sub_response_item_bucket_matches_requested_view",
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                "test_games_eligibility.py::test_games_upcoming_confirmed_hidden_and_paused_relationships_appear",
                "test_games_eligibility.py::test_games_in_progress_stays_upcoming_until_ends_at",
                "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
                "test_games_eligibility.py::test_games_history_excludes_past_guest_only_relationship",
                "test_games_eligibility.py::test_games_history_uses_host_priority_and_returns_one_card",
                "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_owner_priority_returns_one_card",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_admin_removed_owned_and_confirmed_requester_posts",
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                "test_pagination_and_card_data.py::test_exact_limit_page_has_no_next_cursor_for_both_my_games_domains",
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_games_history_pagination_sorts_descending_and_survives_limit_change",
                "test_pagination_and_card_data.py::test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
                "test_pagination_and_card_data.py::test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards",
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view",
            ],
        },
        {
            "id": "CLOCK-MY-GAMES-FROZEN-CURSOR-BASELINE",
            "source_id": "my-games-spec",
            "strategy": "frozen_application_clock",
            "reason": "The three-page cursor test freezes the application clock to keep the scenario deterministic, but its runtime proof is pagination metadata and row continuity rather than a time-boundary assertion.",
            "test_refs": [
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
            ],
        },
    ],
    "review_flags": [
        {
            "id": "RF-PARAM-API-AUTH",
            "kind": "parametrization_shape",
            "summary": "Both endpoint rows use the same unauthenticated GET setup, action, rule, and 401 assertion shape.",
            "status": "confirmed",
            "test_ref": "test_api_contract.py::test_my_games_endpoints_require_authentication",
        },
        {
            "id": "RF-PARAM-API-INVALID-VIEW",
            "kind": "parametrization_shape",
            "summary": "Both endpoint rows use the same authenticated invalid-view GET setup, action, rule, and 400/detail assertion shape.",
            "status": "confirmed",
            "test_ref": "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
        },
        {
            "id": "RF-PARAM-API-EMPTY",
            "kind": "parametrization_shape",
            "summary": "Both endpoint rows use the same authenticated empty-list setup, action, rule, and envelope assertion shape.",
            "status": "confirmed",
            "test_ref": "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
        },
        {
            "id": "RF-PARAM-API-LIMIT",
            "kind": "parametrization_shape",
            "summary": "Both endpoint rows use the same authenticated limit validation setup, action, rule, and response assertion shape.",
            "status": "confirmed",
            "test_ref": "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
        },
        {
            "id": "RF-PARAM-GAMES-UPCOMING-FILTERS",
            "kind": "parametrization_shape",
            "summary": "Each field/value row mutates one lifecycle or visibility dimension while keeping the same setup, action, rule, and inclusion assertion shape.",
            "status": "confirmed",
            "test_ref": "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
        },
        {
            "id": "RF-PARAM-GAMES-HISTORY-EXCLUSIONS",
            "kind": "parametrization_shape",
            "summary": "Each participant-status row uses the same past game setup, action, exclusion rule, and empty-list assertion shape.",
            "status": "confirmed",
            "test_ref": "test_games_eligibility.py::test_games_history_excludes_non_confirmed_past_relationships",
        },
        {
            "id": "RF-PARAM-SUB-UPCOMING-FILTERS",
            "kind": "parametrization_shape",
            "summary": "Each post-status row mutates one lifecycle value while keeping the same setup, action, rule, and inclusion assertion shape.",
            "status": "confirmed",
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
        },
        {
            "id": "RF-PARAM-SUB-HIDDEN",
            "kind": "parametrization_shape",
            "summary": "Owner and confirmed-requester rows use the same hidden qualifying relationship rule and response assertion shape with equivalent relationship setup.",
            "status": "confirmed",
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_qualifying_relationships_still_appear",
        },
        {
            "id": "RF-PARAM-SUB-HIDDEN-DENIAL",
            "kind": "parametrization_shape",
            "summary": "Pending and sub-waitlist rows use the same hidden requester setup, action, rule, and empty-list assertion shape.",
            "status": "confirmed",
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
        },
        {
            "id": "RF-PARAM-SUB-HISTORY-EXCLUSIONS",
            "kind": "parametrization_shape",
            "summary": "Each request-status row uses the same past post setup, action, exclusion rule, and empty-list assertion shape.",
            "status": "confirmed",
            "test_ref": "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_non_confirmed_past_relationships",
        },
        {
            "id": "RF-PARAM-CURSOR-INVALID",
            "kind": "parametrization_shape",
            "summary": "Each cursor row uses the same authenticated request, invalid-cursor rule, and 400/detail assertion shape.",
            "status": "confirmed",
            "test_ref": "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error",
        },
        {
            "id": "RF-MUT-NETWORK-BLOCKING",
            "kind": "network_blocking",
            "summary": "Mutation runtime uses the compliance.runtime pytest plugin with BACKEND_TEST_BLOCK_NETWORK=1; only the configured local test database socket is allowed.",
            "status": "confirmed",
        },
    ],
    "gaps": [],
    "mutation_targets": [
        {
            "id": "MUT-MG-GAMES-LIST-ELIGIBILITY",
            "source_id": "game-service",
            "module": "backend.services.game_service",
            "protected_requirement": "My Games game cards include only owned or confirmed relationships in the requested upcoming/history bucket, with cancelled-history proof and the 60-day history cutoff.",
            "symbols": [
                "MY_GAMES_HISTORY_WINDOW_DAYS",
                "MY_GAMES_CONFIRMED_STATUSES",
                "MY_GAMES_CANCELLED_TYPES",
                "list_my_game_cards",
                "load_my_games_user_participants",
                "get_my_games_participant_priority",
            ],
            "test_refs": [
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_games_eligibility.py::test_games_upcoming_lifecycle_and_visibility_filters",
                "test_games_eligibility.py::test_games_upcoming_confirmed_hidden_and_paused_relationships_appear",
                "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                "test_games_eligibility.py::test_games_history_excludes_past_guest_only_relationship",
                "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
                "test_games_eligibility.py::test_games_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
        },
        {
            "id": "MUT-MG-GAMES-CARD-STATUS",
            "source_id": "game-service",
            "module": "backend.services.game_service",
            "protected_requirement": "My Games game cards expose the correct bucket, host/participant relationship fields, and status label/tone for upcoming, history, and cancelled results.",
            "symbols": [
                "build_my_game_card_read",
                "get_my_game_status",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_response_item_bucket_matches_requested_view",
                "test_games_eligibility.py::test_games_upcoming_includes_host_and_confirmed_only",
                "test_games_eligibility.py::test_games_history_includes_recent_ended_host_and_confirmed_relationships",
                "test_games_eligibility.py::test_games_cancelled_history_includes_host_and_confirmed_proof_only",
            ],
        },
        {
            "id": "MUT-MG-GAMES-VIEW-LIMITS",
            "source_id": "game-service",
            "module": "backend.services.game_service",
            "protected_requirement": "My Games game requests normalize and validate the view parameter and return the documented default and capped page limits.",
            "symbols": [
                "MY_GAMES_CARD_DEFAULT_LIMIT",
                "MY_GAMES_CARD_MAX_LIMIT",
                "MY_GAMES_VALID_VIEWS",
                "normalize_my_games_view",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
            ],
        },
        {
            "id": "MUT-MG-GAMES-CURSOR-CONTRACT",
            "source_id": "game-service",
            "module": "backend.services.game_service",
            "protected_requirement": "My Games game cursors are encoded, decoded, validated, and bound to the games domain, requested view, and sort direction.",
            "symbols": [
                "MY_GAMES_CURSOR_DOMAIN",
                "encode_my_games_cursor",
                "decode_my_games_cursor",
                "validate_my_games_cursor_context",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error",
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
            ],
        },
        {
            "id": "MUT-MG-GAMES-CURSOR-FILTER",
            "source_id": "game-service",
            "module": "backend.services.game_service",
            "protected_requirement": "My Games game pagination applies stable starts_at, created_at, and id cursor ordering without duplicates or omissions.",
            "symbols": [
                "build_my_games_cursor_filter",
                "parse_browse_game_card_cursor_datetime",
                "parse_browse_game_card_cursor_uuid",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
                "test_pagination_and_card_data.py::test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_games_history_pagination_sorts_descending_and_survives_limit_change",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
            ],
        },
        {
            "id": "MUT-MG-SUB-LIST-ELIGIBILITY",
            "source_id": "need-a-sub-service",
            "module": "backend.services.need_a_sub_post_service",
            "protected_requirement": "My Games Need a Sub cards include only owned or confirmed-request relationships in the requested upcoming/history bucket, with whole-post cancellation proof and pre-read cleanup.",
            "symbols": [
                "MY_NEED_A_SUB_CARD_DEFAULT_LIMIT",
                "MY_NEED_A_SUB_CARD_MAX_LIMIT",
                "MY_NEED_A_SUB_VALID_VIEWS",
                "MY_NEED_A_SUB_HISTORY_WINDOW_DAYS",
                "list_my_need_a_sub_cards",
                "load_my_need_a_sub_user_requests",
                "get_my_need_a_sub_request_priority",
            ],
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_post_lifecycle_filters",
                "test_need_a_sub_eligibility.py::test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear",
                "test_need_a_sub_eligibility.py::test_need_a_sub_history_excludes_admin_removed_owned_and_confirmed_requester_posts",
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
                "test_need_a_sub_eligibility.py::test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window",
            ],
        },
        {
            "id": "MUT-MG-SUB-CARD-STATUS",
            "source_id": "need-a-sub-service",
            "module": "backend.services.need_a_sub_post_service",
            "protected_requirement": "My Games Need a Sub cards expose correct owner/request relationship fields and status label/tone.",
            "symbols": [
                "build_my_need_a_sub_card_read",
                "get_my_need_a_sub_status",
            ],
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
            ],
        },
        {
            "id": "MUT-MG-SUB-DETAIL-ACCESS",
            "source_id": "need-a-sub-service",
            "module": "backend.services.need_a_sub_post_service",
            "protected_requirement": "My Games Need a Sub cards expose the private-detail access flag only for owners, currently confirmed requesters, or recently ended confirmed requesters.",
            "symbols": [
                "MY_NEED_A_SUB_DETAIL_ACCESS_HOURS",
                "user_can_view_private_sub_post",
                "user_has_current_confirmed_sub_post_request",
            ],
            "test_refs": [
                "test_need_a_sub_eligibility.py::test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only",
                "test_need_a_sub_eligibility.py::test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof",
            ],
        },
        {
            "id": "MUT-MG-SUB-CURSOR-CONTRACT",
            "source_id": "need-a-sub-service",
            "module": "backend.services.need_a_sub_post_service",
            "protected_requirement": "My Games Need a Sub cursors are encoded, decoded, validated, and bound to the need-a-sub domain, requested view, and sort direction.",
            "symbols": [
                "MY_NEED_A_SUB_CURSOR_DOMAIN",
                "MY_NEED_A_SUB_VALID_VIEWS",
                "encode_my_need_a_sub_cursor",
                "decode_my_need_a_sub_cursor",
                "validate_my_need_a_sub_cursor_context",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_endpoints_reject_invalid_view",
                "test_pagination_and_card_data.py::test_my_games_invalid_cursor_payloads_return_client_error",
                "test_pagination_and_card_data.py::test_my_games_cursors_are_bound_to_domain_and_view",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
            ],
        },
        {
            "id": "MUT-MG-SUB-CURSOR-FILTER",
            "source_id": "need-a-sub-service",
            "module": "backend.services.need_a_sub_post_service",
            "protected_requirement": "My Games Need a Sub pagination applies stable starts_at, created_at, and id cursor ordering without duplicates or omissions.",
            "symbols": [
                "build_my_need_a_sub_cursor_filter",
                "parse_sub_post_card_cursor_datetime",
                "parse_sub_post_card_cursor_uuid",
            ],
            "test_refs": [
                "test_api_contract.py::test_my_games_empty_response_shape_and_default_limit",
                "test_api_contract.py::test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max",
                "test_pagination_and_card_data.py::test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates",
                "test_pagination_and_card_data.py::test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains",
                "test_pagination_and_card_data.py::test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates",
            ],
        },
    ],
}
