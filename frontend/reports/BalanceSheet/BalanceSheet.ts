import { t } from 'fyo';
import {
  AccountRootType,
  AccountRootTypeEnum,
} from 'models/baseModels/Account/types';
import {
  AccountReport,
  convertAccountRootNodesToAccountList,
} from 'reports/AccountReport';
import {
  AccountNameValueMapMap,
  GroupedMap,
  ReportData,
  RootTypeRow,
  ValueMap,
} from 'reports/types';
import { isCredit } from 'models/helpers';
import { QueryFilter } from 'utils/db/types';
import { getMapFromList } from 'utils';

export class BalanceSheet extends AccountReport {
  static title = t`Balance Sheet`;
  static reportName = 'balance-sheet';
  loading = false;

  override async _getQueryFilters(): Promise<QueryFilter> {
    const { toDate } = await this._getFromAndToDates();
    return { date: ['<', toDate], reverted: false };
  }

  override async _getGroupedByDateRanges(
    map: GroupedMap
  ): Promise<AccountNameValueMapMap> {
    const accounts = await this._setAndReturnAccountMap();
    const result: AccountNameValueMapMap = new Map();
    for (const [account, entries] of map) {
      const values: ValueMap = new Map();
      const direction = isCredit(accounts[account]?.rootType) ? -1 : 1;
      const sorted = [...entries].sort(
        (a, b) => a.date!.getTime() - b.date!.getTime()
      );
      let index = 0;
      let balance = 0;
      for (const range of this._dateRanges!) {
        const end = range.toDate.toISODate();
        while (
          index < sorted.length &&
          sorted[index].date!.toISOString().slice(0, 10) < end
        ) {
          const entry = sorted[index++];
          balance +=
            direction * ((entry.debit ?? 0) - (entry.credit ?? 0));
        }
        values.set(range, { balance });
      }
      result.set(account, values);
    }
    return result;
  }

  get rootTypes(): AccountRootType[] {
    return [
      AccountRootTypeEnum.Asset,
      AccountRootTypeEnum.Liability,
      AccountRootTypeEnum.Equity,
    ];
  }

  async setReportData(filter?: string, force?: boolean) {
    this.loading = true;
    if (force || filter !== 'hideGroupAmounts') {
      await this._setRawData();
    }

    const map = this._getGroupedMap(true, 'account');
    const rangeGroupedMap = await this._getGroupedByDateRanges(map);
    const accountTree = await this._getAccountTree(rangeGroupedMap);

    for (const name of Object.keys(accountTree)) {
      const { rootType } = accountTree[name];
      if (this.rootTypes.includes(rootType)) {
        continue;
      }

      delete accountTree[name];
    }

    const rootTypeRows: RootTypeRow[] = this.rootTypes
      .map((rootType) => {
        const rootNodes = this.getRootNodes(rootType, accountTree)!;
        const rootList = convertAccountRootNodesToAccountList(rootNodes);
        return {
          rootType,
          rootNodes,
          rows: this.getReportRowsFromAccountList(rootList),
        };
      })
      .filter((row) => !!row.rootNodes.length);

    this.reportData = this.getReportDataFromRows(
      getMapFromList(rootTypeRows, 'rootType')
    );
    this.loading = false;
  }

  getReportDataFromRows(
    rootTypeRows: Record<AccountRootType, RootTypeRow | undefined>
  ): ReportData {
    const typeNameList = [
      {
        rootType: AccountRootTypeEnum.Asset,
        totalName: t`Total Asset (Debit)`,
      },
      {
        rootType: AccountRootTypeEnum.Liability,
        totalName: t`Total Liability (Credit)`,
      },
      {
        rootType: AccountRootTypeEnum.Equity,
        totalName: t`Total Equity (Credit)`,
      },
    ];

    const reportData: ReportData = [];
    const emptyRow = this.getEmptyRow();
    for (const { rootType, totalName } of typeNameList) {
      const row = rootTypeRows[rootType];
      if (!row) {
        continue;
      }

      reportData.push(...row.rows);

      if (row.rootNodes.length) {
        const totalNode = this.getTotalNode(row.rootNodes, totalName);
        const totalRow = this.getRowFromAccountListNode(totalNode);
        reportData.push(totalRow);
      }

      reportData.push(emptyRow);
    }

    if (reportData.at(-1)?.isEmpty) {
      reportData.pop();
    }

    return reportData;
  }
}
