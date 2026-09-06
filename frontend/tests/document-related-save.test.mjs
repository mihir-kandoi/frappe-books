import assert from 'node:assert/strict';
import { test } from 'node:test';
import { makeFyo } from './helpers/accounting.mjs';

for (const schemaName of ['POSOpeningShift', 'POSClosingShift']) {
  for (const refreshFails of [false, true]) {
    test(`${schemaName} saves once when settings refresh ${refreshFails ? 'fails' : 'succeeds'}`, async () => {
      const fyo = await makeFyo();
      const doc = fyo.doc.getNewDoc(schemaName);
      const warnings = [];
      let writes = 0;
      let refreshed = false;
      let notified = false;
      fyo.onDocumentActionWarning = (warning) => warnings.push(warning);
      fyo.db.insert = async (schema, values) => {
        assert.equal(schema, schemaName);
        writes++;
        return values;
      };
      fyo.singles.POSSettings = {
        async load() {
          assert.equal(doc.inserted, true);
          refreshed = true;
          if (refreshFails) throw new Error('Settings refresh failed');
        },
      };
      doc.once('afterSync', () => {
        notified = true;
      });

      await doc.sync();

      assert.equal(writes, 1);
      assert.equal(doc.dirty, false);
      assert.equal(refreshed, true);
      assert.equal(notified, true);
      assert.equal(warnings.length, refreshFails ? 1 : 0);
    });
  }
}

test('saving a converted party refreshes its linked lead without another write', async () => {
  const fyo = await makeFyo();
  const lead = fyo.doc.getNewDoc('Lead', {
    name: 'Original Lead',
    status: 'Open',
  });
  const party = fyo.doc.getNewDoc('Party', {
    name: 'Different Party Name',
    fromLead: lead.name,
  });
  const writes = [];
  fyo.db.insert = async (schema, values) => {
    writes.push(schema);
    return values;
  };
  fyo.db.get = async (schema, name) => {
    assert.equal(schema, 'Lead');
    assert.equal(name, lead.name);
    return { ...lead.getValidDict(), status: 'Converted' };
  };

  await party.sync();

  assert.deepEqual(writes, ['Party']);
  assert.equal(party.dirty, false);
  assert.equal(lead.status, 'Converted');
  assert.equal(fyo.errorLog.length, 0);
});
