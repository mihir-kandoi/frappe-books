import standardChart from 'fixtures/verified/standardCOA.json';
import { TranslationString } from 'fyo/utils/translation';

const standardNames = new Set<string>();
collectNames(standardChart);

export function getAccountLabel(name: string): string {
  if (!standardNames.has(name)) return name;
  return TranslationString.prototype.languageMap?.[name]?.translation || name;
}

function collectNames(tree: Record<string, unknown>) {
  for (const [name, value] of Object.entries(tree)) {
    if (value && typeof value === 'object') {
      standardNames.add(name);
      collectNames(value as Record<string, unknown>);
    }
  }
}
