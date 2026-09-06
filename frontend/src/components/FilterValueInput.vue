<template>
  <FrappeSelect
    v-if="field?.fieldtype === 'Select' || field?.fieldtype === 'Check'"
    :options="options"
    :model-value="selectValue"
    :label="t`Value`"
    :placeholder="t`Select a value`"
    variant="outline"
    size="md"
    side="bottom"
    align="start"
    @update:model-value="(value) => $emit('change', value ?? '')"
  />
  <component
    :is="
      field?.fieldtype === 'Date' ? 'FrappeDatePicker' : 'FrappeDateTimePicker'
    "
    v-else-if="['Date', 'Datetime'].includes(field?.fieldtype ?? '')"
    :model-value="String(value ?? '')"
    :label="t`Value`"
    :clearable="true"
    variant="outline"
    size="md"
    side="bottom"
    align="start"
    @change="(value: string) => $emit('change', value)"
  />
  <FilterLinkInput
    v-else-if="linkTarget && ['=', '!='].includes(condition)"
    :key="linkTarget"
    :target="linkTarget"
    :value="String(value ?? '')"
    @change="(value) => $emit('change', value)"
  />
  <AutoComplete
    v-else-if="field?.fieldtype === 'AutoComplete'"
    :df="{ ...field, label: t`Value`, readOnly: false, required: false }"
    :value="value ?? undefined"
    :border="true"
    :show-label="true"
    :show-clear-button="true"
    @change="(value: string) => $emit('change', value)"
  />
  <FrappeTextInput
    v-else
    :model-value="String(value ?? '')"
    :label="t`Value`"
    :placeholder="t`Value`"
    :inputmode="
      field?.fieldtype === 'Int' ? 'numeric' : numeric ? 'decimal' : undefined
    "
    variant="outline"
    size="md"
    @update:model-value="(value) => $emit('change', value)"
    @keydown.enter.stop.prevent="$emit('apply')"
  />
</template>

<script lang="ts">
import { defineAsyncComponent, defineComponent, type PropType } from 'vue';
import { t } from 'fyo';
import { getOptionList } from 'fyo/utils';
import {
  Select as FrappeSelect,
  DatePicker as FrappeDatePicker,
  DateTimePicker as FrappeDateTimePicker,
  TextInput as FrappeTextInput,
} from 'frappe-ui';
import type { Field } from 'schemas/types';
import type { FilterRow, FilterValue } from 'src/utils/filterQuery';
import { fyo } from 'src/initFyo';
import FilterLinkInput from './FilterLinkInput.vue';

export default defineComponent({
  components: {
    FrappeSelect,
    FrappeDatePicker,
    FrappeDateTimePicker,
    FrappeTextInput,
    AutoComplete: defineAsyncComponent(
      () => import('./Controls/AutoComplete.vue')
    ),
    FilterLinkInput,
  },
  props: {
    field: Object as PropType<Field>,
    condition: { type: String, required: true },
    value: [String, Number, Boolean] as PropType<FilterValue>,
    filters: { type: Array as PropType<FilterRow[]>, required: true },
  },
  emits: ['change', 'apply'],
  computed: {
    options() {
      if (this.field?.fieldtype === 'Check')
        return [
          { label: t`Yes`, value: '1' },
          { label: t`No`, value: '0' },
        ];
      return this.field ? getOptionList(this.field, undefined) : [];
    },
    selectValue() {
      if (this.value === true) return '1';
      if (this.value === false) return '0';
      return this.value == null || this.value === ''
        ? undefined
        : String(this.value);
    },
    linkTarget(): string {
      if (this.field?.fieldtype === 'Link') return this.field.target;
      if (this.field?.fieldtype !== 'DynamicLink') return '';
      const reference = this.field.references;
      const values = this.filters.filter(
        (row) =>
          row.fieldname === reference && row.condition === '=' && row.value
      );
      const targets = new Set(values.map((row) => String(row.value)));
      const target = targets.size === 1 ? [...targets][0] : '';
      return fyo.schemaMap[target] ? target : '';
    },
    numeric() {
      return ['Int', 'Float', 'Currency'].includes(this.field?.fieldtype ?? '');
    },
  },
});
</script>
