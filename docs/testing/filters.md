# Filter coverage

The list filter supports eight conditions: Is, Is Not, Contains, Does Not Contain,
Greater Than, Less Than, Is Empty, and Is Not Empty. Rules use AND, including
multiple rules on the same field. Clear removes user rules and preserves implicit
and route restrictions. Apply, Enter in text inputs, Escape, and outside clicks
apply complete rules. Invalid query values keep the editor open with an error.
Value controls follow [Frappe's field metadata approach](https://github.com/frappe/frappe/blob/develop/frappe/public/js/frappe/ui/filters/filter.js).
Select fields show all configured labels and submit their stored values. Computed
Status fields supply their own choices. Select and Link fields default to Is.
Link equality filters offer record search. Contains uses text. Dynamic Links offer
record search after an equality filter selects their reference type. Changing that
type clears dependent values. Autocomplete fields retain suggestions and typed input.
Date and Datetime fields use the native Frappe UI calendar and date-time pickers.
Enter commits a picker value; Escape closes the nested picker first. Both leave
the filter editor open. Empty conditions do not show a value picker.

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
as empty. Pickers serialize Date values as `YYYY-MM-DD` and Datetime values as
`YYYY-MM-DD HH:mm:ss`. Selecting only a date in an empty Datetime picker uses
midnight. Picker values can also be typed or cleared.
Check fields offer Is / Is Not with Yes / No. Numeric and date fields omit text
conditions. Document numbers, net and grand totals, audit dates and users, and
Submitted/Cancelled flags are available even when their form fields are read-only.
Document number and Number Series query separate stored fields. Other read-only
or computed values need an explicit filter opt-in. Table, attachment, button,
secret, and internal metadata fields remain excluded.

Run frontend unit tests with `yarn --cwd frontend test`. Run browser tests with
`yarn --cwd frontend test:ui tests/ui/filter-dropdown.spec.ts tests/ui/filter-value-input.spec.ts`. Set
`BOOKS_BROWSER_CHANNEL=chrome` to use an installed Chrome; otherwise install
Playwright's Chromium with `yarn --cwd frontend playwright install chromium`.

The browser/database cases require `BOOKS_FILTER_TEST_BENCH` (an absolute
bench path) and `BOOKS_FILTER_TEST_SITE` (a dedicated site with `allow_tests=1`).
They invoke `bench --site … execute` using arguments, load this checkout through
`PYTHONPATH`, and roll back fixture records. They do not run without these variables.
Database tests run with `bench --site <test-site> run-tests --module
frappe_books.tests.test_filters` from the bench directory. The existing CI database
matrix runs both layers on SQLite, MariaDB, and PostgreSQL.

This matrix covers the supported behaviors and input classes. It does not claim
to enumerate every possible string, custom schema, locale, or database collation.
