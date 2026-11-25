# PES6 Studio 360

Editor local para pesquisar e preparar patches da edição PAL de **Pro
Evolution Soccer 6 para Xbox 360**, com interface no navegador e backend
Python. Projeto PatchPES6.

## Funcionalidades

- Galeria DDS/WE00, categorias, prévias e importação de texturas externas.
- Editor de escudos com conversão para as duas resoluções e verificação
  de capacidade antes de aplicar as alterações.
- Edição de nomes e siglas de equipes, limitada ao espaço original de texto.
- Editor de nomes de ligas/competições no idioma inglês e seleção manual
  do emblema de competição a editar.
- Tela de placares e HUD: exportação/importação dos atlas PNG, prévia
  convertida e atualização conjunta das duas cópias dos números.
- Jogadores e elencos: nomes, nomes na camisa, inscrições, ordem, números
  e transferências entre elencos, com bases 6667/6668 independentes.
- Edição de 26 valores de habilidades, preservando os bits vizinhos;
  os rótulos comparados ao formato PC ainda exigem conferência no Xbox 360.
- Tela de uniformes com duas partes independentes por entrada, importação
  conjunta com verificação de capacidade e prévia conferida na exportação.
- Projetos salvos com vínculo às fontes; exportação de ISO ou arquivos
  modificados para uma instalação extraída.

As fontes originais são preservadas. Os vínculos de uniformes são manuais;
o programa não deduz equivalência de recursos por imagens iguais.
O editor de uniformes não identifica automaticamente clube, principal,
reserva ou goleiro. Vínculos manuais organizam o catálogo; não mudam o
recurso escolhido pelo jogo. A validação em partida continua pendente.

## Requisitos e arquivos locais

Python 3.12 ou superior. Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Use sua própria cópia PAL do jogo. Os arquivos abaixo **não estão neste
repositório** e devem permanecer apenas na máquina do usuário:

- `default.xex` e `cv.img` originais.
- `rv_e.img` original ou `rv_e_limpo.img` original verificado.
- `cv_extraido_v03/` e `rv_e_extraido/`: saídas da extração local.
- `cv_we00_texturas/`, incluindo `index.csv`: catálogo WE00 local.
- ISO original, por padrão na pasta acima com o nome
  `Pro Evolution Soccer 2006 [PAL].iso`.

Ferramentas de extração e de geração do catálogo estão nos scripts
`pes6_extrator_v03.py` e `pes6_we00_catalogo.py`; consulte `--help`.
O perfil de nomes de clubes exige o hash do XEX PAL identificado no código.
O editor de ligas exige a versão original verificada de `rv_e`.

## Abrir e usar

No Windows, dê dois cliques em `PES6Studio.cmd`, ou arraste a ISO original
para esse arquivo. Se necessário, ajuste o caminho de Python no iniciador.

Também é possível abrir por comando:

```powershell
python pes6_studio_v10.py cv_extraido_v03 rv_e_extraido --we00 cv_we00_texturas --iso '..\Pro Evolution Soccer 2006 [PAL].iso'
```

A interface abre em `http://127.0.0.1:8765`. Veja
[o guia de uso](PES6STUDIO_LEIA-ME.md) para escudos, nomes e ligas.

## Evidência e limites

O escudo do Chelsea foi confirmado em jogo pelo usuário. Edição de nomes,
nomes de ligas e associação de emblemas de competições exigem conferência
do usuário na versão e nas telas utilizadas. A presença de um nome nos
arquivos não cria uma nova competição nem comprova que ela seja selecionável.

Emblemas de ligas são selecionados visualmente pelo usuário; IDs de texto
não são tratados como IDs de imagem ou de competição. Uniformes devem ser
criados externamente e vinculados somente depois de conferência.

Nomes de clubes modificam o XEX, que é reconstruído e verificado, mas não
é re-assinado. Compatibilidade com console físico não foi validada.
Veja [ENGINEERING.md](ENGINEERING.md) para formatos, fontes e comandos.

Os placares usam um conjunto global de texturas. A troca automática por
competição ainda exige identificar o estado da competição e implementar
a seleção no executável Xbox 360; o módulo Kitserver de PC não funciona
diretamente nessa plataforma. Os layouts e posições do HUD não são editados
nesta versão. Alterações de placar ainda precisam de validação em partida.

O editor de jogadores preserva os atributos ainda não identificados; não
edita idade, aparência ou formação tática. A base ativa em
partida precisa ser confirmada: IDs de 6667 e 6668 não são intercambiáveis.
Os nomes de equipes mostrados em 6668 são referências para conferir pelo
elenco. Option files/saves do jogo podem influenciar o resultado observado.

## Testes e versionamento

```powershell
python -m unittest discover
```

Os testes independentes dos dados rodam sem os arquivos do jogo. Testes com
binários reais são ignorados quando as fontes locais não estão disponíveis.
ISOs, IMG, XEX, texturas, projetos pessoais, saídas de patch, emuladores e
pesquisa gerada estão excluídos pelo `.gitignore`. Apenas código e
documentação do projeto são versionados.

Na cópia de desenvolvimento original, este ambiente restringe escrita em
`.git/`. Os metadados locais ficam separados em `research/versioning/` e
podem ser utilizados com `GitStudio.cmd status`, `GitStudio.cmd log` etc.
Uma clonagem normal do GitHub usa o Git convencional; o helper detecta
automaticamente quando os metadados separados não estão presentes.
