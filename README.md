Complete all 10 stubs to make the prototype fully functional. Each file contains detailed `TODO` comments with implementation steps and API references.

| # | File | What to implement | Difficulty |
|---|------|------------------|------------|
| 1 | `backend/app/services/github_service.py` | Implement `_push_file_changes_to_branch()` — create Git blobs, build a tree, commit to a new branch via GitHub Git Data API, then open a real PR | ★★★ |
| 2 | `backend/app/api/routes.py` | Implement `POST /webhook/push` — parse real GitHub push-event JSON, validate HMAC signature, extract commit SHA and repo, auto-trigger analysis | ★★ |
| 3 | `backend/app/services/vector_index.py` | Implement `embed_with_model()` — replace TF-IDF hashing with real sentence embeddings via OpenAI `text-embedding-3-small` or `sentence-transformers` | ★★★ |
| 4 | `backend/app/workers/analysis_worker.py` | Implement `PersistenceLayer` — replace in-memory `_jobs` dict with SQLite or Redis so job history survives restarts | ★★ |
| 5 | `backend/app/mocks/mock_interfaces.py` | Implement `fetch_real_read_counts()` — replace hardcoded page-view counts with GitHub Traffic API or a real analytics source | ★ |
| 6 | `backend/app/services/github_fetcher.py` | Implement `fetch_gitlab_commits()` and `fetch_azuredevops_commits()` — add GitLab and Azure DevOps as supported git providers | ★★ |
| 7 | `backend/app/services/notifier.py` | Implement `send_slack_message()` and `send_teams_message()` — post Block Kit / Adaptive Card alerts when high-traffic docs drift above threshold | ★★ |
| 8 | `backend/app/services/doc_debt.py` | Implement `_get_symbol_author()` and `generate_doc_debt_report()` — attribute stale docs to the engineer who last changed the referenced code via git blame or GitHub API | ★★★ |
| 9 | `backend/app/services/doc_executor.py` | Implement `execute_code_block()` — run fenced code blocks in a sandboxed subprocess with timeout, return pass/fail; wire into `verify_doc_examples()` | ★★★ |
| 10 | `backend/app/services/auto_merge.py` | Implement `score_rewrite_confidence()`, `_check_ci_status()`, and `merge_pr()` — auto-merge low-risk doc PRs when confidence is high and CI passes | ★★★ |