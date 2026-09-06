import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { build, preview, loadConfigFromFile, type PreviewServer } from 'vite';

let server: PreviewServer;
let outputDirectory: string;
let fixtureUrl: string;

test.beforeAll(async () => {
  const loaded = await loadConfigFromFile(
    { command: 'serve', mode: 'test' },
    path.resolve(__dirname, '../../vite.config.ts')
  );
  outputDirectory = await mkdtemp(path.join(tmpdir(), 'books-report-table-'));
  const config = {
    ...loaded!.config,
    configFile: false,
    logLevel: 'error' as const,
    build: {
      ...loaded!.config.build,
      outDir: outputDirectory,
      rollupOptions: {
        input: path.resolve(__dirname, 'fixtures/report-table.html'),
      },
    },
    preview: { host: '127.0.0.1', port: 0, proxy: {} },
  } as const;
  await build(config);
  server = await preview(config);
  fixtureUrl = `${server.resolvedUrls!.local[0]}tests/ui/fixtures/report-table.html`;
});

test.afterAll(async () => {
  if (server)
    await new Promise<void>((resolve) =>
      server.httpServer.close(() => resolve())
    );
  if (outputDirectory)
    await rm(outputDirectory, { recursive: true, force: true });
});

test.beforeEach(async ({ page }) => {
  await page.goto(fixtureUrl);
  await expect(page.getByRole('columnheader', { name: /^Item/ })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
});

test('defaults show complete timestamps and more of item names in compact rows', async ({
  page,
}) => {
  const row = page.locator('[data-slot="list-row"]').first();
  const date = row
    .getByRole('cell')
    .nth(1)
    .locator('[data-report-text] > span');
  expect(await date.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true
  );
  expect(await columnWidth(page, 'Item')).toBeGreaterThan(
    await columnWidth(page, 'Quantity')
  );
  expect((await row.boundingBox())!.height).toBe(48);
  await handle(page, 'Item').hover();
  await page.screenshot({ path: test.info().outputPath('report-columns.png') });
});

test('only clipped text opens a hoverable tooltip with focus and Escape support', async ({
  page,
}) => {
  const text = itemText(page);
  const value = await text.textContent();
  const tooltip = page.locator('[data-slot="bubble"]');
  await text.hover();
  await expect(tooltip).toHaveText(value!);
  await tooltip.hover();
  await expect(tooltip).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(tooltip).toBeHidden();
  await page.mouse.move(0, 0);
  await text.focus();
  await expect(tooltip).toHaveText(value!);
  await page.keyboard.press('Escape');
  await expect(tooltip).toBeHidden();
  const location = page
    .getByRole('cell', { name: 'Retail Floor', exact: true })
    .first();
  await location.hover();
  await expect(location.locator('[tabindex="0"]')).toHaveCount(0);
  await expect(tooltip).toBeHidden();
  await text.hover();
  await expect(tooltip).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath('overflow-tooltip.png'),
  });
});

test('dragging keeps headers and rows aligned and restores widths after reload', async ({
  page,
}) => {
  const initial = await columnWidth(page, 'Item');
  await dragColumn(page, 'Item', 110);
  await expect.poll(() => columnWidth(page, 'Item')).toBe(initial + 110);
  const cell = page
    .locator('[data-slot="list-row"]')
    .first()
    .getByRole('cell')
    .nth(2);
  expect((await cell.boundingBox())!.width).toBe(initial + 110);
  await page.reload();
  await expect.poll(() => columnWidth(page, 'Item')).toBe(initial + 110);

  await page.evaluate(() => (window as any).reportFixture.switchReport());
  await expect.poll(() => columnWidth(page, 'Item')).toBe(initial);
});

test('double-click fits values from other pages and removes unnecessary tooltips', async ({
  page,
}) => {
  await handle(page, 'Item').dblclick();
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  const text = itemText(page);
  await expect(text).toContainText('Rechargeable Battery');
  expect(await text.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true
  );
  await expect(text).not.toHaveAttribute('tabindex', '0');
  await page.reload();
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  expect(
    await itemText(page).evaluate((el) => el.scrollWidth <= el.clientWidth)
  ).toBe(true);
});

test('keyboard resizing respects minimum width, fits content and reverses in RTL', async ({
  page,
}) => {
  const initial = await columnWidth(page, 'Item');
  await handle(page, 'Item').focus();
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => columnWidth(page, 'Item')).toBe(initial + 8);
  await page.keyboard.press('Shift+ArrowLeft');
  await expect.poll(() => columnWidth(page, 'Item')).toBe(initial - 32);
  await dragColumn(page, 'Item', -400);
  await expect.poll(() => columnWidth(page, 'Item')).toBe(48);
  await handle(page, 'Item').press('Enter');
  expect(
    await itemText(page).evaluate((el) => el.scrollWidth <= el.clientWidth)
  ).toBe(true);

  await page.evaluate(() => {
    document.documentElement.dir = 'rtl';
    (window as any).reportFixture.direction.value = 'rtl';
  });
  const fitted = await columnWidth(page, 'Item');
  await handle(page, 'Item').press('ArrowLeft');
  await expect.poll(() => columnWidth(page, 'Item')).toBe(fitted + 8);
  await dragColumn(page, 'Item', -40);
  await expect.poll(() => columnWidth(page, 'Item')).toBe(fitted + 48);
});

test('column preferences survive optional column changes and invalid saved data', async ({
  page,
}) => {
  await dragColumn(page, 'Serial Number', 60);
  const width = await columnWidth(page, 'Serial Number');
  await page.evaluate(() => {
    const report = (window as any).reportFixture.state.report;
    const index = report.columns.findIndex(
      (column: any) => column.fieldname === 'batch'
    );
    report.columns.splice(index, 1);
    report.reportData.forEach((row: any) => row.cells.splice(index, 1));
  });
  expect(await columnWidth(page, 'Serial Number')).toBe(width);
  await handle(page, 'Serial Number').press('Enter');
  expect(await columnWidth(page, 'Serial Number')).toBeGreaterThan(width);
  await page.evaluate(() => {
    localStorage.setItem('books:report-column-widths:stock-ledger', '{invalid');
  });
  await page.reload();
  await expect.poll(() => columnWidth(page, 'Item')).toBe(240);
});

test('period columns resize independently in financial statements', async ({
  page,
}) => {
  await page.evaluate(() => (window as any).reportFixture.showBalanceSheet());
  const handles = page.getByRole('separator');
  const first = handles.nth(1);
  const second = handles.nth(2);
  const width = Number(await second.getAttribute('aria-valuenow'));
  await first.press('Shift+ArrowRight');
  await expect(first).toHaveAttribute('aria-valuenow', String(width + 40));
  await expect(second).toHaveAttribute('aria-valuenow', String(width));
  await page.reload();
  await page.evaluate(() => (window as any).reportFixture.showBalanceSheet());
  await expect(first).toHaveAttribute('aria-valuenow', String(width + 40));
  await expect(second).toHaveAttribute('aria-valuenow', String(width));
});

test('tooltips preserve group folding and update when cell values change', async ({
  page,
}) => {
  await page.evaluate(() => {
    const rows = (window as any).reportFixture.state.report.reportData;
    rows[0].isGroup = true;
    rows[0].level = 0;
    rows[1].level = 1;
  });
  const text = itemText(page);
  const rows = page.locator('[data-slot="list-row"]');
  await text.click();
  await expect(rows).toHaveCount(49);
  await text.click();
  await expect(rows).toHaveCount(50);
  await page.evaluate(() => {
    (window as any).reportFixture.state.report.reportData[0].cells[2].value =
      'Tea';
  });
  await expect(text).not.toHaveAttribute('tabindex', '0');
});

function handle(page: Page, name: string) {
  return page.getByRole('separator', {
    name: `Resize ${name} column`,
    exact: true,
  });
}

async function columnWidth(page: Page, name: string) {
  return Number(await handle(page, name).getAttribute('aria-valuenow'));
}

function itemText(page: Page): Locator {
  return page
    .locator('[data-slot="list-row"]')
    .first()
    .getByRole('cell')
    .nth(2)
    .locator('[data-report-text] > span');
}

async function dragColumn(page: Page, name: string, delta: number) {
  const separator = handle(page, name);
  await separator.scrollIntoViewIfNeeded();
  const bounds = (await separator.boundingBox())!;
  const x = bounds.x + bounds.width / 2;
  const y = bounds.y + bounds.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + delta, y, { steps: 4 });
  await page.mouse.up();
}
