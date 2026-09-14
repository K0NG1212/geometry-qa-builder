from pathlib import Path

def check_units(b, units, bundle):
    b.validate(units, b.read(Path(__file__).with_name('schema.json')))
    sources = b.bundle_check(bundle)
    for asset in b.unique(units['assets'], 'source_id').values():
        if asset['source_id'] not in sources or sources[asset['source_id']]['kind'] != 'xyz':
            raise ValueError('units: unknown XYZ asset')
        if asset['unit'] == 'angstrom':
            if not asset['checked_by'].strip():
                raise ValueError('units: missing checker identity')
            b.check_refs(asset['source_refs'], sources)
        elif asset['source_refs']:
            b.check_refs(asset['source_refs'], sources)

def prepare(b, args):
    sources=[]; warnings=[]
    for filename in args.source:
        path=Path(filename)
        if path.suffix.lower()=='.pdf':
            try: from pypdf import PdfReader
            except ImportError: raise ValueError('PDF requires pypdf; alternatively supply extracted UTF-8 text')
            warnings.append(path.name+': text-only PDF extraction; images and table layout NOT validated')
            chunks=[(f'page {i+1}',page.extract_text() or '') for i,page in enumerate(PdfReader(path).pages)]
        else:
            lines=path.read_text(encoding='utf-8-sig').splitlines()
            chunks=[(f'lines {i+1}-{min(i+60,len(lines))}','\n'.join(lines[i:i+60])) for i in range(0,len(lines),60)]
        for loc,text in chunks:
            if not text.strip(): warnings.append(path.name+' '+loc+': empty'); continue
            sources.append({'source_id':f'S{len(sources)+1:04}','location':path.name+' '+loc,'origin':str(path.resolve()),'kind':'text','text':text})
    for filename in args.xyz:
        path=Path(filename); text=path.read_text(encoding='utf-8-sig'); b.parse_xyz(text)
        sources.append({'source_id':f'S{len(sources)+1:04}','location':path.name+' XYZ (unit recorded separately)','origin':str(path.resolve()),'kind':'xyz','text':text})
    bundle={'paper_id':args.paper_id,'title':args.title,'url':args.url,'synthetic':args.synthetic,'sources':sources,'warnings':warnings}
    b.bundle_check(bundle)
    if Path(args.out).exists(): raise ValueError('output already exists; choose a new file')
    b.write(args.out,bundle)
