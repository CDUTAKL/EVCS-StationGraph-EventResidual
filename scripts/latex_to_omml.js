#!/usr/bin/env node
/* Convert one LaTeX display formula to a minimal DOCX containing native OMML.
 * Dependencies are deliberately installed in an ephemeral runtime, not the repo.
 */
'use strict';

const fs = require('fs');
const { Document, Packer, Paragraph, Math } = require('docx');
const temml = require('temml');
const { mathmlToDocxChildren } = require('/Users/xushuyuan/.codex/skills/docx-editor-cn/scripts/mathml-to-docx.js');

async function main() {
  const latex = fs.readFileSync(0, 'utf8').trim();
  const mathml = temml.renderToString(latex, { displayMode: true, throwOnError: false });
  const children = mathmlToDocxChildren(mathml, { libreOfficeCompat: false });
  const doc = new Document({
    sections: [{ children: [new Paragraph({ children: [new Math({ children })] })] }],
  });
  const buffer = await Packer.toBuffer(doc);
  process.stdout.write(buffer.toString('base64'));
}

main().catch((error) => { console.error(error.stack || error); process.exit(1); });
