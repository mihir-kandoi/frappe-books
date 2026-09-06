import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Fyo, getSchemas, models } from './helpers/accounting.mjs';

test('an overallocated duplicate keeps its amount and can save after correction', async () => {
  const { fyo, original, invoice, payment, stored } = await makePayment();

  await assert.rejects(
    payment.sync(),
    /Payment amount cannot exceed 4,90,231\.00/
  );
  assert.equal(payment.amount.float, 910429);
  assert.equal(payment.for[0].amount.float, 910429);
  assert.equal(payment.isSyncing, false);
  assert.equal(stored.has('Payment'), false);

  await payment.set('amount', fyo.pesa(490231));
  await payment.sync();

  assert.equal(payment.amount.float, 490231);
  assert.equal(payment.for[0].amount.float, 490231);
  assert.equal(payment.inserted, true);
  assert.equal(payment.isSubmitted, false);
  assert.notEqual(payment.name, original.name);
  assert.equal(Number(stored.get('Payment').amount), 490231);
  assert.equal(original.amount.float, 910429);
  assert.equal(original.for[0].amount.float, 910429);
  assert.equal(original.isSubmitted, true);
  assert.equal(invoice.outstandingAmount.float, 490231);
});

test('rejecting an amount edit preserves the previous payment and allocation', async () => {
  const { fyo, payment } = await makePayment();
  await payment.set('amount', fyo.pesa(490231));

  await assert.rejects(
    payment.set('amount', fyo.pesa(910429)),
    /Payment amount cannot exceed 4,90,231\.00/
  );

  assert.equal(payment.amount.float, 490231);
  assert.equal(payment.for[0].amount.float, 490231);
});

test('changing an invoice reference refreshes the payment limit', async () => {
  const { fyo, payment } = await makePayment();
  await payment.set('amount', fyo.pesa(490231));
  fyo.doc.getNewDoc('PurchaseInvoice', {
    name: 'OTHER-PI',
    party: payment.party,
    submitted: true,
    outstandingAmount: 1200000,
  });

  await payment.for[0].set('referenceName', 'OTHER-PI');
  await payment.sync();

  assert.equal(payment.amount.float, 1200000);
  assert.equal(payment.for[0].referenceName, 'OTHER-PI');
  assert.equal(payment.inserted, true);
});

test('a changed invoice balance is checked again when editing the amount', async () => {
  const { fyo, invoice, payment } = await makePayment();
  await payment.set('amount', fyo.pesa(490231));
  invoice.outstandingAmount = fyo.pesa(100);

  await assert.rejects(
    payment.set('amount', fyo.pesa(200)),
    /Payment amount cannot exceed 100\.00/
  );
  assert.equal(payment.amount.float, 490231);
});

test('full-payment validation uses the newly selected invoice balance', async () => {
  const { fyo, payment } = await makePayment();
  fyo.singles.AccountingSettings.enablePartialPayment = false;
  await payment.set('amount', fyo.pesa(490231));
  fyo.doc.getNewDoc('PurchaseInvoice', {
    name: 'SMALLER-PI',
    party: payment.party,
    submitted: true,
    outstandingAmount: 100000,
  });

  await payment.for[0].set('referenceName', 'SMALLER-PI');
  await payment.sync();

  assert.equal(payment.amount.float, 100000);
  assert.equal(payment.for[0].amount.float, 100000);
  assert.equal(payment.inserted, true);
});

async function makePayment() {
  const stored = new Map();
  let fyo;
  class PaymentStore {
    getSchemaMap() {
      return getSchemas('-', []);
    }

    call(method, schemaName, value) {
      if (method === 'exists') {
        return Boolean(fyo.doc.docs.get(schemaName)?.[value]);
      }
      if (method === 'getAll') return [];
      if (method === 'insert') {
        stored.set(schemaName, structuredClone(value));
        return structuredClone(value);
      }
      throw new Error(`Unexpected database call: ${method}`);
    }
  }

  fyo = new Fyo({ DatabaseDemux: PaymentStore });
  await fyo.db.init();
  fyo.doc.registerModels(models);
  fyo.singles.AccountingSettings = { enablePartialPayment: true };
  fyo.singles.SystemSettings = { currency: 'INR', displayPrecision: 2 };
  fyo.doc.getNewDoc('Party', { name: 'Supplier', role: 'Supplier' });
  fyo.doc.getNewDoc('Account', { name: 'Creditors' });
  fyo.doc.getNewDoc('Account', { name: 'Bank' });
  fyo.doc.getNewDoc('PaymentMethod', { name: 'Cash', type: 'Cash' });
  fyo.doc.getNewDoc('NumberSeries', {
    name: 'DEMO-PAY-',
    referenceType: 'Payment',
    start: 1002,
  });
  const invoice = fyo.doc.getNewDoc('PurchaseInvoice', {
    name: 'DEMO-PI-1001',
    party: 'Supplier',
    submitted: true,
    outstandingAmount: 490231,
  });
  const original = fyo.doc.getNewDoc('Payment', {
    name: 'DEMO-PAY-1001',
    numberSeries: 'DEMO-PAY-',
    party: 'Supplier',
    paymentType: 'Pay',
    paymentMethod: 'Cash',
    account: 'Creditors',
    paymentAccount: 'Bank',
    amount: 910429,
    submitted: true,
    for: [
      {
        referenceType: 'PurchaseInvoice',
        referenceName: invoice.name,
        amount: 910429,
      },
    ],
  });
  original._notInserted = false;
  return { fyo, original, invoice, payment: original.duplicate(), stored };
}
