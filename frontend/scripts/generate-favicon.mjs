import { deflateSync } from 'node:zlib';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'favicon.png');
const W = 32;
const H = 32;
const SS = 4;

const BARS = [
  { x: 2, y: 24, w: 6, h: 14, color: '#1A1A18' },
  { x: 9.5, y: 16, w: 6, h: 22, color: '#1A1A18' },
  { x: 17, y: 20, w: 6, h: 18, color: '#1A1A18' },
  { x: 24.5, y: 8, w: 6, h: 30, color: '#C9964A' },
  { x: 32, y: 26, w: 6, h: 12, color: '#1A1A18' },
];

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const SW = W * SS;
const SH = H * SS;
const k = SH / 40;

const bars = BARS.map((b) => ({
  x0: b.x * k,
  y0: b.y * k,
  w: b.w * k,
  h: b.h * k,
  rx: (b.w / 3) * k,
  color: hexToRgb(b.color),
}));

function inRoundedRect(px, py, b) {
  if (px < b.x0 || px > b.x0 + b.w || py < b.y0 || py > b.y0 + b.h) return false;
  const cx0 = b.x0 + b.rx;
  const cx1 = b.x0 + b.w - b.rx;
  const cy0 = b.y0 + b.rx;
  const cy1 = b.y0 + b.h - b.rx;
  if ((px >= cx0 && px <= cx1) || (py >= cy0 && py <= cy1)) return true;
  const cxs = px < cx0 ? cx0 : cx1;
  const cys = py < cy0 ? cy0 : cy1;
  const dx = px - cxs;
  const dy = py - cys;
  return dx * dx + dy * dy <= b.rx * b.rx;
}

const ss = new Float64Array(SW * SH * 4);
for (const b of bars) {
  for (let y = 0; y < SH; y++) {
    for (let x = 0; x < SW; x++) {
      if (inRoundedRect(x + 0.5, y + 0.5, b)) {
        const i = (y * SW + x) * 4;
        ss[i] = b.color[0];
        ss[i + 1] = b.color[1];
        ss[i + 2] = b.color[2];
        ss[i + 3] = 255;
      }
    }
  }
}

const pixels = Buffer.alloc(W * H * 4);
for (let y = 0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    let r = 0;
    let g = 0;
    let b = 0;
    let a = 0;
    for (let sy = 0; sy < SS; sy++) {
      for (let sx = 0; sx < SS; sx++) {
        const i = ((y * SS + sy) * SW + (x * SS + sx)) * 4;
        r += ss[i];
        g += ss[i + 1];
        b += ss[i + 2];
        a += ss[i + 3];
      }
    }
    const idx = (y * W + x) * 4;
    if (a > 0) {
      pixels[idx] = Math.round(r / a);
      pixels[idx + 1] = Math.round(g / a);
      pixels[idx + 2] = Math.round(b / a);
    }
    pixels[idx + 3] = Math.round(a / (SS * SS));
  }
}

const crcTable = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) {
    c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  crcTable[n] = c >>> 0;
}

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type, 'ascii');
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])));
  return Buffer.concat([len, typeBuf, data, crc]);
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(W, 0);
ihdr.writeUInt32BE(H, 4);
ihdr[8] = 8;
ihdr[9] = 6;
ihdr[10] = 0;
ihdr[11] = 0;
ihdr[12] = 0;

const stride = W * 4 + 1;
const raw = Buffer.alloc(H * stride);
for (let y = 0; y < H; y++) {
  raw[y * stride] = 0;
  pixels.copy(raw, y * stride + 1, y * W * 4, (y + 1) * W * 4);
}

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk('IHDR', ihdr),
  chunk('IDAT', deflateSync(raw, { level: 9 })),
  chunk('IEND', Buffer.alloc(0)),
]);

writeFileSync(OUT, png);
console.log(`wrote ${OUT} (${png.length} bytes)`);
