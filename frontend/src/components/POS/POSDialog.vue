<template>
  <FrappeDialog
    :open="openModal"
    :size="size"
    bare
    @close="$emit('closemodal')"
  >
    <div
      class="flex max-h-[calc(100dvh-6rem)] min-w-0 flex-col text-ink-gray-9"
    >
      <header
        class="flex shrink-0 items-start justify-between gap-4 border-b border-outline-gray-1 px-6 py-4"
      >
        <DialogTitle class="min-w-0 text-lg font-semibold leading-7">
          {{ title }}
        </DialogTitle>
        <FrappeButton
          icon="lucide-x"
          variant="ghost"
          class="shrink-0"
          :aria-label="t`Close`"
          @click="$emit('closemodal')"
        />
      </header>
      <div
        class="custom-scroll custom-scroll-thumb1 min-h-0 overflow-y-auto px-6 py-5"
        :class="bodyClass"
      >
        <slot />
      </div>
      <footer
        v-if="$slots.actions"
        class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-outline-gray-1 px-6 py-3"
      >
        <slot name="actions" />
      </footer>
    </div>
  </FrappeDialog>
</template>

<script setup lang="ts">
import { t } from 'fyo';
import { Button as FrappeButton, Dialog as FrappeDialog } from 'frappe-ui';
import { DialogTitle } from 'reka-ui';

withDefaults(
  defineProps<{
    openModal: boolean;
    title: string;
    size?: 'sm' | 'md' | 'lg' | '2xl' | '3xl' | '4xl';
    bodyClass?: string;
  }>(),
  { size: 'sm', bodyClass: '' },
);

defineEmits<{ closemodal: [] }>();
</script>
