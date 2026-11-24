// Build-only conversion: no SVG engine or network access is needed by Diolino.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('../online/site/node_modules/sharp');
const directory = path.resolve(__dirname, '../assets/visual/lucide');
(async () => {
  for (const name of fs.readdirSync(directory).filter(n => n.endsWith('.svg'))) {
    const source = fs.readFileSync(path.join(directory, name), 'utf8');
    if (/<script|foreignObject|href\s*=|url\s*\(/i.test(source)) throw Error('Unexpected active SVG content: '+name);
    await sharp(Buffer.from(source.replace('stroke-width="2"', 'stroke-width="1.65"').replace('currentColor', '#ffffff')))
      .resize(144, 144).png().toFile(path.join(directory, name.replace('.svg', '.png')));
  }
})();
