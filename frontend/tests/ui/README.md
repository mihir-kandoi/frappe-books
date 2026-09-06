# Browser regression tests

Run the link control tests against a configured local Books test site after `yarn build`.
The tests create documents in browser memory. They do not save fixture records.

```sh
yarn playwright install chromium
yarn test:ui
```

The default site is `http://books-test.localhost:8000` with the local `Administrator` / `admin` login.
Set `BOOKS_TEST_URL`, `BOOKS_TEST_USER`, and `BOOKS_TEST_PASSWORD` to use another test site.
Set `BOOKS_BROWSER_CHANNEL=chrome` to use an installed Chrome browser.

The report table tests build and serve an isolated fixture with in-memory rows.
They do not need a Books site or a separate build:

```sh
yarn test:ui tests/ui/report-table.spec.ts
```
