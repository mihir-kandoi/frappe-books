import { Fyo, t } from 'fyo';
import { Action, ListViewSettings, ValidationMap } from 'fyo/model/types';
import { ModelNameEnum } from 'models/types';
import {
  getInvoiceActions,
  getTransactionStatusColumn,
} from '../../helpers';
import { Invoice } from '../Invoice/Invoice';
import { SalesInvoiceItem } from '../SalesInvoiceItem/SalesInvoiceItem';
import { LoyaltyProgram } from '../LoyaltyProgram/LoyaltyProgram';
import { DocValue } from 'fyo/core/types';
import { Party } from '../Party/Party';
import { ValidationError } from 'fyo/utils/errors';
import { Money } from 'pesa';
import { Doc } from 'fyo/model/doc';

export class SalesInvoice extends Invoice {
  items?: SalesInvoiceItem[];

  validations: ValidationMap = {
    loyaltyPoints: async (value: DocValue) => {
      if (!this.redeemLoyaltyPoints || this.isSubmitted || this.isReturn) {
        return;
      }

      const partyDoc = (await this.fyo.doc.getDoc(
        ModelNameEnum.Party,
        this.party
      )) as Party;

      if ((value as number) <= 0) {
        throw new ValidationError(t`Points must be greather than 0`);
      }

      if ((value as number) > (partyDoc?.loyaltyPoints || 0)) {
        throw new ValidationError(
          t`${this.party as string} only has ${
            partyDoc.loyaltyPoints as number
          } points`
        );
      }

      const loyaltyProgramDoc = (await this.fyo.doc.getDoc(
        ModelNameEnum.LoyaltyProgram,
        this.loyaltyProgram
      )) as LoyaltyProgram;
      const toDate = loyaltyProgramDoc?.toDate as Date;
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (toDate && new Date(toDate).getTime() < today.getTime()) {
        return;
      }

      if (!this?.grandTotal) {
        return;
      }

      const loyaltyPoint =
        ((value as number) || 0) *
        ((loyaltyProgramDoc?.conversionFactor as number) || 0);

      if (!this.isReturn) {
        const totalDiscount = this.getTotalDiscount();
        let baseGrandTotal;

        if (!this.taxes!.length) {
          baseGrandTotal = (this.netTotal as Money).sub(totalDiscount);
        } else {
          baseGrandTotal = ((this.taxes ?? []) as Doc[])
            .map((doc) => doc.amount as Money)
            .reduce((a, b) => {
              if (this.isReturn) {
                return a.abs().add(b.abs()).neg();
              }
              return a.add(b.abs());
            }, (this.netTotal as Money).abs())
            .sub(totalDiscount);
        }

        if (baseGrandTotal?.lt(loyaltyPoint)) {
          throw new ValidationError(
            t`no need ${value as number} points to purchase this item`
          );
        }
      }
    },
  };

  static getListViewSettings(): ListViewSettings {
    return {
      columns: [
        'name',
        getTransactionStatusColumn(),
        'party',
        'date',
        'baseGrandTotal',
        'outstandingAmount',
      ],
    };
  }

  static getActions(fyo: Fyo): Action[] {
    return getInvoiceActions(fyo, ModelNameEnum.SalesInvoice);
  }
}
