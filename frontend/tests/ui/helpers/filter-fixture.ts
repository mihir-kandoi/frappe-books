import { expect, test, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { build, preview, loadConfigFromFile, type PreviewServer } from 'vite';

export function setupFilterFixture() {
  let server: PreviewServer;
  let directory: string;
  let url: string;

  test.beforeAll(async () => {
    const loaded = await loadConfigFromFile(
      { command: 'serve', mode: 'test' },
      path.resolve(__dirname, '../../../vite.config.ts')
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
          input: path.resolve(__dirname, '../fixtures/filter-dropdown.html'),
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
    await page.clock.install({ time: new Date('2024-02-15T12:00:00') });
    await page.goto(url);
    await page.getByRole('button', { name: 'Filter', exact: true }).click();
    await page.evaluate(() => document.fonts.ready);
  });
}

export async function choose(
  page: Page,
  control: string,
  option: string,
  index = 0
) {
  await page
    .getByRole('combobox', { name: control, exact: true })
    .nth(index)
    .click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

export async function setValue(page: Page, value: string, index = 0) {
  const row = page
    .getByRole('region', { name: 'Filters', exact: true })
    .getByRole('group')
    .nth(index);
  await expect(row.getByLabel('Value', { exact: true })).toBeVisible();
  const select = row.getByRole('combobox', { name: 'Value', exact: true });
  if (await select.count()) {
    await select.click();
    await page.getByRole('option', { name: value, exact: true }).click();
  } else {
    await row.getByRole('textbox', { name: 'Value', exact: true }).fill(value);
  }
}

export async function appliedFilters(page: Page) {
  return page.evaluate(() => (window as any).filterFixture.state.applied);
}
