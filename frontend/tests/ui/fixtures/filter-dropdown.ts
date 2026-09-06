import { createApp, h, reactive, ref } from 'vue';
import { FrappeUI, FrappeUIProvider } from 'frappe-ui';
import { fyo } from 'src/initFyo';
import List from 'src/pages/ListView/List.vue';
import FilterDropdown from 'src/components/FilterDropdown.vue';
import { models } from 'models';
import { getSchemas } from 'schemas';
import { FrappeDatabaseDemux } from 'src/web/databaseDemux';
import { languageDirectionKey } from 'src/utils/injectionKeys';
import type { QueryFilter } from 'utils/db/types';
import 'src/styles/index.css';

async function mount() {
  FrappeDatabaseDemux.prototype.getSchemaMap = async () => {
    const schemas = getSchemas('-', []);
    return {
      ...schemas,
      Item: {
        ...schemas.Item,
        fields: [
          ...schemas.Item.fields,
          {
            fieldname: 'customChoice',
            fieldtype: 'Select',
            label: 'Custom Choice',
            filter: true,
            readOnly: true,
            required: true,
            default: 'code-one',
            options: [
              { label: 'First label', value: 'code-one' },
              { label: 'Second label', value: 'code-two' },
            ],
          },
          {
            fieldname: 'customSuggestion',
            fieldtype: 'AutoComplete',
            label: 'Custom Suggestion',
            options: [
              { label: 'One', value: 'One' },
              { label: 'Two', value: 'Two' },
            ],
          },
        ],
      },
    };
  };
  await fyo.db.init();
  fyo.doc.registerModels(models);
  fyo.singles.SystemSettings = { currency: 'USD', displayPrecision: 2 } as any;
  const state = reactive({
    applied: {} as QueryFilter,
    schemaName: 'SalesInvoice',
    useDatabase: false,
    lookupFailure: false,
    lookupCalls: [] as string[],
    queries: [] as QueryFilter[],
  });
  const list = ref<InstanceType<typeof List>>();
  fyo.db.getAll = async (_schema, options) => {
    if (options?.fields?.[0] !== '*') {
      state.lookupCalls.push(_schema);
      if (state.lookupFailure) throw new Error('Lookup unavailable');
      if (_schema === 'User')
        return [{ name: 'Administrator' }, { name: 'Guest' }];
      return _schema === 'NumberSeries'
        ? [{ name: 'JV-' }, { name: 'BANK-' }]
        : [{ name: `${_schema}-001` }, { name: `${_schema}-002` }];
    }
    state.queries.push(options?.filters ?? {});
    if (state.useDatabase) {
      const response = await fetch('/__filter_database_test', {
        method: 'POST',
        body: JSON.stringify(options?.filters ?? {}),
      });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }
    return Array.from({ length: 60 }, (_, index) => ({
      name: `INV-${index + 1}`,
      party: 'Test customer',
      date: '2024-01-01',
      submitted: true,
      cancelled: false,
      grandTotal: fyo.pesa(100),
      baseGrandTotal: fyo.pesa(100),
      outstandingAmount: fyo.pesa(
        index % 3 === 0 ? 0 : index % 3 === 1 ? 50 : 100
      ),
    }));
  };
  const filter = ref<InstanceType<typeof FilterDropdown>>();
  const app = createApp({
    render: () =>
      h(
        FrappeUIProvider,
        {},
        {
          default: () =>
            h('main', { class: 'min-h-screen bg-surface-gray-1' }, [
              h(
                'header',
                {
                  class:
                    'flex h-16 items-center justify-between border-b border-outline-gray-1 bg-surface-white px-5',
                },
                [
                  h('h1', { class: 'text-lg font-semibold' }, 'Sales Invoice'),
                  h(FilterDropdown, {
                    ref: filter,
                    schemaName: state.schemaName,
                    onChange: (query: QueryFilter) => {
                      state.applied = query;
                      void list.value?.updateData(query);
                    },
                  }),
                ]
              ),
              h(List, {
                ref: list,
                schemaName: state.schemaName,
                listConfig: { columns: ['name'] },
                class: 'h-[calc(100vh-4rem)]',
              }),
            ]),
        }
      ),
  });
  app.use(FrappeUI);
  app.mixin({
    computed: { fyo: () => fyo },
    methods: { t: fyo.t, T: fyo.T },
  });
  app.provide(languageDirectionKey, ref('ltr'));
  app.mount('#app');
  (window as any).filterFixture = { state, filter, list, fyo };
}

void mount();
