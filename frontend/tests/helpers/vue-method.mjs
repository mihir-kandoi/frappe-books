import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';

export async function loadMethod(relativePath, name, context) {
  const text = await readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8');
  const script = text.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
  const source = ts.createSourceFile('component.ts', script, ts.ScriptTarget.Latest, true);
  let method;
  function visit(node) {
    if (ts.isMethodDeclaration(node) && node.name.getText(source) === name) method = node.getText(source);
    ts.forEachChild(node, visit);
  }
  visit(source);
  if (!method) throw new Error(`Method ${name} not found`);
  method = method.replace("await import('src/utils/ui')", 'await openUi()');
  const { outputText } = ts.transpileModule(`({${method}}).${name}`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  });
  return vm.runInNewContext(outputText, context);
}
