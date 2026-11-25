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
