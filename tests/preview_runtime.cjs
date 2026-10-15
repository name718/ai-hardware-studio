// Run the actual generated preview script without a browser or network access.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const html = fs.readFileSync(process.argv[2], 'utf8');
const source = html.split('<script>')[1].split('</script>')[0];
let fills = 0;
const ctx = {};
for (const name of ['scale', 'clearRect', 'beginPath', 'moveTo', 'lineTo', 'closePath']) {
  ctx[name] = (...args) => args.forEach(value => assert(Number.isFinite(value)));
}
ctx.fill = () => fills++;
const listeners = {};
const canvas = {
  getContext: () => ctx,
  setPointerCapture() {},
  addEventListener: (name, callback) => { listeners[name] = callback; },
};
const button = {};
const context = {
  innerWidth: 1280, innerHeight: 800,
  window: { devicePixelRatio: 1 },
  document: { querySelector: selector => selector === 'canvas' ? canvas : button },
};
vm.runInNewContext(source, context, { timeout: 5000 });
assert(fills > 100);
const before = fills;
canvas.onpointerdown({ clientX: 200, clientY: 200, pointerId: 1 });
canvas.onpointermove({ clientX: 320, clientY: 280 });
canvas.onpointerup();
listeners.wheel({ deltaY: -300, preventDefault() {} });
button.onclick();
context.window.onresize();
assert(fills > before * 4);
console.log('Preview initial projection, orbit, zoom, reset and resize passed');
