# Browser regression tests

Run these tests against a configured local Books test site after `yarn build`.
The tests create documents in browser memory. They do not save fixture records.

```sh
yarn playwright install chromium
yarn test:ui
```

The default site is `http://books-test.localhost:8000` with the local `Administrator` / `admin` login.
Set `BOOKS_TEST_URL`, `BOOKS_TEST_USER`, and `BOOKS_TEST_PASSWORD` to use another test site.
Set `BOOKS_BROWSER_CHANNEL=chrome` to use an installed Chrome browser.
