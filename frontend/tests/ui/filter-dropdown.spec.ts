import { expect, test, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { build, preview, loadConfigFromFile, type PreviewServer } from 'vite';

let server: PreviewServer;
let directory: string;
let url: string;

test.beforeAll(async () => {
  const loaded = await loadConfigFromFile(
    { command: 'serve', mode: 'test' },
    path.resolve(__dirname, '../../vite.config.ts')
  );
  directory = await mkdtemp(path.join(tmpdir(), 'books-filter-ui-'));
  const config = {
    ...loaded!.config,
    configFile: false,
    logLevel: 'error' as const,
    build: {
      ...loaded!.config.build,
      outDir: directory,
      rollupOptions: {
        input: path.resolve(__dirname, 'fixtures/filter-dropdown.html'),
      },
    },
    preview: { host: '127.0.0.1', port: 0, proxy: {} },
  };
  await build(config);
  server = await preview(config);
  url = `${server.resolvedUrls!.local[0]}tests/ui/fixtures/filter-dropdown.html`;
});

test.afterAll(async () => {
  if (server)
    await new Promise<void>((resolve) =>
      server.httpServer.close(() => resolve())
    );
  if (directory) await rm(directory, { recursive: true, force: true });
});

test.beforeEach(async ({ page }) => {
  await page.goto(url);
  await page.getByRole('button', { name: 'Filter', exact: true }).click();
  await page.evaluate(() => document.fonts.ready);
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1024, height: 640 },
  { width: 390, height: 560 },
]) {
  test(`filter rows and footer fit at ${viewport.width} × ${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    const panel = page.getByRole('region', { name: 'Filters', exact: true });
    const add = panel.getByRole('button', {
      name: 'Add a filter',
      exact: true,
    });
    expect((await add.boundingBox())!.height).toBe(32);
    await add.click();
    const row = panel.getByRole('group', { name: 'Filter 1', exact: true });
    for (const control of await row.locator('button, input').all()) {
      await expect(control).toBeInViewport();
      const bounds = (await control.boundingBox())!;
      const outer = (await panel.boundingBox())!;
      expect(bounds.x - outer.x).toBeGreaterThanOrEqual(12);
      expect(
        outer.x + outer.width - bounds.x - bounds.width
      ).toBeGreaterThanOrEqual(12);
    }
    await page.screenshot({
      animations: 'disabled',
      path: test.info().outputPath('single-filter.png'),
    });
    for (let i = 0; i < 12; i++) await add.click();
    await expect(panel.locator('footer')).toBeInViewport();
    await expect(
      panel.getByRole('button', { name: 'Apply', exact: true })
    ).toBeInViewport();
    const bounds = (await panel.boundingBox())!;
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height);
    expect(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
      true
    );
    await page.screenshot({
      animations: 'disabled',
      path: test.info().outputPath('many-filters.png'),
    });
    const lastValue = panel
      .getByRole('textbox', { name: 'Value', exact: true })
      .last();
    await lastValue.scrollIntoViewIfNeeded();
    await expect(lastValue).toBeInViewport();
  });
}

test('selecting a condition closes its menu and Apply preserves the value', async ({
  page,
}) => {
  const panel = page.getByRole('region', { name: 'Filters', exact: true });
  await panel
    .getByRole('button', { name: 'Add a filter', exact: true })
    .click();
  await panel.getByRole('combobox', { name: 'Condition', exact: true }).click();
  await page.getByRole('option', { name: 'Is', exact: true }).click();
  await expect(page.getByRole('listbox')).toBeHidden();
  await expect(panel).toBeVisible();
  await panel.getByRole('textbox', { name: 'Value', exact: true }).fill('Paid');
  await panel.getByRole('button', { name: 'Apply', exact: true }).click();
  await expect(panel).toBeHidden();
  expect(await appliedFilters(page)).toEqual({ status: ['=', 'Paid'] });
  const trigger = page.getByRole('button', {
    name: '1 filter applied',
    exact: true,
  });
  await expect(trigger).toBeFocused();
  await trigger.press('Enter');
  await expect(
    panel.getByRole('textbox', { name: 'Value', exact: true })
  ).toHaveValue('Paid');
  await expect(
    panel.getByRole('combobox', { name: 'Field', exact: true })
  ).toBeFocused();
  await expect(page.locator('[data-slot="bubble"]')).toBeHidden();
  await panel.getByRole('button', { name: 'Clear', exact: true }).click();
  await expect(panel.getByText('No filters selected')).toBeVisible();
  expect(await appliedFilters(page)).toEqual({});
});

test('remaining filters can be edited and removed after an incomplete row is discarded', async ({
  page,
}) => {
  const panel = page.getByRole('region', { name: 'Filters', exact: true });
  const add = panel.getByRole('button', { name: 'Add a filter', exact: true });
  await add.click();
  await add.click();
  await panel
    .getByRole('textbox', { name: 'Value', exact: true })
    .nth(1)
    .fill('Paid');
  await panel.getByRole('button', { name: 'Apply', exact: true }).click();
  await page
    .getByRole('button', { name: '1 filter applied', exact: true })
    .click();
  await expect(panel.getByRole('group')).toHaveCount(1);
  await panel
    .getByRole('textbox', { name: 'Value', exact: true })
    .fill('Unpaid');
  await panel
    .getByRole('textbox', { name: 'Value', exact: true })
    .press('Enter');
  await expect(panel).toBeHidden();
  expect(await appliedFilters(page)).toEqual({ status: ['like', '%Unpaid%'] });
  await page
    .getByRole('button', { name: '1 filter applied', exact: true })
    .click();
  await panel
    .getByRole('button', { name: 'Remove filter 1', exact: true })
    .click();
  await expect(panel.getByText('No filters selected')).toBeVisible();
  await page.keyboard.press('Escape');
  expect(await appliedFilters(page)).toEqual({});
});

async function appliedFilters(page: Page) {
  return page.evaluate(() => (window as any).filterFixture.state.applied);
}

const operatorCases = [
  ['Is', '=', 'Paid', 20],
  ['Is Not', '!=', 'Paid', 40],
  ['Contains', 'like', 'paid', 60],
  ['Does Not Contain', 'not like', 'partly', 40],
  ['Greater Than', '>', 'Paid', 40],
  ['Less Than', '<', 'Paid', 0],
  ['Is Empty', 'is null', null, 0],
  ['Is Not Empty', 'is not null', null, 60],
] as const;
for (const [label, operator, value, count] of operatorCases) {
  test(`status ${label} produces the expected list records`, async ({
    page,
  }) => {
    const panel = page.getByRole('region', { name: 'Filters', exact: true });
    await panel
      .getByRole('button', { name: 'Add a filter', exact: true })
      .click();
    await choose(page, 'Condition', label);
    if (value !== null)
      await panel
        .getByRole('textbox', { name: 'Value', exact: true })
        .fill(value);
    else
      await expect(
        panel.getByRole('textbox', { name: 'Value', exact: true })
      ).toHaveCount(0);
    await panel.getByRole('button', { name: 'Apply', exact: true }).click();
    await expect
      .poll(() =>
        page.evaluate(
          () => (window as any).filterFixture.list.value.data.length
        )
      )
      .toBe(count);
    expect(await appliedFilters(page)).toEqual({
      status: [operator, operator.includes('like') ? `%${value}%` : value],
    });
    await page
      .getByRole('button', { name: '1 filter applied', exact: true })
      .click();
    await expect(
      panel.getByRole('combobox', { name: 'Condition', exact: true })
    ).toHaveText(label);
  });
}

test('Is Empty on User Remark hides Value and sends the unary condition', async ({
  page,
}) => {
  await page.evaluate(() => {
    (window as any).filterFixture.state.schemaName = 'JournalEntry';
  });
  await page.getByRole('button', { name: 'Filter', exact: true }).click();
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await choose(page, 'Field', 'User Remark');
  await choose(page, 'Condition', 'Is Empty');
  await expect(
    page.getByRole('textbox', { name: 'Value', exact: true })
  ).toHaveCount(0);
  await page.screenshot({
    path: test.info().outputPath('empty-remark.png'),
    animations: 'disabled',
  });
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  expect(await appliedFilters(page)).toEqual({ userRemark: ['is null', null] });
});

test('changing field types resets values and restricts operators; invalid dates stay open', async ({
  page,
}) => {
  await page.evaluate(() => {
    (window as any).filterFixture.state.schemaName = 'JournalEntry';
  });
  await page.getByRole('button', { name: 'Filter', exact: true }).click();
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await page.getByRole('textbox', { name: 'Value', exact: true }).fill('Paid');
  await choose(page, 'Field', 'Date');
  const input = page.getByRole('textbox', { name: 'Value', exact: true });
  await expect(input).toHaveValue('');
  await page.getByRole('combobox', { name: 'Condition', exact: true }).click();
  await expect(
    page.getByRole('option', { name: 'Contains', exact: true })
  ).toHaveCount(0);
  await page.getByRole('option', { name: 'Is', exact: true }).click();
  await input.fill('2023-02-29');
  await input.press('Enter');
  await expect(page.getByRole('alert')).toContainText('Enter a valid date');
  expect(await appliedFilters(page)).toEqual({});
  await input.fill('2024-02-29');
  await input.press('Enter');
  await expect(
    page.getByRole('region', { name: 'Filters', exact: true })
  ).toBeHidden();
  expect(await appliedFilters(page)).toEqual({ date: ['=', '2024-02-29'] });
});

test('same-field conditions survive apply, reopen, edit, remove, refresh and clear', async ({
  page,
}) => {
  const panel = page.getByRole('region', { name: 'Filters', exact: true });
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await page.getByRole('textbox', { name: 'Value', exact: true }).fill('paid');
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await choose(page, 'Condition', 'Is Not', 1);
  await page
    .getByRole('textbox', { name: 'Value', exact: true })
    .nth(1)
    .fill('Paid');
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  expect(await appliedFilters(page)).toEqual({
    status: ['like', '%paid%', '!=', 'Paid'],
  });
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).filterFixture.list.value.data.length)
    )
    .toBe(40);
  await page.evaluate(async () => {
    await (window as any).filterFixture.list.value.updateData();
  });
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).filterFixture.list.value.data.length)
    )
    .toBe(40);
  await page
    .getByRole('button', { name: '2 filters applied', exact: true })
    .click();
  await panel
    .getByRole('button', { name: 'Remove filter 1', exact: true })
    .click();
  await panel
    .getByRole('textbox', { name: 'Value', exact: true })
    .fill('Unpaid');
  await page.keyboard.press('Escape');
  expect(await appliedFilters(page)).toEqual({ status: ['!=', 'Unpaid'] });
  await page
    .getByRole('button', { name: '1 filter applied', exact: true })
    .click();
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  expect(await appliedFilters(page)).toEqual({});
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).filterFixture.list.value.data.length)
    )
    .toBe(60);
});

test('filtering on page two returns to the first page of matching records', async ({
  page,
}) => {
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(
    page.getByRole('spinbutton', { name: 'Page number', exact: true })
  ).toHaveValue('2');
  await page.getByRole('button', { name: 'Filter', exact: true }).click();
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await choose(page, 'Condition', 'Is');
  await page.getByRole('textbox', { name: 'Value', exact: true }).fill('Paid');
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  await expect(
    page.getByRole('spinbutton', { name: 'Page number', exact: true })
  ).toHaveValue('1');
  await expect(page.getByText('INV-1', { exact: true })).toBeVisible();
});

async function choose(page: Page, control: string, option: string, index = 0) {
  await page
    .getByRole('combobox', { name: control, exact: true })
    .nth(index)
    .click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

for (const [field, value, expected] of [
  ['Rate', '0', { rate: ['=', 0] }],
  ['Rate', '-12.5', { rate: ['=', -12.5] }],
  ['Track Inventory', 'No', { trackItem: ['=', '0'] }],
  ['Track Inventory', 'Yes', { trackItem: ['=', '1'] }],
] as const) {
  test(`${field} accepts ${value} and counts the applied filter`, async ({
    page,
  }) => {
    await page.evaluate(() => {
      (window as any).filterFixture.state.schemaName = 'Item';
    });
    await page.getByRole('button', { name: 'Filter', exact: true }).click();
    await page
      .getByRole('button', { name: 'Add a filter', exact: true })
      .click();
    await choose(page, 'Field', field);
    await choose(page, 'Condition', 'Is');
    if (field === 'Track Inventory') await choose(page, 'Value', value);
    else
      await page
        .getByRole('textbox', { name: 'Value', exact: true })
        .fill(value);
    await page.getByRole('button', { name: 'Apply', exact: true }).click();
    const query = await appliedFilters(page);
    const numericExpected = JSON.parse(JSON.stringify(expected));
    if (field === 'Track Inventory')
      numericExpected.trackItem[1] = Number(numericExpected.trackItem[1]);
    expect(query).toEqual(numericExpected);
    await expect(
      page.getByRole('button', { name: '1 filter applied', exact: true })
    ).toBeVisible();
  });
}

test('date and time validation accepts correction and SQL round trips', async ({
  page,
}) => {
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await choose(page, 'Field', 'Date');
  const input = page.getByRole('textbox', { name: 'Value', exact: true });
  await input.fill('2024-02-29');
  await input.press('Enter');
  await expect(page.getByRole('alert')).toContainText('date and time');
  await input.fill('2024-02-29T13:45:00');
  await input.press('Enter');
  await expect(
    page.getByRole('region', { name: 'Filters', exact: true })
  ).toBeHidden();
  expect(await appliedFilters(page)).toEqual({
    date: ['=', '2024-02-29 13:45:00'],
  });
  await page.evaluate(() => {
    const f = (window as any).filterFixture;
    f.filter.value.setFilter(f.state.applied);
  });
  expect(await appliedFilters(page)).toEqual({
    date: ['=', '2024-02-29 13:45:00'],
  });
});

test('hidden filters survive visible removal and Clear; drafts do not change the badge', async ({
  page,
}) => {
  await page.evaluate(() => {
    const f = (window as any).filterFixture.filter.value;
    f.setFilter({ status: ['!=', 'Cancelled'] }, true);
  });
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await page.getByRole('textbox', { name: 'Value', exact: true }).fill('paid');
  await expect(
    page.getByRole('button', { name: 'Filter', exact: true })
  ).toBeVisible();
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  expect(await appliedFilters(page)).toEqual({
    status: ['!=', 'Cancelled', 'like', '%paid%'],
  });
  await page
    .getByRole('button', { name: '1 filter applied', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Remove filter 1', exact: true })
    .click();
  await page.keyboard.press('Escape');
  expect(await appliedFilters(page)).toEqual({ status: ['!=', 'Cancelled'] });
  await page.getByRole('button', { name: 'Filter', exact: true }).click();
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await page.getByRole('textbox', { name: 'Value', exact: true }).fill('paid');
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  expect(await appliedFilters(page)).toEqual({ status: ['!=', 'Cancelled'] });
});

test('outside click applies changes and zero matches can be cleared', async ({
  page,
}) => {
  await page.getByRole('button', { name: 'Add a filter', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Value', exact: true })
    .fill('missing');
  await page
    .getByRole('heading', { name: 'Sales Invoice', exact: true })
    .click();
  expect(await appliedFilters(page)).toEqual({ status: ['like', '%missing%'] });
  await expect(
    page.getByText('No entries found', { exact: true })
  ).toBeVisible();
  await page
    .getByRole('button', { name: '1 filter applied', exact: true })
    .click();
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  await expect(page.getByText('INV-1', { exact: true })).toBeVisible();
});

const databaseCases = [
  ['Is', 'Beta', ['3']],
  ['Is Not', 'Beta', ['0', '1', '2', '4']],
  ['Contains', 'Alpha', ['2', '4']],
  ['Does Not Contain', 'Alpha', ['0', '1', '3']],
  ['Greater Than', 'Alpha', ['2', '3', '4']],
  ['Less Than', 'Alpha', ['0', '1']],
  ['Is Empty', null, ['0', '1']],
  ['Is Not Empty', null, ['2', '3', '4']],
] as const;
for (const [condition, value, matches] of databaseCases) {
  test(`Frappe database: User Remark ${condition} returns matching records`, async ({
    page,
  }) => {
    await useFilterDatabase(page);
    await page.getByRole('button', { name: 'Filter', exact: true }).click();
    await page
      .getByRole('button', { name: 'Add a filter', exact: true })
      .click();
    await choose(page, 'Field', 'User Remark');
    await choose(page, 'Condition', condition);
    if (value !== null)
      await page
        .getByRole('textbox', { name: 'Value', exact: true })
        .fill(value);
    await page.getByRole('button', { name: 'Apply', exact: true }).click();
    await expect
      .poll(() =>
        page.evaluate(() =>
          (window as any).filterFixture.list.value.data
            .map((row: any) => row.referenceNumber)
            .sort()
        )
      )
      .toEqual(matches);
    for (const index of matches)
      await expect(
        page.getByText(new RegExp(`^Filter ${index} `))
      ).toBeVisible();
  });
}

async function useFilterDatabase(page: Page, schemaName = 'JournalEntry') {
  test.skip(
    !process.env.BOOKS_FILTER_TEST_BENCH || !process.env.BOOKS_FILTER_TEST_SITE,
    'Requires an explicit Frappe test bench and site'
  );
  let pending: Promise<unknown> = Promise.resolve();
  await page.route('**/__filter_database_test', async (route) => {
    const result = pending.then(() =>
      promisify(execFile)(
        'bench',
        [
          '--site',
          process.env.BOOKS_FILTER_TEST_SITE!,
          'execute',
          'frappe_books.tests.test_filters.query_filter_fixture',
          '--kwargs',
          JSON.stringify({
            filters: route.request().postData(),
            schema_name: schemaName,
          }),
        ],
        {
          cwd: process.env.BOOKS_FILTER_TEST_BENCH,
          env: {
            ...process.env,
            PYTHONPATH: path.resolve(__dirname, '../../..'),
          },
        }
      )
    );
    pending = result.catch(() => {});
    const { stdout } = await result.catch((error) => {
      throw new Error(`${error.message}\n${error.stdout}\n${error.stderr}`);
    });
    await route.fulfill({ json: JSON.parse(stdout) });
  });
  await page.keyboard.press('Escape');
  await page.evaluate(async (schemaName) => {
    const fixture = (window as any).filterFixture;
    fixture.state.useDatabase = true;
    fixture.state.schemaName = schemaName;
    await fixture.list.value.updateData({});
  }, schemaName);
  await expect
    .poll(() =>
      page.evaluate(() => (window as any).filterFixture.list.value.data.length)
    )
    .toBe(5);
}

const storedFieldCases = [
  ['JournalEntry', 'Entry No', 'Contains', 'Filter 3 ', ['3']],
  ['JournalEntry', 'Number Series', 'Is', 'JV-', ['0', '2', '4']],
  ['JournalEntry', 'Created By', 'Is', 'Administrator', ['0', '2', '4']],
  ['JournalEntry', 'Modified By', 'Is', 'Guest', ['1', '3']],
  [
    'JournalEntry',
    'Created',
    'Greater Than',
    '2024-01-03T12:00:00',
    ['3', '4'],
  ],
  [
    'JournalEntry',
    'Modified',
    'Greater Than',
    '2024-02-03T12:00:00',
    ['3', '4'],
  ],
  ['JournalEntry', 'Submitted', 'Is', 'No', ['0', '3']],
  ['JournalEntry', 'Cancelled', 'Is', 'Yes', ['2']],
  ['SalesInvoice', 'Invoice No', 'Contains', 'Filter invoice 3 ', ['3']],
  ['SalesInvoice', 'Net Total', 'Is', '0', ['0']],
  ['SalesInvoice', 'Grand Total', 'Greater Than', '112', ['2', '3', '4']],
  ['SalesInvoice', 'Base Grand Total', 'Less Than', '448', ['0', '1']],
] as const;
for (const [schema, field, condition, value, matches] of storedFieldCases) {
  test(`stored field ${schema}.${field} returns matching Frappe records`, async ({
    page,
  }) => {
    await useFilterDatabase(page, schema);
    await page.getByRole('button', { name: 'Filter', exact: true }).click();
    await page
      .getByRole('button', { name: 'Add a filter', exact: true })
      .click();
    await choose(page, 'Field', field);
    await choose(page, 'Condition', condition);
    if (field === 'Submitted' || field === 'Cancelled')
      await choose(page, 'Value', value);
    else
      await page
        .getByRole('textbox', { name: 'Value', exact: true })
        .fill(value);
    await page.getByRole('button', { name: 'Apply', exact: true }).click();
    await expect
      .poll(() =>
        page.evaluate(() =>
          (window as any).filterFixture.list.value.data
            .map((row: any) => row.name.match(/^Filter (?:invoice )?(\d) /)[1])
            .sort()
        )
      )
      .toEqual(matches);
  });
}
