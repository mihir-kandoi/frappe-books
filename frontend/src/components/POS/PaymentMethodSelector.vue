<template>
	<div>
		<FrappeFormLabel :label="t`Payment method`" :required="true" size="md" />
		<div class="mt-2 grid grid-cols-2 gap-2">
			<FrappeButton
				v-for="method in methods"
				:key="method"
				class="min-w-0 w-full"
				:tooltip="method"
				:aria-pressed="method === selected"
				theme="gray"
				:variant="method === selected ? 'solid' : 'subtle'"
				size="lg"
				@click="$emit('select', method)"
			>
				<span class="flex min-w-0 items-center justify-center gap-2">
					<span class="truncate">{{ t`${method}` }}</span>
					<span
						v-if="method === selected"
						class="lucide-check size-4 shrink-0"
						aria-hidden="true"
					/>
				</span>
			</FrappeButton>
		</div>
	</div>
</template>

<script lang="ts">
import { Button as FrappeButton, FormLabel as FrappeFormLabel } from "frappe-ui";
import { defineComponent, PropType } from "vue";

export default defineComponent({
	name: "PaymentMethodSelector",
	components: { FrappeButton, FrappeFormLabel },
	props: {
		methods: {
			type: Array as PropType<string[]>,
			default: () => [],
		},
		selected: String,
	},
	emits: ["select"],
});
</script>
