#!/usr/bin/env node
/* Convert one LaTeX display formula to a minimal DOCX containing native OMML.
 * Dependencies are deliberately installed in an ephemeral runtime, not the repo.
 */
'use strict';

const fs = require('fs');
const { Document, Packer, Paragraph, Math, XmlComponent, XmlAttributeComponent } = require('docx');
const { XMLParser, XMLBuilder } = require('fast-xml-parser');
const temml = require('temml');
const { mathmlToDocxChildren } = require('/Users/xushuyuan/.codex/skills/docx-editor-cn/scripts/mathml-to-docx.js');

class AccentAttributes extends XmlAttributeComponent {
  constructor(value) {
    super({ value });
    this.xmlKeys = { value: 'm:val' };
  }
}

function convertPreservingAccents(mathml) {
  const options = { preserveOrder: true, ignoreAttributes: false, attributeNamePrefix: '', textNodeName: 'text', trimValues: false };
  const parser = new XMLParser(options);
  const builder = new XMLBuilder(options);
  const accents = new Map();
  const lowerLimits = new Map();
  const glyphs = new Map([['ˆ', '\u0302'], ['^', '\u0302'], ['~', '\u0303'], ['˜', '\u0303'], ['¯', '\u0304'], ['→', '\u20d7']]);
  const tagOf = node => Object.keys(node).find(key => key !== ':@' && key !== 'text');
  const plain = nodes => nodes.map(node => node.text || plain(node[tagOf(node)] || [])).join('');
  function prepare(nodes) {
    return nodes.map(node => {
      const tag = tagOf(node);
      if (!tag) return node;
      const children = prepare(node[tag]);
      if (tag === 'mover' && children.length === 2 && glyphs.has(plain([children[1]]))) {
        const token = `NATIVEACCENT${accents.size}TOKEN`;
        accents.set(token, { base: children[0], glyph: glyphs.get(plain([children[1]])) });
        return { mi: [{ text: token }] };
      }
      // The bundled walker flattens munder for textual operators. Preserve
      // the optimization variable underneath min/max as editable OMML.
      if (tag === 'munder' && children.length === 2 && ['min', 'max'].includes(plain([children[0]]))) {
        const token = `NATIVELOWERLIMIT${lowerLimits.size}TOKEN`;
        lowerLimits.set(token, { base: children[0], lower: children[1] });
        return { mi: [{ text: token }] };
      }
      return { ...node, [tag]: children };
    });
  }
  const prepared = builder.build(prepare(parser.parse(mathml)));
  function restore(component) {
    if (!component || !Array.isArray(component.root)) return component;
    if (component.rootKey === 'm:r') {
      const text = component.root.filter(child => child.rootKey === 'm:t').flatMap(child => child.root).join('');
      const payload = accents.get(text);
      const lower = lowerLimits.get(text);
      if (lower) {
        const limit = new XmlComponent('m:limLow');
        limit.root.push(new XmlComponent('m:limLowPr'));
        for (const [tag, value] of [['m:e', lower.base], ['m:lim', lower.lower]]) {
          const expression = new XmlComponent(tag);
          const fragment = `<math><mrow>${builder.build([value])}</mrow></math>`;
          expression.root.push(...mathmlToDocxChildren(fragment, { libreOfficeCompat: false }).map(restore));
          limit.root.push(expression);
        }
        return limit;
      }
      if (payload) {
        const accent = new XmlComponent('m:acc');
        const properties = new XmlComponent('m:accPr');
        const character = new XmlComponent('m:chr');
        character.root.push(new AccentAttributes(payload.glyph));
        properties.root.push(character);
        const expression = new XmlComponent('m:e');
        const baseXml = `<math><mrow>${builder.build([payload.base])}</mrow></math>`;
        expression.root.push(...mathmlToDocxChildren(baseXml, { libreOfficeCompat: false }).map(restore));
        accent.root.push(properties, expression);
        return accent;
      }
    }
    component.root = component.root.map(restore);
    return component;
  }
  return mathmlToDocxChildren(prepared, { libreOfficeCompat: false }).map(restore);
}

async function main() {
  const latex = fs.readFileSync(0, 'utf8').trim();
  const rendered = temml.renderToString(latex, { displayMode: true, throwOnError: true });
  // The bundled walker chooses the first descendant mrow. A root msup/msub
  // can therefore lose its base and keep only the script's inner mrow.
  // An explicit outer row makes the actual full expression the walk root.
  const mathml = rendered.replace(/(<math\b[^>]*>)/, '$1<mrow>')
    .replace(/<\/math>\s*$/, '</mrow></math>');
  const children = convertPreservingAccents(mathml);
  const doc = new Document({
    sections: [{ children: [new Paragraph({ children: [new Math({ children })] })] }],
  });
  const buffer = await Packer.toBuffer(doc);
  process.stdout.write(buffer.toString('base64'));
}

main().catch((error) => { console.error(error.stack || error); process.exit(1); });
