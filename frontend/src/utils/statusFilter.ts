import {
  getDocStatus,
  getStatusText,
  getLoyaltyProgramStatus,
  getLoyaltyProgramStatusText,
} from 'models/helpers';
import { RenderData } from 'fyo/model/types';

export function matchesStatus(row: RenderData, filter: unknown): boolean {
  const conditions = Array.isArray(filter) ? filter : ['=', filter];
  if (!conditions.length || conditions.length % 2)
    throw new Error('Invalid status filter');
  const isLoyaltyProgram = row.schema?.name === 'LoyaltyProgram';
  const status = isLoyaltyProgram
    ? getLoyaltyProgramStatus(row)
    : getDocStatus(row);
  const label = (
    isLoyaltyProgram
      ? getLoyaltyProgramStatusText(status)
      : getStatusText(status as ReturnType<typeof getDocStatus>)
  ).toLowerCase();
  for (let index = 0; index < conditions.length; index += 2) {
    if (
      !matchesCondition(
        label,
        status.toLowerCase(),
        conditions[index],
        conditions[index + 1]
      )
    )
      return false;
  }
  return true;
}

function matchesCondition(
  label: string,
  status: string,
  operator: string,
  expected: unknown
): boolean {
  const value = String(expected ?? '').toLowerCase();
  switch (operator) {
    case '=':
      return label === value || status === value;
    case '!=':
      return label !== value && status !== value;
    case 'like':
      return matchesPattern(label, value) || matchesPattern(status, value);
    case 'not like':
      return !matchesPattern(label, value) && !matchesPattern(status, value);
    case '>':
      return label > value;
    case '<':
      return label < value;
    case 'is null':
      return label === '';
    case 'is not null':
      return label !== '';
    default:
      throw new Error(
        `Unsupported status filter operator: ${String(operator)}`
      );
  }
}

function matchesPattern(value: string, pattern: string) {
  const escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(
    `^${escaped.replace(/%/g, '[\\s\\S]*').replace(/_/g, '[\\s\\S]')}$`,
    'iu'
  ).test(value);
}
