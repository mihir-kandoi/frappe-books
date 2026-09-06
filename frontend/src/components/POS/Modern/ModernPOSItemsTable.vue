<template>
  <div ref="container" class="flex min-h-0 flex-1 gap-2 pt-2">
    <div
      v-for="(columnItems, columnIndex) in itemColumns"
      :key="columnIndex"
      class="min-h-0 min-w-0 flex-1"
    >
      <FrappeList
        :columns="listColumns"
        :row-height="48"
        divider="full"
        class="flex h-full min-h-0 flex-col overflow-hidden rounded-4 border border-outline-gray-1 list-gap-2 [--list-row-padding-x:0px]"
      >
        <FrappeListHeader>
          <FrappeListHeaderCell
            v-for="df in tableFields"
            :key="df.fieldname"
            class="px-3"
            :class="isNumeric(df as Field) ? 'justify-end' : ''"
          >
            {{ df.label }}
          </FrappeListHeaderCell>
        </FrappeListHeader>

        <div
          class="custom-scroll custom-scroll-thumb2 min-h-0 flex-1 overflow-y-auto"
        >
          <FrappeListRows :items="columnItems" row-key="name">
            <template #default="{ item: row, value }">
              <FrappeListRow
                :value="value"
                class="text-ink-gray-8"
                :aria-label="`Add ${row.name}`"
                @click="handleChange(row)"
              >
                <FrappeListCell
                  v-for="df in tableFields"
                  :key="df.fieldname"
                  class="min-w-0 px-3"
                  :class="
                    isNumeric(df as Field) ? 'justify-end text-end' : ''
                  "
                >
                  <span
                    class="truncate"
                    :title="
                      fyo.format(row[df.fieldname as keyof POSItem], df)
                    "
                  >
                    {{
                      fyo.format(row[df.fieldname as keyof POSItem], df)
                    }}
                  </span>
                </FrappeListCell>
              </FrappeListRow>
            </template>
          </FrappeListRows>
        </div>
      </FrappeList>
    </div>
  </div>
</template>

<script lang="ts">
import {
  List as FrappeList,
  ListCell as FrappeListCell,
  ListHeader as FrappeListHeader,
  ListHeaderCell as FrappeListHeaderCell,
  ListRow as FrappeListRow,
  ListRows as FrappeListRows,
} from 'frappe-ui/list';
import { isNumeric } from 'src/utils';
import { t } from 'fyo';
import { defineComponent } from 'vue';
import { Field } from 'schemas/types';
import { POSItem } from '../types';

export default defineComponent({
  name: 'ModernPOSItemsTable',
  components: {
    FrappeList,
    FrappeListCell,
    FrappeListHeader,
    FrappeListHeaderCell,
    FrappeListRow,
    FrappeListRows,
  },
  emits: ['addItem', 'updateValues'],
  props: {
    items: Array,
    itemQtyMap: Object,
    itemVisibility: {
      type: String,
      default: 'Inventory Items',
    },
  },
  data() {
    return {
      showTwoColumns: false,
      resizeObserver: undefined as ResizeObserver | undefined,
    };
  },
  mounted() {
    this.resizeObserver = new ResizeObserver(([entry]) => {
      this.showTwoColumns = entry.contentRect.width >= 840;
    });
    this.resizeObserver.observe(this.$refs.container as HTMLElement);
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect();
  },
  computed: {
    ratio() {
      return [1.6, 0.9, 0.8, 0.7];
    },
    listColumns(): string[] {
      return this.ratio.map((ratio) => `minmax(0, ${ratio}fr)`);
    },
    tableFields() {
      const fields = [
        {
          fieldname: 'name',
          fieldtype: 'Data',
          label: t`Item`,
          placeholder: 'Item',
          readOnly: true,
        },
        {
          fieldname: 'rate',
          label: t`Rate`,
          placeholder: 'Rate',
          fieldtype: 'Currency',
          readOnly: true,
        },
        {
          fieldname: 'unit',
          label: t`Unit`,
          placeholder: 'Unit',
          fieldtype: 'Data',
          target: 'UOM',
          readOnly: true,
        },
      ] as Field[];

      fields.splice(2, 0, {
        fieldname: 'availableQty',
        label: t`Qty`,
        placeholder: 'Available Qty',
        fieldtype: 'Float',
        readOnly: true,
      });

      return fields;
    },
    itemColumns(): POSItem[][] {
      const items = (this.items ?? []) as POSItem[];
      if (!this.showTwoColumns || items.length < 2) return [items];
      const midpoint = Math.ceil(items.length / 2);
      return [items.slice(0, midpoint), items.slice(midpoint)];
    },
  },
  methods: {
    handleChange(value: POSItem) {
      this.$emit('addItem', value);
      this.$emit('updateValues');
    },
    isNumeric,
  },
});
</script>
