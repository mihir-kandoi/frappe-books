import { getDocStatus } from 'models/helpers';
import { RenderData } from 'fyo/model/types';

export function matchesStatus(row: RenderData, filter: unknown): boolean {
  const [operator, expected] = Array.isArray(filter)
    ? filter
    : ['=', filter];
  const status = getDocStatus(row).toLowerCase();
  const value = String(expected ?? '').toLowerCase();
  switch (operator) {
    case '=':
      return status === value;
    case '!=':
      return status !== value;
    case 'like':
      return status.includes(value);
    case 'not like':
      return !status.includes(value);
    case '>':
      return status > value;
    case '<':
      return status < value;
    case 'is null':
      return status === '';
    case 'is not null':
      return status !== '';
    default:
      throw new Error(
        `Unsupported status filter operator: ${String(operator)}`
      );
  }
}
