<template>
  <FrappePopover
    v-if="fields.length"
    ref="filterPopover"
    side="bottom"
    align="end"
    :offset="8"
    @close="emitFilterChange"
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
      <h2 class="shrink-0 px-4 pb-3 pt-4 text-base font-semibold text-ink-gray-9">
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
              @change="(value) => updateNewFilters(i, 'fieldname', value)"
            />
            <Select
              :border="true"
              :show-label="true"
              class="min-w-0"
              :df="{
                label: t`Condition`,
                fieldname: 'condition',
                fieldtype: 'Select',
                options: conditionsForDropdown,
              }"
              :value="filter.condition"
              @change="(value) => updateNewFilters(i, 'condition', value)"
            />
            <Data
              :border="true"
              :show-label="true"
              class="col-span-2 min-w-0 sm:col-span-1"
              :df="{
                label: t`Value`,
                placeholder: t`Value`,
                fieldname: 'value',
                fieldtype: 'Data',
              }"
              :value="String(filter.value)"
              @input="(event) => updateFilterValueFromInput(i, event)"
              @change="(value) => updateNewFilters(i, 'value', value)"
              @keydown.enter.stop.prevent="applyFilters"
            />
            <FrappeButton
              icon="lucide-x"
              size="xs"
              variant="ghost"
              class="col-start-3 row-start-1 mb-1 justify-self-center sm:col-start-4"
              :tooltip="t`Remove filter`"
              :aria-label="t`Remove filter ${i + 1}`"
              @click="removeFilter(i)"
            />
          </div>
        </div>
        <p v-else class="py-2 text-base text-ink-gray-6">
          {{ t`No filters selected` }}
        </p>
      </div>
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
import { Field, FieldTypeEnum } from 'schemas/types';
import { Button as FrappeButton, Popover as FrappePopover } from 'frappe-ui';
import { fyo } from 'src/initFyo';
import { getRandomString } from 'utils';
import { defineComponent } from 'vue';
import Data from './Controls/Data.vue';
import Select from './Controls/Select.vue';
import { QueryFilter } from 'utils/db/types';
import { t } from 'fyo';

const conditions = [
  { label: t`Is`, value: '=' },
  { label: t`Is Not`, value: '!=' },
  { label: t`Contains`, value: 'like' },
  { label: t`Does Not Contain`, value: 'not like' },
  { label: t`Greater Than`, value: '>' },
  { label: t`Less Than`, value: '<' },
  { label: t`Is Empty`, value: 'is null' },
  { label: t`Is Not Empty`, value: 'is not null' },
] as const;

type Condition = (typeof conditions)[number]['label'];

type Filter = {
  id: string;
  fieldname: string;
  condition: Condition;
  value: QueryFilter[string];
  implicit: boolean;
};

const fieldLabelAcronyms = new Set(['ERP', 'GST', 'GSTIN', 'HSN', 'ID', 'POS', 'SAC', 'UOM']);

function getFieldLabel(field: Field): string {
  const label = field.label?.trim();
  if (label && label !== field.fieldname) {
    return label;
  }

  return field.fieldname
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word, index) => {
      const upperWord = word.toUpperCase();
      if (fieldLabelAcronyms.has(upperWord)) {
        return upperWord;
      }

      const lowerWord = word.toLowerCase();
      if (index > 0 && ['and', 'an', 'a', 'from', 'by', 'on'].includes(lowerWord)) {
        return lowerWord;
      }

      return lowerWord[0].toUpperCase() + lowerWord.slice(1);
    })
    .join(' ');
}

export default defineComponent({
  name: 'FilterDropdown',
  components: {
    FrappePopover,
    Select,
    Data,
    FrappeButton,
  },
  props: { schemaName: { type: String, required: true } },
  emits: ['change'],
  data() {
    return {
      filters: [] as Filter[],
      newFilters: [] as Filter[],
    };
  },
  computed: {
    fields(): Field[] {
      const excludedFieldsTypes: string[] = [
        FieldTypeEnum.Table,
        FieldTypeEnum.Attachment,
        FieldTypeEnum.AttachImage,
      ];

      const listViewSettings = fyo.models[this.schemaName]?.getListViewSettings?.(fyo);
      const statusField = listViewSettings?.columns?.[1] as any;

      const fields = fyo.schemaMap[this.schemaName]?.fields ?? [];
      const filteredFields = fields.filter((f) => {
        if (f.filter) {
          return true;
        }

        if (excludedFieldsTypes.includes(f.fieldtype)) {
          return false;
        }

        if (f.computed || f.meta || f.readOnly) {
          return false;
        }

        return true;
      });

      if (statusField && statusField.fieldname) {
        const statusFieldExists = filteredFields.some(
          (field) => field.fieldname === statusField.fieldname,
        );

        if (!statusFieldExists) {
          const originalStatusField = fields.find(
            (field) => field.fieldname === statusField.fieldname,
          );
          if (originalStatusField) {
            filteredFields.unshift(originalStatusField);
          } else {
            filteredFields.unshift(statusField);
          }
        }
      }

      return filteredFields;
    },
    fieldOptions(): { label: string; value: string }[] {
      return this.fields.map((df) => ({
        label: getFieldLabel(df),
        value: df.fieldname,
      }));
    },
    conditions(): { label: string; value: string }[] {
      return [...conditions];
    },
    conditionsForDropdown(): { label: string; value: string }[] {
      return conditions.map((c) => ({
        label: c.label,
        value: c.label,
      }));
    },
    explicitFilters(): Filter[] {
      return this.filters.filter((f) => !f.implicit);
    },
    activeFilterCount(): number {
      return this.explicitFilters.filter((filter) => filter.value).length;
    },
    filterAppliedMessage(): string {
      if (this.activeFilterCount === 1) {
        return this.t`1 filter applied`;
      }

      return this.t`${this.activeFilterCount} filters applied`;
    },
  },

  methods: {
    getConditionLabel(value: string): string {
      const condition = conditions.find((c) => c.value === value);
      return condition ? condition.label : value;
    },

    getConditionValue(label: string): string {
      const condition = conditions.find((c) => c.label === label);
      return condition ? condition.value : label;
    },

    addNewFilter(): void {
      const df = this.fields[0];
      if (!df) {
        return;
      }

      this.addFilter(df.fieldname, 'like', '', false);
    },
    addFilter(
      fieldname: string,
      condition: string,
      value: Filter['value'],
      implicit?: boolean,
    ): void {
      const displayCondition = this.getConditionLabel(condition);
      const newFilter = {
        id: getRandomString(),
        fieldname,
        condition: displayCondition,
        value,
        implicit: !!implicit,
      };
      this.filters.push(newFilter);
      this.newFilters.push(newFilter);
    },

    applyFilters() {
      this.closeFilterPopover();
    },

    removeFilter(index: number): void {
      this.filters.splice(index, 1);
      this.newFilters.splice(index, 1);
    },

    clearAllFilters(): void {
      this.filters = [];
      this.newFilters = [];

      this.$emit('change', {});
    },

    updateNewFilters<K extends keyof Filter>(index: number, key: K, value: Filter[K]) {
      if (key === 'condition') {
        const displayCondition = this.getConditionLabel(value as string);
        this.newFilters![index][key] = displayCondition as Filter[K];
        this.filters[index][key] = displayCondition as Filter[K];
      } else {
        this.newFilters![index][key] = value;
        this.filters[index][key] = value;
      }
    },

    updateFilterValueFromInput(index: number, event: Event): void {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) {
        return;
      }

      this.updateNewFilters(index, 'value', target.value);
    },

    closeFilterPopover(): void {
      const popover = this.$refs.filterPopover as
        | InstanceType<typeof FrappePopover>
        | undefined;
      popover?.close();
    },

    setFilter(filters: QueryFilter, implicit?: boolean): void {
      this.filters = [];
      this.newFilters = [];

      Object.keys(filters).map((fieldname) => {
        let parts = filters[fieldname];
        let condition: Condition;
        let value: Filter['value'];

        if (Array.isArray(parts)) {
          condition = parts[0] as Condition;
          value = parts[1] as Filter['value'];
        } else {
          condition = '=';
          value = parts;
        }

        this.addFilter(fieldname, condition, value, implicit);
      });

      this.emitFilterChange();
    },

    emitFilterChange(): void {
      const filters: Record<string, [Condition, Filter['value']]> = {};

      for (const { condition, value, fieldname } of this.newFilters) {
        if (value === '' || value === null || value === undefined) {
          continue;
        }

        const sqlCondition = this.getConditionValue(condition);

        if (fieldname === 'numberSeries') {
          filters['name'] = [sqlCondition, value];
        } else {
          filters[fieldname] = [sqlCondition, value];
        }
      }

      this.$emit('change', filters);
      this.filters = [...this.newFilters];

      if (this.newFilters.length) {
        this.filters = this.filters.filter(
          (filter) => filter.condition && filter.value && filter.fieldname,
        );
        this.filters.push(this.newFilters[this.newFilters.length - 1]);
      }

      this.filters = Array.from(
        new Map(
          this.filters.map((filter) => [
            `${filter.condition}-${filter.value}-${filter.fieldname}`,
            filter,
          ]),
        ).values(),
      );
      // Keep draft indices aligned with the remaining visible rows.
      this.newFilters = [...this.filters];
    },
  },
});
</script>
