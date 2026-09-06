# Filter coverage

The list filter supports eight conditions: Is, Is Not, Contains, Does Not Contain,
Greater Than, Less Than, Is Empty, and Is Not Empty. Rules use AND, including
multiple rules on the same field. Clear removes user rules and preserves implicit
and route restrictions. Apply, Enter, Escape, and outside clicks apply complete
rules. Invalid values keep the editor open with an error.

| Area | Tests |
| --- | --- |
| Operators and types | All eight conditions across Data, Text, Select, Link, DynamicLink, Color, AutoComplete, Int, Float, Currency, Date, Datetime, and Check, including rejected combinations |
| Values | Blank drafts, NULL, zero, false, negative and decimal numbers, invalid/nonfinite numbers, leap dates, invalid dates, date/time round trips, whitespace, Unicode, quotes, and wildcards |
| Rule state | Same-field ranges, duplicates, contradictory rules, multiple fields, hidden rules, stable removal, clear, reopen, field changes, and applied counts |
| Lists and exports | Computed status labels, repeated status conditions, empty results, refresh, stale requests, pagination, base restrictions, and filtered exports |
| Database | Real result sets for all adapter operators; all 64 pairs of UI conditions; submitted/cancelled combinations; invalid filters and read permissions |
| Browser | Native Frappe UI controls, keyboard and pointer actions, responsive layout, typed inputs, and all eight User Remark conditions through the real database adapter |

Contains adds `%` around the entered text. `%` and `_` retain SQL wildcard
semantics. Is compares the entered value without adding wildcards. Empty checks
use Frappe's `is set` / `is not set` semantics; text NULL and empty strings count
as empty. Date values require `YYYY-MM-DD`; Datetime values also require a time.
Check fields offer Is / Is Not with Yes / No. Numeric and date fields omit text
conditions. Table, attachment, button, and secret fields are excluded.

Run frontend unit tests with `yarn --cwd frontend test`. Run browser tests with
`yarn --cwd frontend test:ui tests/ui/filter-dropdown.spec.ts`. Set
`BOOKS_BROWSER_CHANNEL=chrome` to use an installed Chrome; otherwise install
Playwright's Chromium with `yarn --cwd frontend playwright install chromium`.

The eight browser/database cases require `BOOKS_FILTER_TEST_BENCH` (an absolute
bench path) and `BOOKS_FILTER_TEST_SITE` (a dedicated site with `allow_tests=1`).
They invoke `bench --site … execute` using arguments, load this checkout through
`PYTHONPATH`, and roll back fixture records. They do not run without these variables.
Database tests run with `bench --site <test-site> run-tests --module
frappe_books.tests.test_filters` from the bench directory. The existing CI database
matrix runs both layers on SQLite, MariaDB, and PostgreSQL.

This matrix covers the supported behaviors and input classes. It does not claim
to enumerate every possible string, custom schema, locale, or database collation.
