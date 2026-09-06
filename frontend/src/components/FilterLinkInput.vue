<template>
  <FrappeCombobox
    :model-value="value || null"
    :options="options"
    :loading="loading"
    :filterable="false"
    :label="t`Value`"
    :placeholder="t`Select a value`"
    :empty-text="error || t`No results found`"
    :error="error || undefined"
    variant="outline"
    size="md"
    @update:open="(open) => onOpen(Boolean(open))"
    @input="onInput"
    @update:model-value="(value) => $emit('change', value ?? '')"
  />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { t } from 'fyo';
import { Combobox as FrappeCombobox } from 'frappe-ui';
import { fyo } from 'src/initFyo';

type Option = { label: string; value: string; description?: string };

export default defineComponent({
  components: { FrappeCombobox },
  props: {
    target: { type: String, required: true },
    value: { type: String, default: '' },
  },
  emits: ['change'],
  data() {
    return { records: [] as Option[], search: '', loading: false, error: '' };
  },
  computed: {
    options(): Option[] {
      const query = this.search.toLocaleLowerCase();
      const options = this.records.filter((option) =>
        `${option.label} ${option.value}`.toLocaleLowerCase().includes(query)
      );
      if (
        this.value &&
        !query &&
        !options.some((option) => option.value === this.value)
      )
        options.unshift({ label: this.value, value: this.value });
      return options;
    },
  },
  methods: {
    onInput(event: Event) {
      this.search = (event.target as HTMLInputElement).value;
      if (!this.search) this.$emit('change', '');
    },
    async onOpen(open: boolean) {
      this.search = '';
      if (!open || this.loading) return;
      this.loading = true;
      this.error = '';
      try {
        const schema = fyo.schemaMap[this.target];
        const title = schema?.linkDisplayField || schema?.titleField || 'name';
        const rows = await fyo.db.getAll(this.target, {
          fields: [...new Set(['name', title])],
        });
        this.records = rows.map((row) => ({
          label: String(row[title] || row.name),
          value: String(row.name),
          description:
            row[title] && row[title] !== row.name
              ? String(row.name)
              : undefined,
        }));
      } catch {
        this.error = t`Unable to load options`;
      } finally {
        this.loading = false;
      }
    },
  },
});
</script>
