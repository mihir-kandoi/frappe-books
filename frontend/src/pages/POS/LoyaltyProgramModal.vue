<template>
  <Modal
    :open-modal="openModal"
    :title="t`Redeem Loyalty Points`"
    @closemodal="cancelLoyaltyProgram"
  >
    <div class="flex flex-col gap-5">
      <div class="flex items-start gap-3">
        <Icon name="coins" class="mt-1 size-5 shrink-0 text-ink-gray-6" />
        <div class="min-w-0">
          <p class="text-base font-medium text-ink-gray-9">
            {{ t`${loyaltyPoints} points available` }}
          </p>
          <p class="break-words text-sm text-ink-gray-6">
            {{ loyaltyProgram }}
          </p>
        </div>
      </div>
      <Int
        v-if="sinvDoc.fieldMap"
        :show-label="true"
        :border="true"
        :focus-input="true"
        :value="pendingLoyaltyPoints"
        :df="sinvDoc.fieldMap.loyaltyPoints"
        @keydown.enter="saveLoyaltyPoints"
        @change="setPendingLoyaltyPoints"
      />
    </div>
    <template #actions>
      <Button size="md" class="min-w-24" @click="cancelLoyaltyProgram">{{
        t`Cancel`
      }}</Button>
      <Button
        size="md"
        class="min-w-24"
        type="primary"
        @click="saveLoyaltyPoints"
        >{{ t`Save` }}</Button
      >
    </template>
  </Modal>
</template>

<script lang="ts">
import Button from 'src/components/Button.vue';
import Modal from 'src/components/POS/POSDialog.vue';
import { SalesInvoice } from 'models/baseModels/SalesInvoice/SalesInvoice';
import { defineComponent, inject } from 'vue';
import { t } from 'fyo';
import { showToast } from 'src/utils/interactive';
import { ModelNameEnum } from 'models/types';
import Int from 'src/components/Controls/Int.vue';
import Icon from 'src/components/Icon.vue';

export default defineComponent({
  name: 'LoyaltyProgramModal',
  components: {
    Modal,
    Button,
    Int,
    Icon,
  },
  props: {
    openModal: {
      type: Boolean,
      default: false,
    },
    loyaltyPoints: {
      type: Number,
      default: 0,
    },

    loyaltyProgram: {
      type: String,
      default: '',
    },
  },
  emits: ['setLoyaltyPoints', 'toggleModal'],
  setup() {
    return {
      sinvDoc: inject('sinvDoc') as SalesInvoice,
    };
  },
  data() {
    return {
      validationError: false,
      initialLoyaltyPoints: 0,
      pendingLoyaltyPoints: 0,
    };
  },
  watch: {
    openModal(value: boolean) {
      if (!value) {
        return;
      }

      this.initialLoyaltyPoints = this.sinvDoc.loyaltyPoints ?? 0;
      this.pendingLoyaltyPoints = this.initialLoyaltyPoints;
      this.validationError = false;
    },
  },
  methods: {
    setPendingLoyaltyPoints(value: number) {
      this.pendingLoyaltyPoints = value;
      this.validationError = false;
    },
    cancelLoyaltyProgram() {
      this.sinvDoc.loyaltyPoints = this.initialLoyaltyPoints;
      this.$emit('setLoyaltyPoints', this.initialLoyaltyPoints);
      this.$emit('toggleModal', 'LoyaltyProgram', false);
    },
    async applyLoyaltyPoints(newValue: number): Promise<boolean> {
      try {
        const partyData = await this.fyo.db.get(
          ModelNameEnum.Party,
          this.sinvDoc.party as string
        );

        if (!partyData.loyaltyProgram) {
          throw new Error(t`Customer is not enrolled in a loyalty program`);
        }

        const loyaltyProgramDoc = await this.fyo.db.getAll(
          ModelNameEnum.LoyaltyProgram,
          {
            fields: ['conversionFactor', 'toDate'],
            filters: { name: partyData.loyaltyProgram as string },
          }
        );

        const toDate = loyaltyProgramDoc[0]?.toDate as Date;
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        if (toDate && new Date(toDate).getTime() < today.getTime()) {
          throw new Error(t`Loyalty program has expired and cannot be applied`);
        }

        if (this.loyaltyPoints < newValue) {
          throw new Error(
            `${this.sinvDoc.party as string} only has ${this.loyaltyPoints} points`
          );
        }

        const loyaltyPoint =
          newValue * ((loyaltyProgramDoc[0]?.conversionFactor as number) || 0);

        if (this.sinvDoc.baseGrandTotal?.lt(loyaltyPoint)) {
          throw new Error(t`no need ${newValue} points to purchase this item`);
        }

        if (newValue < 0) {
          throw new Error(t`Points must be greater than 0`);
        }

        this.sinvDoc.loyaltyPoints = newValue;
        this.$emit('setLoyaltyPoints', newValue);

        this.validationError = false;
        return true;
      } catch (error) {
        this.validationError = true;

        showToast({
          type: 'error',
          message: t`${error as string}`,
        });

        return false;
      }
    },
    async saveLoyaltyPoints() {
      const applied = await this.applyLoyaltyPoints(this.pendingLoyaltyPoints);

      if (applied) {
        this.$emit('toggleModal', 'LoyaltyProgram', false);
      }
    },
  },
});
</script>
