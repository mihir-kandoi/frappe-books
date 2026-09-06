<template>
  <div class="flex flex-col gap-3">
    <div class="grid grid-cols-2 gap-2">
      <Button :style="buttonStyle('save')" @click="$emit('save')">{{
        t`Save`
      }}</Button>
      <Button :style="buttonStyle('cancel')" @click="$emit('clear')">{{
        t`Cancel`
      }}</Button>
      <Button
        :style="buttonStyle('held')"
        :class="{ 'col-span-2': !enableReturns }"
        @click="$emit('held')"
        >{{ t`Held` }}</Button
      >
      <Button
        v-if="enableReturns"
        :style="buttonStyle('return')"
        @click="$emit('return')"
        >{{ t`Return` }}</Button
      >
    </div>
    <Button
      size="lg"
      type="primary"
      :style="buttonStyle('pay')"
      :disabled="disablePay"
      @click="$emit('pay')"
    >
      {{ isReturn ? t`Refund` : t`Pay` }}
    </Button>
  </div>
</template>

<script setup lang="ts">
import { t } from 'fyo';
import { POSProfile } from 'models/baseModels/POSProfile/PosProfile';
import Button from 'src/components/Button.vue';
import { fyo } from 'src/initFyo';

const props = defineProps<{
  profile?: POSProfile | null;
  enableReturns?: boolean;
  disablePay?: boolean;
  isReturn?: boolean;
}>();
defineEmits<{ save: []; clear: []; held: []; return: []; pay: [] }>();

function buttonStyle(
  action: 'save' | 'cancel' | 'held' | 'return' | 'pay',
) {
  const field = `${action}ButtonColour`;
  const backgroundColor =
    props.profile?.[field] || fyo.singles.Defaults?.[field];
  return backgroundColor
    ? { backgroundColor: String(backgroundColor) }
    : undefined;
}
</script>
