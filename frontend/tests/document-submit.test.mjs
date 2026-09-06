import assert from 'node:assert/strict';
import { test } from 'node:test';
import { makeFyo } from './helpers/accounting.mjs';

test('submission notifies listeners after the server accepts the document without rerunning model hooks', async () => {
  const { fyo, payment } = await makePayment();
  const calls = [];
  payment.afterSubmit = () => {
    assert.fail('Accounting hooks must run only on the server');
  };
  payment.once('afterSubmit', () => {
    assert.equal(payment.submitted, true);
    assert.equal(payment.dirty, false);
    assert.equal(payment.canSubmit, false);
    calls.push('listener');
  });
  fyo.db.runLifecycleAction = async (...args) => {
    assert.deepEqual(args, ['submit', 'Payment', payment.name]);
    assert.equal(payment.submitted, false);
    calls.push('server');
    return { ...payment.getValidDict(), submitted: true };
  };

  await payment.submit();
  await payment.submit();

  assert.deepEqual(calls, ['server', 'listener']);
});

test('a rejected submission retains the draft and listeners for a successful retry', async () => {
  const { fyo, payment } = await makePayment();
  let submissions = 0;
  let notifications = 0;
  payment.once('afterSubmit', () => notifications++);
  fyo.db.runLifecycleAction = async () => {
    submissions++;
    if (submissions === 1) throw new Error('Account cannot receive a posting');
    return { ...payment.getValidDict(), submitted: true };
  };

  await assert.rejects(payment.submit(), /Account cannot receive a posting/);

  assert.equal(payment.inserted, true);
  assert.equal(payment.submitted, false);
  assert.equal(payment.dirty, false);
  assert.equal(payment.canSubmit, true);
  assert.equal(notifications, 0);

  await payment.submit();

  assert.equal(payment.submitted, true);
  assert.equal(notifications, 1);
});

async function makePayment() {
  const fyo = await makeFyo();
  const payment = fyo.doc.getNewDoc('Payment', {
    name: 'PAY-0001',
    amount: 100,
    paymentType: 'Pay',
    submitted: false,
  });
  payment._notInserted = false;
  payment._dirty = false;
  return { fyo, payment };
}
