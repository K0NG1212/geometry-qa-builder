'use strict';
// Links to the paper or database a question came from. Two thirds of the sources are a citation
// ("..., doi:10.3390/molecules21010016 (Europe PMC PMC6274253)"), not a URL, and index.html put that whole
// string into href=: 151 questions had a dead source link until 2026-10-30. Only a real URL may be linked, so
// the link is taken from the citation itself -- a URL inside it, else its DOI, PMCID or arXiv id, else the
// resource page the question is filed under. The citation text is always shown as well.
// Returns [[label, url], ...], empty if the citation carries no identifier at all.
function sourceLinks(source, name, page) {
 source = source || '';
 if (/^https?:\/\//.test(source.trim())) return [[(name ? name + ' ' : '') + '原始来源 ↗', source.trim()]];
 const inside = [...new Set(source.match(/https?:\/\/[^\s;,，、）)]+/g) || [])].slice(0, 3);
 if (inside.length) return inside.map(u => [new URL(u).hostname.replace(/^www\./, '') + ' ↗', u]);
 const out = [], doi = source.match(/\bdoi:?\s*(10\.\S+?)(?:[\s;,，（(。]|$)/i),
  pmc = source.match(/\b(PMC\d+)\b/), arxiv = source.match(/arXiv:\s*(\d{4}\.\d{4,5})/i);
 if (doi) out.push(['DOI ' + doi[1] + ' ↗', 'https://doi.org/' + doi[1]]);
 if (pmc) out.push(['Europe PMC ' + pmc[1] + ' ↗', 'https://europepmc.org/article/PMC/' + pmc[1]]);
 if (arxiv) out.push(['arXiv ' + arxiv[1] + ' ↗', 'https://arxiv.org/abs/' + arxiv[1]]);
 return out.length ? out : page ? [[(name ? name + ' ' : '') + '资源页 ↗', page]] : [];
}
