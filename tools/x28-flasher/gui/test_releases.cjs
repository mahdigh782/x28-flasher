// Run: node tools/x28-flasher/gui/test_releases.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const source = html.slice(html.indexOf('function viewBuild()'), html.indexOf('\nconst WRITES'));
const S = { st: { build: { docker: true, backups: [] } }, releases: [
  { tag: 'v2-beta', beta: true, signed: true, date: '' },
  { tag: 'v1', beta: false, signed: true, date: '' },
] };
const head = () => '', esc = (s) => s, busy = () => false;
// Compile the actual view, with only its rendering dependencies stubbed.
const render = new Function('S', 'head', 'esc', 'busy', `${source}; return viewBuild();`);
for (const src of ['release', 'backup']) {
  S.bdSource = src;
  S.bdBeta = false;
  let view = render(S, head, esc, busy);
  assert(view.includes('value="v1"'));
  assert(!view.includes('value="v2-beta"'));
  S.bdBeta = true;
  view = render(S, head, esc, busy);
  assert(view.includes('value="v1"'));
  assert(view.includes('value="v2-beta"'));
}
S.releases = S.releases.filter((r) => r.beta);
S.bdBeta = false;
const view = render(S, head, esc, busy);
assert(!view.includes('value="v2-beta"'));
assert(view.includes('id="bd-go" data-act="build" disabled'));
console.log('release filtering ok');
