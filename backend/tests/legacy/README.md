# Legacy Backend Tests

These are valid existing backend tests that have not yet been reorganized into
`pages/` or `shared/`.

Do not add new polished tests here.

When a page or shared rule area is actively polished, move the relevant legacy
coverage into its owner:

- Page-owned behavior goes to `backend/tests/pages/<page>/`.
- Multi-page shared behavior goes to `backend/tests/shared/<rule_area>/`.
- Reusable helper code goes to `backend/tests/support/`.

