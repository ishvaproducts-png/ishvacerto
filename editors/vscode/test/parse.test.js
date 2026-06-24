// Headless unit test for the pure parseVerdict() exported by extension.js.
// Plain node (node test/parse.test.js) -- no VS Code, no test framework, no npm deps.
// extension.js guards its require('vscode') so importing it here does NOT pull in vscode.

'use strict';

const assert = require('assert');
const { parseVerdict } = require('../extension.js');

let passed = 0;
function check(name, fn) {
  fn();
  passed += 1;
  console.log('ok - ' + name);
}

check('parses VERIFIED', () => {
  const json = JSON.stringify({
    verdict: 'VERIFIED', entry_point: 'square', spec_source: 'doctest',
    counterexample: '', detail: { n_examples: 2 },
  });
  const v = parseVerdict(json);
  assert.strictEqual(v.verdict, 'VERIFIED');
  assert.strictEqual(v.entry_point, 'square');
  assert.strictEqual(v.spec_source, 'doctest');
  assert.strictEqual(v.counterexample, '');
});

check('parses REFUTED with counterexample + got/expected', () => {
  const json = JSON.stringify({
    verdict: 'REFUTED', entry_point: 'square', spec_source: 'doctest',
    counterexample: 'square(3)', detail: { got: 6, expected: 9 },
  });
  const v = parseVerdict(json);
  assert.strictEqual(v.verdict, 'REFUTED');
  assert.strictEqual(v.counterexample, 'square(3)');
  assert.strictEqual(v.detail.got, 6);
  assert.strictEqual(v.detail.expected, 9);
});

check('parses ABSTAIN', () => {
  const json = JSON.stringify({
    verdict: 'ABSTAIN', entry_point: 'my_func', spec_source: '',
    counterexample: '', detail: { reason: 'no clean spec capturable' },
  });
  const v = parseVerdict(json);
  assert.strictEqual(v.verdict, 'ABSTAIN');
  assert.strictEqual(v.entry_point, 'my_func');
  assert.strictEqual(v.counterexample, '');
});

check('tolerates trailing newline / surrounding whitespace', () => {
  const v = parseVerdict('\n  {"verdict":"VERIFIED","entry_point":"f"}  \n');
  assert.strictEqual(v.verdict, 'VERIFIED');
  assert.strictEqual(v.entry_point, 'f');
});

check('missing optional fields default to empty', () => {
  const v = parseVerdict('{"verdict":"ABSTAIN"}');
  assert.strictEqual(v.entry_point, '');
  assert.strictEqual(v.spec_source, '');
  assert.deepStrictEqual(v.detail, {});
});

check('throws on non-JSON', () => {
  assert.throws(() => parseVerdict('not json at all'), /no JSON object/);
});

check('throws on JSON without a verdict field', () => {
  assert.throws(() => parseVerdict('{"entry_point":"f"}'), /missing "verdict"/);
});

console.log('\n' + passed + '/' + passed + ' parse tests passed');
