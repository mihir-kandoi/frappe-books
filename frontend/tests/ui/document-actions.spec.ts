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
  directory = await mkdtemp(path.join(tmpdir(), 'books-document-actions-'));
  const config = {
    ...loaded!.config,
    configFile: false,
    logLevel: 'error' as const,
    build: {
      ...loaded!.config.build,
      outDir: directory,
      rollupOptions: {
        input: path.resolve(__dirname, 'fixtures/document-actions.html'),
      },
    },
    preview: { host: '127.0.0.1', port: 0, proxy: {} },
  };
  await build(config);
  server = await preview(config);
  url = `${server.resolvedUrls!.local[0]}tests/ui/fixtures/document-actions.html`;
});

test.afterAll(async () => {
  if (server)
    await new Promise<void>((resolve) => server.httpServer.close(() => resolve()));
  if (directory) await rm(directory, { recursive: true, force: true });
});

test.beforeEach(async ({ page }) => {
  await page.goto(url);
  await page.getByRole('button', { name: 'Save', exact: true }).waitFor();
});

for (const action of ['Save', 'Submit']) {
  test(`${action} failure closes the confirmation and allows correction and retry`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await prepareAction(page, action);
    await page.evaluate(() => ((window as any).documentActions.state.fail = true));
    await page.getByRole('button', { name: action, exact: true }).click();
    await page.getByRole('button', { name: 'Yes', exact: true }).click();

    const error = page.getByRole('dialog', { name: 'Error', exact: true });
    await expect(error).toContainText('Write rejected');
    await expect(page.getByRole('dialog', { includeHidden: true })).toHaveCount(1);
    await error.getByRole('button', { name: 'Okay', exact: true }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('button', { name: action, exact: true })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Value' })).toHaveValue('Unsaved edit');
    expect(await readState(page)).toMatchObject({
      result: false,
      calls: 1,
      dirty: action === 'Save',
      inserted: action === 'Submit',
      submitted: false,
    });
    await expect(page.getByText('Dialog record saved', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Dialog record submitted', { exact: true })).toHaveCount(0);

    await page.evaluate(async () => {
      const { doc, state } = (window as any).documentActions;
      state.fail = false;
      await doc.set('value', 'Corrected edit');
    });
    await confirmAction(page, 'Save');
    if (action === 'Submit') await confirmAction(page, 'Submit');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(await readState(page)).toMatchObject({
      result: true,
      dirty: false,
      inserted: true,
      submitted: action === 'Submit',
      value: 'Corrected edit',
    });
    expect(errors).toEqual([]);
  });

  for (const dismiss of ['No', 'Escape']) {
    test(`${dismiss} cancels ${action} without writing`, async ({ page }) => {
      await prepareAction(page, action);
      await page.getByRole('button', { name: action, exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      if (dismiss === 'Escape') await page.keyboard.press('Escape');
      else await page.getByRole('button', { name: 'No', exact: true }).click();
      await expect(page.getByRole('dialog')).toHaveCount(0);
      expect(await readState(page)).toMatchObject({ result: false, calls: 0 });
    });
  }
}

test('a pending save keeps the confirmation busy and performs one write', async ({ page }) => {
  await page.evaluate(() => ((window as any).documentActions.state.pending = true));
  await confirmAction(page, 'Save');
  await expect(page.getByRole('button', { name: 'No', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Yes', exact: true })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(await readState(page)).toMatchObject({ calls: 1, result: null });
  await page.evaluate(() => (window as any).documentActions.release());
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(await readState(page)).toMatchObject({ calls: 1, result: true, dirty: false });
});

async function prepareAction(page: Page, action: string) {
  if (action !== 'Submit') return;
  await page.evaluate(() => {
    const { doc } = (window as any).documentActions;
    doc._notInserted = false;
    doc._dirty = false;
  });
}

async function confirmAction(page: Page, action: string) {
  await page.getByRole('button', { name: action, exact: true }).click();
  await page.getByRole('button', { name: 'Yes', exact: true }).click();
}

async function readState(page: Page) {
  return page.evaluate(() => {
    const { doc, state } = (window as any).documentActions;
    return {
      ...state,
      dirty: doc.dirty,
      inserted: doc.inserted,
      submitted: !!doc.submitted,
      value: doc.value,
    };
  });
}
