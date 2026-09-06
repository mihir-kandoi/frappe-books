<template>
  <Modal
    :open-modal="openModal"
    :title="t`Leave this sale?`"
    size="lg"
    @closemodal="$emit('toggleModal', 'Alert')"
  >
    <p class="text-base leading-6 text-ink-gray-7">
      {{
        t`Save this sale to resume it later, or discard the selected items and continue to the invoice list.`
      }}
    </p>
    <template #actions>
      <Button size="lg" @click="$emit('toggleModal', 'Alert')">{{
        t`Cancel`
      }}</Button>
      <Button
        size="lg"
        theme="red"
        @click="
          routeTo('/list/SalesInvoice');
          $emit('toggleModal', 'Alert');
        "
        >{{ t`Discard and Continue` }}</Button
      >
      <Button size="lg" type="primary" @click="$emit('saveAndContinue')">{{
        t`Save and Continue`
      }}</Button>
    </template>
  </Modal>
</template>

<script lang="ts">
import Button from 'src/components/Button.vue';
import Modal from 'src/components/POS/POSDialog.vue';
import { defineComponent } from 'vue';
import { routeTo } from 'src/utils/ui';

export default defineComponent({
  name: 'AlertModal',
  components: {
    Modal,
    Button,
  },
  props: {
    openModal: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['toggleModal', 'saveAndContinue'],
  methods: {
    routeTo,
  },
});
</script>
