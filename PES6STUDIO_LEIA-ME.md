# PES6 Studio — edição pela interface

Abra `PES6Studio.cmd` com dois cliques. Ele utiliza o Python instalado e a
ISO original da pasta acima. Você também pode arrastar a ISO original sobre
esse iniciador. Mantenha a janela do servidor aberta enquanto usa o Studio.

## Trocar o escudo de uma equipe

1. No Studio, clique em **Clubes, nomes e escudos**.
2. Busque a equipe e selecione-a na lista. Chelsea aparece como
   **Chelsea (London FC)**; o nome dentro do jogo ainda é London FC.
3. Confira as imagens originais de 128×128 e 64×64.
4. Escolha seu PNG externo. Prefira uma arte com transparência e boa definição.
5. Use **Manter proporção e transparência** ou **Preencher toda a área**.
6. Clique em **Importar nas duas resoluções**. O Studio adapta e verifica as
   duas versões antes de aplicar a edição. Confira as prévias convertidas.
7. Clique em **Salvar projeto** para continuar depois.
8. Escolha **ISO para Xenia** ou **IMG para console (experimental)** e clique
   em **Gerar patch verificado**.
9. Use **Abrir pasta do patch** para localizar a saída em `pes6_patches/`.

**Restaurar escudo deste clube** remove somente as edições das duas versões
selecionadas. **Carregar projeto** recupera as alterações previamente salvas.
A galeria e o editor de clubes compartilham o mesmo projeto e o mesmo patch.
Se houver alterações em outros recursos da galeria, elas também serão incluídas.

O Studio mostra quando outros registros apontam para o mesmo recurso; essa
informação vem das referências da tabela, não de imagens que parecem iguais.
Importações ambíguas ou incompletas são bloqueadas. O Chelsea foi confirmado
em jogo pelo usuário; os demais registros mostram o nível de evidência atual.

## Trocar nomes e siglas dentro do jogo

1. Abra **Clubes, nomes e escudos** e selecione a equipe.
2. Preencha **Nome** e **Sigla**. Os contadores mostram o limite em bytes
   disponível para cada campo no executável original. Textos maiores são
   bloqueados para preservar os dados vizinhos.
3. Clique em **Preparar nome e sigla** e depois em **Salvar projeto**.
4. Gere a **ISO para Xenia**. É possível gerar somente nomes ou combiná-los
   com os escudos e demais alterações do projeto.
5. Use **Abrir pasta do patch** e teste o resultado no jogo.

Exemplo que cabe no espaço original: **London FC → Chelsea**, **LDN → CHE**.
**Restaurar nome original** remove somente a edição de nome/sigla da equipe.
As alterações são recuperadas junto com o projeto salvo.

A exportação de nomes altera `default.xex`. Em saída **IMG**, o executável
modificado também é incluído na pasta e é necessário para aplicar os nomes.
A assinatura original do executável não é regenerada; a validação atual é
da reconstrução binária. A execução dos nomes modificados ainda precisa
ser testada no Xenia; console físico não foi validado.

## Editar ligas e competições

1. Abra **Ligas e competições** no menu principal.
2. Selecione um dos nomes identificados no idioma inglês (`rv_e`).
3. Digite o novo nome e clique em **Preparar nome**. Há um limite editorial
   de 64 bytes UTF-8; a capacidade real dos arquivos também é verificada.
4. Para o emblema, escolha visualmente a imagem correspondente na grade.
   As 27 imagens são recursos de competições; sua ordem não determina
   a associação com os nomes da lista. A escolha é manual e fica no projeto.
5. Importe seu PNG, confira a prévia e use **Salvar projeto** e **Gerar patch**.

Escolher uma imagem no editor não altera o vínculo usado pelo motor do jogo:
é preciso identificar a imagem correta antes de substituí-la. Nenhuma
associação liga/emblema é presumida automaticamente. Os textos são alterados
nas duas tabelas identificadas, não nas descrições de conquistas ou em todos
os idiomas. A presença de um nome não cria uma competição selecionável.

O editor aceita o arquivo original `rv_e_limpo.img` ou `rv_e.img` que
corresponda ao hash PAL validado. Se uma entrada precisar crescer, o Studio
utiliza somente o espaço vazio já reservado a ela no AFS, atualiza seu
tamanho no índice e preserva os offsets dos outros arquivos.

## Uniformes e demais recursos

### Jogadores e elencos (v0.15)

1. Abra **Jogadores e elencos** e escolha a base. Comece examinando a 6668,
   que contém o elenco de Chelsea com Ashley Cole, Boulahrouz e Drogba.
   A seleção da base no editor não muda a base carregada pelo jogo.
2. Busque um jogador pelo nome ou ID. Edite o nome no jogo e o nome na
   camisa, depois clique em **Preparar jogador**. Limites: 45 e 15 bytes
   UTF-8, respectivamente. Um caractere acentuado pode ocupar vários bytes.
3. Escolha o elenco e confira a identidade pelos jogadores. Os nomes de
   equipe exibidos são referências, não uma associação validada em partida.
4. Para registrar alguém, selecione o jogador à esquerda e clique em
   **Colocar** na posição desejada. **Remover** libera a posição; ↑ e ↓
   mudam a ordem levando o número junto. Clique em **Preparar elenco**.
5. Para transferir, prepare primeiro o elenco, informe a posição de origem
   (1–32), escolha outro elenco e clique em **Transferir para a primeira
   vaga**. Origem e destino são alterados juntos. Outras inscrições do
   mesmo ID, como a seleção nacional, permanecem.
6. Salve o projeto e gere IMG ou ISO. Os arquivos gerados podem incluir
   alterações de jogadores, clubes, ligas e placares no mesmo patch.

Cada elenco tem 32 posições; 255 no número significa não definido. O editor
rejeita IDs fora da base, jogadores repetidos no mesmo elenco e destino
sem vaga. As bases possuem IDs diferentes: as alterações não são copiadas
automaticamente entre elas. Os registros existentes são editados sem
aumentar a quantidade de jogadores.

Atributos técnicos, físicos, aparência, posição e formação tática são
preservados nesta etapa. A ordem das inscrições não é um editor de tática.
Os testes verificam os arquivos gerados; confira a base realmente usada
em partida e a influência do option file/save antes de atualizar em massa.

### Identificar a base carregada (v0.16)

Na tela **Jogadores e elencos**, escolha o modo de saída IMG ou ISO e clique
em **Gerar teste isolado da base**. O Studio cria uma saída independente com
Lampard renomeado para `Lampard DB6667` em uma base e `Lampard DB6668` na
outra. O nome na camisa também recebe o marcador correspondente.

Use essa saída numa cópia de teste do jogo e confira Lampard no elenco do
Chelsea/London FC e na Inglaterra. Registre o modo e a tela onde o marcador
apareceu: isso identifica a origem daquele nome naquele contexto, sem provar
que todos os modos utilizam a mesma base. Se nenhum aparecer, confira qual
cópia foi aberta e a influência do option file/save. Preserve seus saves.

Esse botão não altera inscrições, atributos ou seu projeto atual, não inclui
as alterações pendentes e não salva os marcadores no projeto. A saída contém
`database_test.json` com os marcadores e instruções. Para voltar ao patch
normal, use **Gerar patch**, sem reutilizar os arquivos do teste isolado.

### Placares e HUD (v0.14)

1. Abra **Placares e HUD** no menu principal.
2. Selecione HUD, placas auxiliares, números ou replay e baixe o PNG original.
3. Edite o PNG externamente, mantendo as dimensões, posições e transparência
   dos elementos. Cada imagem é um atlas com vários recortes usados pelo jogo.
4. Importe o PNG e confira a prévia convertida para a paleta do jogo.
5. Use **Salvar projeto** e **Gerar patch**. A saída inclui o `rv_e.img`
   modificado, ou uma ISO nova, conforme o modo escolhido.

Os números são atualizados nas duas cópias identificadas, nas entradas
249 e 253. As alterações de placar podem ser combinadas com nomes de ligas,
clubes e outros recursos. Se a galeria também modificar a mesma entrada
do placar, o Studio informa o conflito em vez de sobrescrever uma alteração.

Esta versão prepara um único conjunto global. A troca automática conforme
a competição e a edição das coordenadas do placar ainda não estão disponíveis.
Confira o resultado numa partida antes de considerar o placar validado.

Use a galeria para importar artes externas, conferir a prévia, categorizar
recursos e salvar vínculos manuais de equipe/tipo já conferidos. Não há
associação automática de uniformes por ordem de elenco ou por pixels iguais.

Selecionar automaticamente placares por competição ainda não está
disponível. O rótulo Chelsea (London FC)
identifica a equipe na lista; use os campos de nome/sigla e gere o patch
para alterar o texto dentro do jogo.

## Abrir por comando, se necessário

No PowerShell, dentro desta pasta:

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" pes6_studio_v10.py cv_extraido_v03 rv_e_extraido --we00 cv_we00_texturas --iso '..\Pro Evolution Soccer 2006 [PAL].iso'
```

O navegador abre em `http://127.0.0.1:8765`. Se o Python estiver em outro
local, ajuste `PES6PY` no iniciador. Os arquivos originais são preservados;
as importações ficam no projeto e as saídas são criadas em novas pastas.
