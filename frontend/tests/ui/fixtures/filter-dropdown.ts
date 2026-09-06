import { createApp, h, reactive, ref } from 'vue';
import { FrappeUI, FrappeUIProvider } from 'frappe-ui';
import { fyo } from 'src/initFyo';
import FilterDropdown from 'src/components/FilterDropdown.vue';
import { models } from 'models';
import { getSchemas } from 'schemas';
import { FrappeDatabaseDemux } from 'src/web/databaseDemux';
import { languageDirectionKey } from 'src/utils/injectionKeys';
import type { QueryFilter } from 'utils/db/types';
import 'src/styles/index.css';

async function mount() {
  FrappeDatabaseDemux.prototype.getSchemaMap = async () => getSchemas('-', []);
  await fyo.db.init();
  fyo.doc.registerModels(models);
  const state = reactive({ applied: {} as QueryFilter });
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
                    schemaName: 'SalesInvoice',
                    onChange: (query: QueryFilter) => {
                      state.applied = query;
                    },
                  }),
                ]
              ),
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
  (window as any).filterFixture = { state, filter };
}

void mount();
