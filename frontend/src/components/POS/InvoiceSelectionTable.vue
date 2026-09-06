<template>
  <div class="flex min-h-0 flex-1 overflow-x-auto">
	<FrappeList
		:columns="listColumns"
		:row-height="48"
		divider="full"
		class="flex min-h-0 min-w-[34rem] flex-1 flex-col overflow-hidden rounded-4 border border-outline-gray-1 list-gap-2 [--list-row-padding-x:0px]"
		:aria-label="t`Invoices`"
	>
		<FrappeListHeader>
			<FrappeListHeaderCell class="justify-center">
				<span class="sr-only">{{ t`Select` }}</span>
			</FrappeListHeaderCell>
			<FrappeListHeaderCell
				v-for="field in fields"
				:key="field.fieldname"
				class="px-2"
				:class="{ 'justify-end': isNumeric(field) }"
			>
				{{ field.label }}
			</FrappeListHeaderCell>
		</FrappeListHeader>

		<div
			v-if="rows.length"
			class="custom-scroll custom-scroll-thumb2 min-h-0 w-full flex-1 overflow-y-auto"
		>
			<FrappeListRows :items="rows" row-key="name">
				<template #default="{ item: row, value }">
					<FrappeListRow
						:value="value"
						class="transition-colors"
						:class="isSelected(row) ? 'bg-surface-gray-2' : 'bg-surface-base'"
						:aria-selected="isSelected(row)"
					>
						<FrappeListCell class="justify-center">
							<FrappeCheckbox
								:model-value="isSelected(row)"
								:aria-label="`Select invoice ${getRowName(row)}`"
								size="sm"
								@update:model-value="setSelected(row, $event)"
							/>
						</FrappeListCell>
						<FrappeListCell
							v-for="field in fields"
							:key="field.fieldname"
							class="min-w-0 truncate px-2 text-base text-ink-gray-8"
							:class="{ 'justify-end text-end': isNumeric(field) }"
							:title="formatCell(row, field)"
						>
							<span class="truncate">{{ formatCell(row, field) }}</span>
						</FrappeListCell>
					</FrappeListRow>
				</template>
			</FrappeListRows>
		</div>

		<div
			v-else
			class="flex min-h-0 flex-1 items-center justify-center text-sm text-ink-gray-6"
		>
			{{ emptyText }}
		</div>
	</FrappeList>
  </div>
</template>

<script lang="ts">
import { Field } from "schemas/types";
import { Checkbox as FrappeCheckbox } from "frappe-ui";
import {
	List as FrappeList,
	ListCell as FrappeListCell,
	ListHeader as FrappeListHeader,
	ListHeaderCell as FrappeListHeaderCell,
	ListRow as FrappeListRow,
	ListRows as FrappeListRows,
} from "frappe-ui/list";
import { fyo } from "src/initFyo";
import { isNumeric } from "src/utils";
import { defineComponent, PropType } from "vue";

type InvoiceRow = Record<string, unknown>;

export default defineComponent({
	name: "InvoiceSelectionTable",
	components: {
		FrappeCheckbox,
		FrappeList,
		FrappeListCell,
		FrappeListHeader,
		FrappeListHeaderCell,
		FrappeListRow,
		FrappeListRows,
	},
	props: {
		rows: {
			type: Array as PropType<InvoiceRow[]>,
			default: () => [],
		},
		fields: {
			type: Array as PropType<Field[]>,
			required: true,
		},
		ratios: {
			type: Array as PropType<number[]>,
			required: true,
		},
		modelValue: {
			type: String,
			default: "",
		},
		emptyText: {
			type: String,
			required: true,
		},
	},
	emits: ["update:modelValue"],
	computed: {
		listColumns(): string[] {
			return ["2.5rem", ...this.ratios.map((ratio) => `minmax(0, ${ratio}fr)` )];
		},
	},
	methods: {
		isNumeric,
		getRowName(row: InvoiceRow): string {
			return String(row.name ?? "");
		},
		isSelected(row: InvoiceRow): boolean {
			return this.modelValue === this.getRowName(row);
		},
		setSelected(row: InvoiceRow, selected?: boolean | 0 | 1) {
			this.$emit("update:modelValue", selected ? this.getRowName(row) : "");
		},
		formatCell(row: InvoiceRow, field: Field): string {
			try {
				return fyo.format(row[field.fieldname], field) || "—";
			} catch {
				const value = row[field.fieldname];
				return value == null || value === "" ? "—" : String(value);
			}
		},
	},
});
</script>
