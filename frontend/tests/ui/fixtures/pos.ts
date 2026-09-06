import { fyo } from 'src/initFyo';
import { computed, createApp, h, reactive, ref } from 'vue';
import { FrappeUI, FrappeUIProvider } from 'frappe-ui';
import { ConfigProvider } from 'reka-ui';
import { createRouter, createMemoryHistory } from 'vue-router';
import 'src/router';
import ModernPOS from 'src/pages/POS/ModernPOS.vue';
import ClassicPOS from 'src/pages/POS/ClassicPOS.vue';
import Link from 'src/components/Controls/Link.vue';
import { languageDirectionKey } from 'src/utils/injectionKeys';
import { preparePOSData } from './pos-data';
import 'src/styles/index.css';

async function mount() {
  const items = await preparePOSData();
  const invoice = fyo.doc.getNewDoc('SalesInvoice', {
    party: 'Aarav Shah',
    grandTotal: '0',
    baseGrandTotal: '0',
    netTotal: '0',
    outstandingAmount: '0',
    items: [],
    coupons: [],
  });
  const state = reactive({
    linkControl: null as Record<string, unknown> | null,
    modern: true,
    tableView: true,
    shiftOpen: true,
    modal: '',
    paidAmount: fyo.pesa(1250),
    paymentMethod: 'Cash',
    reference: '',
    clearanceDate: undefined as Date | undefined,
    items,
    invoice,
  });
  const coupon = fyo.doc.getNewDoc('AppliedCouponCodes');
  const app = createApp({
    render() {
      if (state.linkControl) {
        return h(ConfigProvider, { dir: state.linkControl.dir as 'ltr' | 'rtl' }, {
          default: () =>
            h(FrappeUIProvider, {}, {
              default: () =>
                h('main', { class: 'max-w-lg p-6' }, [
                  h(Link, {
                    border: true,
                    df: {
                      fieldtype: 'Link',
                      fieldname: 'party',
                      label: 'Customer',
                      target: 'Party',
                    },
                    value: state.invoice.party,
                    ...state.linkControl,
                    onChange: (value: string) => {
                      state.invoice.party = value;
                    },
                  }),
                ]),
            }),
        });
      }
      const modalProps = Object.fromEntries(
        [
          'Alert',
          'Payment',
          'Keyboard',
          'PriceList',
          'ItemEnquiry',
          'CouponCode',
          'ShiftClose',
          'SavedInvoice',
          'LoyaltyProgram',
          'ReturnSalesInvoice',
          'BatchSelection',
        ].map((name) => ['open' + name + 'Modal', state.modal === name])
      );
      return h(
        FrappeUIProvider,
        {},
        {
          default: () => [
            h(
              'header',
              {
                class:
                  'flex h-16 items-center border-b border-outline-gray-1 px-5 text-lg font-semibold',
              },
              'Point of Sale'
            ),
            h(state.modern ? ModernPOS : ClassicPOS, {
              ...modalProps,
              tableView: state.tableView,
              isPosShiftOpen: state.shiftOpen,
              sinvDoc: state.invoice,
              items: state.items,
              searchItems: state.items,
              totalQuantity:
                state.invoice.items?.reduce(
                  (sum, item) => sum + Number(item.quantity ?? 0),
                  0
                ) ?? 0,
              itemDiscounts: fyo.pesa(0),
              loyaltyPoints: 1250,
              loyaltyProgram: 'Store Rewards',
              selectedItemForBatch: items[0].name,
              itemQuantityMap: {},
              onToggleModal: (name: string, open?: boolean) => {
                state.modal = open === false ? '' : name;
              },
              onToggleView: () => {
                state.tableView = !state.tableView;
              },
              onSetPaidAmount: (amount: any) => {
                state.paidAmount = amount;
              },
              onSetCustomer: (name: string) => {
                state.invoice.party = name;
              },
              onSetPaymentMethod: (method: string) => {
                state.paymentMethod = method;
              },
              onSetTransferRefNo: (value: string) => {
                state.reference = value;
              },
              onSetTransferClearanceDate: (value: Date) => {
                state.clearanceDate = value;
              },
              onHandlePaymentAction: () => {
                state.modal = 'Payment';
              },
            }),
          ],
        }
      );
    },
  });
  app.use(FrappeUI);
  app.use(
    createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { render: () => null } }],
    })
  );
  app.mixin({
    computed: { fyo: () => fyo, platform: () => 'Web' },
    methods: { t: fyo.t, T: fyo.T },
  });
  const values = {
    sinvDoc: computed(() => state.invoice),
    doc: computed(() => state.invoice),
    coupons: coupon,
    appliedCoupons: computed(() => state.invoice.coupons ?? []),
    itemSerialNumbers: {},
    itemQtyMap: {},
    paidAmount: computed(() => state.paidAmount),
    paymentMethod: computed(() => state.paymentMethod),
    transferRefNo: computed(() => state.reference),
    transferClearanceDate: computed(() => state.clearanceDate),
    totalTaxedAmount: fyo.pesa(0),
    itemDiscounts: fyo.pesa(0),
    isDiscountingEnabled: true,
  };
  Object.entries(values).forEach(([key, value]) => app.provide(key, value));
  app.provide(languageDirectionKey, ref('ltr'));
  app.mount('#app');
  (window as any).posFixture = {
    state,
    fyo,
    fillCart() {
      state.invoice.items = items.slice(0, 3).map((item, index) =>
        fyo.doc.getNewDoc('SalesInvoiceItem', {
          name: `row-${index}`,
          item: item.name,
          quantity: 2,
          transferQuantity: 2,
          rate: String(item.rate),
          amount: String(item.rate.mul(2)),
          unit: 'Unit',
          parent: 'POS-AUDIT',
          parentSchemaName: 'SalesInvoice',
          parentFieldname: 'items',
        })
      ) as any;
      for (const field of [
        'netTotal',
        'grandTotal',
        'baseGrandTotal',
        'outstandingAmount',
      ]) {
        state.invoice[field] = fyo.pesa(2250);
      }
    },
  };
}
mount();
