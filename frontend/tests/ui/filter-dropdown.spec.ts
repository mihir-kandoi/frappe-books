import { expect, test, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
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
  expect(await appliedFilters(page)).toEqual({ status: ['like', 'Unpaid'] });
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
