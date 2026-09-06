import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DateTime } from 'luxon';
import {
  makeFyo,
  BalanceSheet,
  ProfitAndLoss,
  getJsonData,
  getCsvData,
  matchesStatus,
} from './helpers/accounting.mjs';

test('CSV and JSON retain hidden groups and visible leaf amounts', async () => {
  const fyo = await makeFyo();
  const report = {
    fyo,
    reportName: 'balance-sheet',
    filters: [],
    columns: [
      { fieldname: 'account', label: 'Account' },
      { fieldname: 'balance', label: 'Balance' },
    ],
    reportData: [
      {
        isGroup: true,
        cells: [
          { value: 'Assets', rawValue: 'Assets' },
          { value: '', rawValue: 123 },
        ],
      },
      {
        isGroup: false,
        cells: [
          { value: 'Cash', rawValue: 'Cash' },
          { value: '123', rawValue: 123 },
        ],
      },
    ],
  };
  for (const precision of [0, 2]) {
    fyo.singles.SystemSettings.displayPrecision = precision;
    assert.deepEqual(JSON.parse(getJsonData(report)).rows, [
      { Account: 'Assets', Balance: '' },
      { Account: 'Cash', Balance: '123' },
    ]);
    assert.match(getCsvData(report), /Cash,123/);
    assert.doesNotMatch(getCsvData(report), /Assets,123/);
  }
});

test('balance sheets include opening balances while P&L shows each period', async () => {
  const fyo = await makeFyo();
  const ranges = [2023, 2024].map((year) => ({
    fromDate: DateTime.local(year, 1, 1),
    toDate: DateTime.local(year + 1, 1, 1),
  }));
  const entries = [
    { account: 'Cash', date: new Date('2022-01-01'), debit: 100 },
    { account: 'Cash', date: new Date('2023-01-01'), debit: 50 },
    { account: 'Cash', date: new Date('2024-01-01'), credit: 20 },
    { account: 'Cash', date: new Date('2025-01-01'), debit: 999 },
  ];
  const report = new BalanceSheet(fyo);
  report._dateRanges = ranges;
  report.accountMap = { Cash: { rootType: 'Asset' } };
  const values = (
    await report._getGroupedByDateRanges(new Map([['Cash', entries]]))
  ).get('Cash');
  assert.deepEqual(
    ranges.map((range) => values.get(range).balance),
    [150, 130]
  );
  report.toDate = '2024-12-31';
  assert.deepEqual((await report._getQueryFilters()).date, ['<', '2025-01-01']);

  const profit = new ProfitAndLoss(fyo);
  profit._dateRanges = ranges;
  profit.accountMap = { Sales: { rootType: 'Income' } };
  const income = [2023, 2024].map((year, i) => ({
    account: 'Sales',
    date: new Date(`${year}-02-01`),
    credit: (i + 1) * 100,
  }));
  const periods = (
    await profit._getGroupedByDateRanges(new Map([['Sales', income]]))
  ).get('Sales');
  assert.deepEqual(
    ranges.map((range) => periods.get(range).balance),
    [100, 200]
  );
});

test('computed filters work without rendered rows, for every offered operator', async () => {
  const fyo = await makeFyo();
  const row = {
    schema: fyo.schemaMap.JournalEntry,
    submitted: true,
    cancelled: true,
  };
  for (const [filter, expected] of [
    [['like', 'can'], true],
    [['not like', 'can'], false],
    [['=', 'Cancelled'], true],
    [['!=', 'Submitted'], true],
    [['>', 'a'], true],
    [['<', 'a'], false],
    [['is null', ''], false],
    [['is not null', ''], true],
  ])
    assert.equal(matchesStatus(row, filter), expected, JSON.stringify(filter));
  assert.throws(() => matchesStatus(row, ['invalid', '']), /Unsupported/);
});

for (const quantity of [3, -3]) {
  test(`flat line discounts agree with invoice totals for quantity ${quantity}`, async () => {
    const { invoice, row, fyo } = await makeInvoice(quantity);
    row.setItemDiscountAmount = true;
    row.itemDiscountAmount = fyo.pesa(50);
    row.itemDiscountedTotal = await row.formulas.itemDiscountedTotal.formula();
    row.itemTaxedTotal = await row.formulas.itemTaxedTotal.formula();
    assert.equal(row.itemDiscountedTotal.float, Math.sign(quantity) * 250);
    assert.equal(
      invoice.getItemDiscountAmount().float,
      Math.sign(quantity) * 50
    );
    assert.equal(invoice.getGrandTotal().float, Math.sign(quantity) * 250);
    const rate = await row.formulas.rate.formula('itemDiscountedTotal');
    assert.equal(rate.float, 100);
  });
}

test('manual rates, including zero, survive quantity changes and formula refresh', async () => {
  const { row, fyo } = await makeInvoice(3);
  for (const rate of [75, 0]) {
    await row.set('rate', fyo.pesa(rate));
    assert.equal(row.isManualRate, true);
    await row.set('quantity', 4);
    await row.runFormulas();
    assert.equal(row.rate.float, rate);
  }
});

test('editing totals still calculates a new manual rate', async () => {
  const { row, fyo } = await makeInvoice(3);
  await row.set('rate', fyo.pesa(100));
  row.setItemDiscountAmount = true;
  row.itemDiscountAmount = fyo.pesa(50);
  await row.set('itemDiscountedTotal', fyo.pesa(400));
  assert.equal(row.rate.float, 150);
});

test('currency formatting uses exactly the configured precision', async () => {
  const fyo = await makeFyo();
  fyo.singles.SystemSettings.displayPrecision = 0;
  assert.equal(fyo.format(fyo.pesa('123.99'), 'Currency'), '124');
});

async function makeInvoice(quantity) {
  const fyo = await makeFyo();
  fyo.getValue = async (_schema, _name, field) =>
    field === 'rate' ? fyo.pesa(100) : undefined;
  const invoice = fyo.doc.getNewDoc('SalesInvoice', {
    currency: 'USD',
    exchangeRate: 1,
    returnAgainst: quantity < 0 ? 'original' : undefined,
    items: [
      {
        item: 'Service',
        quantity,
        rate: fyo.pesa(100),
        amount: fyo.pesa(quantity * 100),
      },
    ],
  });
  invoice.netTotal = fyo.pesa(quantity * 100);
  return { invoice, row: invoice.items[0], fyo };
}

test('automatic rates refresh while manual rates survive exchange changes', async () => {
  const { row, fyo } = await makeInvoice(3);
  fyo.getValue = async (_schema, _name, field) =>
    field === 'rate' ? fyo.pesa(200) : undefined;
  await row.set('quantity', 4);
  assert.equal(row.rate.float, 200);
  await row.set('rate', fyo.pesa(75));
  assert.equal((await row.formulas.rate.formula('exchangeRate')).float, 75);
  assert.equal((await row.formulas.rate.formula('priceList')).float, 200);
  assert.equal(row.isManualRate, false);
});
