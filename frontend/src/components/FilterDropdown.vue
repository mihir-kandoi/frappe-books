<template>
  <FrappePopover
    v-if="fields.length"
    side="bottom"
    align="end"
    :offset="8"
    :open="isOpen"
    @update:open="onOpenChange"
  >
    <template #trigger>
      <FrappeButton icon-left="lucide-list-filter" size="md">
        {{ activeFilterCount > 0 ? filterAppliedMessage : t`Filter` }}
      </FrappeButton>
    </template>
    <section
      :aria-label="t`Filters`"
      class="flex max-h-[var(--reka-popover-content-available-height)] w-[40rem] max-w-[calc(100vw-1.5rem)] flex-col"
    >
      <h2
        class="shrink-0 px-4 pb-3 pt-4 text-base font-semibold text-ink-gray-9"
      >
        {{ t`Filters` }}
      </h2>
      <div class="min-h-0 overflow-y-auto px-4 pb-4">
        <div v-if="explicitFilters.length" class="flex flex-col gap-4">
          <div
            v-for="(filter, i) in explicitFilters"
            :key="filter.id"
            role="group"
            :aria-label="t`Filter ${i + 1}`"
            class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_2rem] items-end gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.25fr)_2rem]"
          >
            <Select
              :border="true"
              :show-label="true"
              class="min-w-0"
              :df="{
                label: t`Field`,
                fieldname: 'fieldname',
                fieldtype: 'Select',
                options: fieldOptions,
              }"
              :value="filter.fieldname"
              @change="(value) => updateFilter(filter, 'fieldname', value)"
            />
            <Select
              :border="true"
              :show-label="true"
              class="min-w-0"
              :df="{
                label: t`Condition`,
                fieldname: 'condition',
                fieldtype: 'Select',
                options: conditionsFor(filter),
              }"
              :value="filter.condition"
              @change="(value) => updateFilter(filter, 'condition', value)"
            />
            <div
              v-if="isValuelessCondition(filter.condition)"
              class="col-span-2 h-8 sm:col-span-1"
            />
            <Select
              v-else-if="fieldFor(filter)?.fieldtype === 'Check'"
              :border="true"
              :show-label="true"
              class="col-span-2 min-w-0 sm:col-span-1"
              :df="{
                fieldname: 'value',
                label: t`Value`,
                fieldtype: 'Select',
                options: checkOptions,
              }"
              :value="
                filter.value === true
                  ? '1'
                  : filter.value === false
                    ? '0'
                    : String(filter.value ?? '')
              "
              @change="(value) => updateFilter(filter, 'value', value)"
            />
            <FrappeTextInput
              v-else
              class="col-span-2 min-w-0 sm:col-span-1"
              variant="outline"
              size="md"
              :label="t`Value`"
              :placeholder="valuePlaceholder(filter)"
              :model-value="String(filter.value ?? '')"
              @update:model-value="
                (value) => updateFilter(filter, 'value', value)
              "
              @keydown.enter.stop.prevent="applyFilters"
            />
            <FrappeButton
              icon="lucide-x"
              size="xs"
              variant="ghost"
              class="col-start-3 row-start-1 mb-1 justify-self-center sm:col-start-4"
              :tooltip="t`Remove filter`"
              :aria-label="t`Remove filter ${i + 1}`"
              @click="removeFilter(filter.id)"
            />
          </div>
        </div>
        <p v-else class="py-2 text-base text-ink-gray-6">
          {{ t`No filters selected` }}
        </p>
      </div>
      <p v-if="error" role="alert" class="px-4 pb-3 text-base text-ink-red-5">
        {{ error }}
      </p>
      <footer
        class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-outline-gray-1 p-3"
      >
        <FrappeButton
          icon-left="lucide-plus"
          size="md"
          variant="ghost"
          @click="addNewFilter"
        >
          {{ t`Add a filter` }}
        </FrappeButton>
        <div v-if="explicitFilters.length" class="flex items-center gap-2">
          <FrappeButton size="md" variant="ghost" @click="clearAllFilters">
            {{ t`Clear` }}
          </FrappeButton>
          <FrappeButton size="md" variant="solid" @click="applyFilters">
            {{ t`Apply` }}
          </FrappeButton>
        </div>
      </footer>
    </section>
  </FrappePopover>
</template>
<script lang="ts">
import { Field } from 'schemas/types';
import {
  Button as FrappeButton,
  Popover as FrappePopover,
  TextInput as FrappeTextInput,
} from 'frappe-ui';
import { fyo } from 'src/initFyo';
import { defineComponent } from 'vue';
import Select from './Controls/Select.vue';
import { QueryFilter } from 'utils/db/types';
import { t } from 'fyo';
import { getFilterFields, getFieldLabel } from 'src/utils/filterFields';
import {
  FilterSet,
  conditionsForField,
  defaultCondition,
  isCompleteFilter,
  isValuelessCondition,
  type FilterRow,
  type FilterCondition,
  type FilterValue,
} from 'src/utils/filterQuery';

export default defineComponent({
  name: 'FilterDropdown',
  components: { FrappePopover, FrappeTextInput, Select, FrappeButton },
  props: { schemaName: { type: String, required: true } },
  emits: ['change'],
  data() {
    return {
      filterSet: new FilterSet(),
      activeFilterCount: 0,
      isOpen: false,
      error: '',
    };
  },
  computed: {
    fields(): Field[] {
      return getFilterFields(
        fyo.schemaMap[this.schemaName]?.fields ?? [],
        fyo.models[this.schemaName]?.getListViewSettings?.(fyo)?.columns
      );
    },
    fieldOptions(): { label: string; value: string }[] {
      return this.fields.map((df) => ({
        label: getFieldLabel(df),
        value: df.fieldname,
      }));
    },
    explicitFilters(): FilterRow[] {
      return this.filterSet.rows.filter((row) => !row.implicit);
    },
    checkOptions() {
      return [
        { label: t`Yes`, value: '1' },
        { label: t`No`, value: '0' },
      ];
    },
    filterAppliedMessage(): string {
      return this.activeFilterCount === 1
        ? t`1 filter applied`
        : t`${this.activeFilterCount} filters applied`;
    },
  },
  watch: {
    schemaName() {
      this.filterSet = new FilterSet();
      this.activeFilterCount = 0;
      this.error = '';
      this.isOpen = false;
      this.$emit('change', {});
    },
  },
  methods: {
    isValuelessCondition,
    fieldFor(filter: FilterRow) {
      return this.fields.find((field) => field.fieldname === filter.fieldname);
    },
    conditionsFor(filter: FilterRow) {
      return [...conditionsForField(this.fieldFor(filter))];
    },
    valuePlaceholder(filter: FilterRow) {
      const type = this.fieldFor(filter)?.fieldtype;
      if (type === 'Date') return 'YYYY-MM-DD';
      if (type === 'Datetime') return 'YYYY-MM-DDTHH:mm:ss';
      return t`Value`;
    },
    onOpenChange(open: boolean) {
      if (open) this.isOpen = true;
      else this.applyFilters();
    },
    addNewFilter() {
      const field = this.fields[0];
      if (field) this.filterSet.add(field.fieldname, defaultCondition(field));
      this.error = '';
    },
    addFilter(
      fieldname: string,
      condition: FilterCondition,
      value: FilterValue,
      implicit = false
    ) {
      this.filterSet.add(fieldname, condition, value, implicit);
    },
    removeFilter(id: number) {
      this.filterSet.remove(id);
      this.error = '';
    },
    clearAllFilters() {
      this.filterSet.clear();
      this.emitFilterChange();
    },
    updateFilter<K extends 'fieldname' | 'condition' | 'value'>(
      row: FilterRow,
      key: K,
      value: FilterRow[K]
    ) {
      row[key] = value;
      this.error = '';
      if (key === 'fieldname') {
        row.value = '';
        if (
          !this.conditionsFor(row).some(
            (option) => option.value === row.condition
          )
        ) {
          row.condition = defaultCondition(this.fieldFor(row));
        }
      }
    },
    applyFilters() {
      if (this.emitFilterChange()) this.isOpen = false;
    },
    setFilter(filters: QueryFilter, implicit = false) {
      this.filterSet.setQuery(filters, implicit);
      this.emitFilterChange();
    },
    emitFilterChange(): boolean {
      try {
        const query = this.filterSet.toQuery(this.fields);
        this.filterSet.normalize();
        this.activeFilterCount =
          this.explicitFilters.filter(isCompleteFilter).length;
        this.error = '';
        this.$emit('change', query);
        return true;
      } catch (error) {
        this.error = (error as Error).message;
        return false;
      }
    },
  },
});
</script>
