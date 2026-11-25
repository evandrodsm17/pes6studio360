"""Shared presentation shell for the local Xbox 360 editor."""
import html
import re

VERSION='0.19'
PAGES={
    'gallery':('/', 'Texturas', 'Biblioteca de texturas', 'Explore os recursos do jogo e prepare cada detalhe do seu patch.'),
    'clubs':('/clubs','Clubes','Clubes e identidades','Nomes, siglas e escudos para dar identidade às suas equipes.'),
    'kits':('/kits','Uniformes','Uniformes','Do atlas original à nova identidade em campo.'),
    'leagues':('/leagues','Competições','Ligas e competições','Organize nomes e emblemas das competições.'),
    'players':('/players','Jogadores','Jogadores e elencos','Atualize jogadores, inscrições e habilidades em um só lugar.'),
    'scoreboards':('/scoreboards','Placares','Placares e HUD','Personalize a apresentação das partidas.'),
    'profiles':('/profiles','Pesquisa','Pesquisa e perfis','Inspecione as estruturas e acompanhe as evidências do projeto.'),
}
ICONS={
    'gallery':'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'clubs':'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    'kits':'<path d="m8 3-5 4 3 4 2-1v11h8V10l2 1 3-4-5-4c-1 3-7 3-8 0Z"/>',
    'leagues':'<path d="M8 3h8v5a4 4 0 0 1-8 0zM8 5H4v2a4 4 0 0 0 5 4m7-6h4v2a4 4 0 0 1-5 4M12 12v6m-4 3h8m-9 0 1-3h8l1 3"/>',
    'players':'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6m1 5a5 5 0 0 1 3 5"/>',
    'scoreboards':'<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M12 8v8m-6-5h2v3H6m10-3h2v3h-2"/>',
    'profiles':'<path d="m10 3-7 9 7 9m4-18 7 9-7 9M14 7l-4 10"/>',
}


def icon(page):
    return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">'+ICONS[page]+'</svg>'


def themed(document,page):
    """Keep editor DOM IDs and scripts intact while adding shared app navigation."""
    if page not in PAGES:raise ValueError('Unknown Studio page')
    document=document.replace('\x07',' · ').replace('\x18','↑').replace('\x19','↓')
    split=document.index('</style>')+len('</style>')
    head,content=document[:split],document[split:]
    content=content.rsplit('</html>',1)[0]
    content=re.sub(r'^\s*<nav>.*?</nav>','',content,count=1,flags=re.S)
    if page=='gallery':
        content=content.replace('<p>ISO original: <strong id="isoPath"></strong></p>',
            '<details class="studio-source"><summary>Arquivo de origem</summary><p><strong id="isoPath"></strong></p></details>')
        content=content.replace('<div style="position:fixed;bottom:0;', '<div class="studio-buildbar" style="position:fixed;bottom:0;',1)
        content=content.replace('<header>','<header><div class="filters-heading"><span>Encontre um recurso</span><small>Filtre, confira e personalize</small></div>',1)
    nav=[]
    for key,(url,label,_,_) in PAGES.items():
        current=' aria-current="page"' if key==page else ''
        nav.append(f'<a class="studio-nav-link" href="{url}"{current}>{icon(key)}<span>{label}</span></a>')
    _,_,title,description=PAGES[page]
    sidebar='<aside class="studio-sidebar"><a class="studio-brand" href="/" aria-label="PES6 Studio 360, início"><img src="/assets/pes6studio360-logo.png" alt="" width="60" height="60"><span><strong>PES6</strong><span>STUDIO <b>360</b></span></span></a><div class="studio-nav-caption">SEU PATCH</div><nav class="studio-navigation" aria-label="Navegação principal">'+''.join(nav)+'</nav><div class="studio-sidebar-footer"><span class="console-light"></span><div><strong>Xbox 360 Edition</strong><small>Editor local · v'+VERSION+'</small></div></div></aside>'
    masthead='<div class="studio-masthead"><span>OFICINA DE MODIFICAÇÕES <b>/</b> PES6</span><span class="studio-platform"><i></i> XBOX 360</span></div>'
    intro=f'<div class="studio-page-heading"><div class="studio-page-symbol">{icon(page)}</div><div><h1>{html.escape(title)}</h1><p>{html.escape(description)}</p></div></div>'
    meta='' if 'name="viewport"' in head else '<meta name="viewport" content="width=device-width,initial-scale=1">'
    assets=f'{meta}<link rel="icon" type="image/png" href="/assets/pes6studio360-logo.png"><link rel="stylesheet" href="/assets/studio.css?v={VERSION}">'
    return head+assets+f'<body class="studio-shell page-{page}">'+sidebar+'<div class="studio-workspace">'+masthead+intro+'<div class="studio-content">'+content+'</div><div class="studio-workspace-footer">PES6 STUDIO 360<span>FEITO PARA PERSONALIZAR O SEU JOGO</span></div></div></body></html>'
