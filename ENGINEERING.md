# PatchPES6 / PES6 Studio

## 2026-11-24 — Uniform source verification

The current Studio entry point is `pes6_studio_v10.py`. Its `/research`
endpoint uses `pes6_evidence.load_evidence`. This now verifies the binary
hashes of all 820 candidate texture parts in entries 5736–6145 against
`research/kit_candidates.csv`, in addition to the database entries listed
in `research/evidence.json`.

Each candidate is verified independently. Equal pixel hashes do not imply
equivalent resources, and do not cause replacement or team assignments.
Missing, duplicate, out-of-range, changed or incomplete candidates fail
verification. Verification streams one unpacked entry at a time.

### Confirmed byte evidence

- AFS offsets and sizes are read from the little-endian AFS index in `cv.img`.
- Entry 5736 begins at AFS offset 509667328. Its unpacked parts start at
  offsets 32 and 263216, each with size 263184 bytes.
- Candidate WE00 headers are `57453030100403080200020000100410`.
- The complete per-part offsets and SHA-256 hashes are recorded in
  `research/kit_candidates.csv`. Part offsets refer to the unpacked entry,
  not absolute positions in the compressed IMG.
- `research/source_verification.json` records the verification result,
  database entry source hashes, and hashes of the reports and verifier used.

### Unconfirmed semantics

No team-to-kit association is confirmed. The roster slots in 6667/6668
and the 728-byte candidate records in 6670 are insufficient to establish
graphic IDs. The arithmetic relation `410 = 2 * (189 + 16)` remains a
hypothesis and must not be used to patch or assign teams.

### Reproduce on Windows PowerShell

Run from the project directory. If `python` resolves to an inaccessible
Windows Store alias, use the installed interpreter:

```powershell
$pesPython = 'C:\Users\evandro.mota\AppData\Local\Python\pythoncore-3.14-64\python.exe'
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence
& $pesPython -c "from pathlib import Path; from pes6_evidence import load_evidence; print(load_evidence(Path('.'),Path('research/evidence.json'))['kit_verification'])"
& $pesPython pes6_studio_v10.py cv_extraido_v03 rv_e_extraido --we00 cv_we00_texturas --iso '..\Pro Evolution Soccer 2006 [PAL].iso'
```

Validation: 16 tests passed, including real IMG/extracted binaries and
malformed candidate catalogs. No runtime confirmation in Xenia was performed.
Original ISO, IMG, executable and extracted sources were not modified.

## 2026-11-24 — Studio profile inspector

The Studio header now opens `/profiles` in a separate tab so current edits
remain in the gallery. `/profiles/data` reads entry 6670 directly from
`cv.img`, validates the WESYS/parts structure and the observed 728-byte
layout, and returns source and part SHA-256 hashes with raw words,
metadata and field distributions. It does not read an assumed team order
or assign kit resources.

There are 189 records in part 0 (137592 bytes) and 16 in part 1
(11648 bytes). For record R and subrecord S, the offset in its part is
`728 * R + 108 * S`. Words occupy offsets 0–83 of each subrecord as
21 big-endian 16-bit values, each followed by two zero bytes. Metadata
occupies offsets 84–107. Bytes 432–727 of each record are zero.

Swatches interpret bits 15–11, 10–6, 5–1 and bit 0 as RGBA5551 solely
as a visualization hypothesis. Swatches show RGB opaquely; their tooltip
reports hypothetical alpha. Neither color format nor field roles are
confirmed. No associations were added.

Reproduce the source-bound analysis:

```powershell
& $pesPython pes6_profiles.py --out research/profiles_6670.json
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence test_profiles
```

The generated JSON includes the compressed entry hash and both part hashes.
Validation: 19 tests passed, including real source counts and offsets,
metadata frequency totals, malformed structures and color conversion bounds.
HTTP smoke checks passed for `/`, `/profiles`, `/profiles/data` and `/research`
with 7759 catalogued textures. Node syntax checks passed for the gallery
and inspector scripts. Visual browser behavior has not been checked.

## 2026-11-24 — Global palette comparison

`pes6_palette_probe.py` compares the 21 words per subrecord in 6670 with
the union of RGB values in all 820 candidate WE00 palettes. It validates
each WE00 header and length, reads directly from `cv.img`, and records
AFS offsets, sizes and SHA-256 hashes of all 410 compressed source entries
and 820 unpacked parts in `research/palette_comparison.json`.

The comparison quantizes palette RGB by truncating channels to 5/6 bits.
It tests RGBA5551, RGB565 and ARGB1555 with both native big-endian words
and byte-swapped words. Alpha is ignored. Unused palette entries are
included: this is palette membership, not similarity of rendered textures.

Observed in the current sources:

- 17220 word occurrences, 436 unique words; every occurrence has bit 0 set.
- Native RGBA5551: 340/436 distinct RGB signatures occur in the palette union.
- Byte-swapped RGBA5551: 160/419 occur. Signature counts can decrease when
  the hypothesized alpha bit is discarded.
- Native RGB565: 202/436; native ARGB1555: 214/430.
- The palette union occupies 12177/32768 possible RGB555 colors (37.16%).
  This coverage is descriptive; it is not a significance test or probability
  that the interpretation is correct.

These observations support further investigation of RGBA5551, but do not
confirm the game's interpretation. No record-to-kit or team-to-kit
associations are emitted, and no resource replacements are performed.

The inspector at `/profiles` offers a comparison table, fetched from
`/profiles/palettes`. Results are calculated from the current source, not
served from a stale report. The UI rejects a profile-source hash mismatch.

Reproduce:

```powershell
& $pesPython pes6_palette_probe.py --out research/palette_comparison.json
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence test_profiles test_palette_probe
```

Validation: 23 tests passed, including real binary sources, malformed WE00
headers/lengths, known color channels and empty comparison inputs. HTTP checks
passed for the inspector, profile data and comparison data; source hashes
agreed across responses. Node syntax checks passed for both Studio scripts.
The new comparison panel has not been checked visually in a browser.

## 2026-11-24 — XEX executable investigation

`pes6_xex_probe.py` reconstructs this title's basic-compressed XEX2 image
in memory. It supports normal AES-CBC encryption or no encryption, checks
block bounds/alignment and PE32 PowerPCBE headers, and scans only sections
marked executable. It never writes an executable image or changes the source.
The research-only dependency `cryptography` is required for encrypted XEX.

Format references (consulted 2026-11-24):

- https://github.com/xenia-project/xenia/blob/master/src/xenia/cpu/xex_module.cc
- https://github.com/xenia-project/xenia/blob/master/src/xenia/kernel/util/xex2_info.h

The loader uses a continuous CBC chain for stored block data, inserts the
declared zero spans between blocks and zero-fills the remaining allocation.
The normal retail loader constant is public in Xenia. No session key is
recorded. Only this basic-compression profile is supported; LZX, devkit and
patch images are not supported by this probe.

Confirmed source identity and structure:

- `default.xex` SHA-256:
  `b76db0fc2f86794f4e99bb4d93dd8148d31a00b518cb1e5c822ef0bc75ac1087`.
- Reconstructed allocation: 18612224 bytes; base `0x82000000`;
  entry point `0x826d2238`. Reconstructed image SHA-256:
  `30fff01e5f225260538b4c67442cfc4103d235c7e35f04a1ac4046b76b748cae`.
- Image offsets are RVAs. Original PE raw-file offsets differ and must not
  be used as memory offsets. Some non-executable section declarations
  (notably `.reloc`) extend beyond this allocation; their actual covered
  bytes are explicitly reported. Executable sections must be fully in bounds.

Instruction-shaped candidates retained in `research/xex_immediates.json`:

| Address | Bytes | Narrow decode | Observation |
| --- | --- | --- | --- |
| `0x8217841c` | `2b0a00bd` | cmpli, immediate 189 | Near multiply below |
| `0x82178424` | `2b0a00cc` | cmpli, immediate 204 | Near multiply below |
| `0x82178430` | `1d4a02d8` | mulli r10,r10,728 | Matches observed candidate record stride |
| `0x82178458` | `1d6b02d8` | mulli r11,r11,728 | Second nearby multiplication |
| `0x8217b588` | `2b0b1a0c` | cmpli, immediate 6668 | Candidate database-ID comparison |
| `0x8217b5b8` | `2b0b1a0e` | cmpli, immediate 6670 | Candidate database-ID comparison |
| `0x822fa198` | `3bab1668` | addi r29,r11,5736 | Base-constant candidate; input semantics unknown |

The coincidence of 728 and 189–204 is a useful lead, not a proven
record-to-team mapping. The third 5736 occurrence at `0x827d984c` follows
an address-high load and is consistent with an address displacement;
literal matches must not all be treated as AFS IDs.

The probe only decodes selected D-form immediate instructions. It does
not establish reachability, function boundaries, runtime values, calling
conventions or the provenance of pointers. Full disassembly/dataflow and
runtime validation remain outstanding. No team or kit associations were added.

Studio `/profiles` now offers the executable candidate table through
`/profiles/executable`, calculated from the current XEX source. This analysis
does not participate in editing or patch generation.

Reproduce:

```powershell
& $pesPython pes6_xex_probe.py --out research
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence test_profiles test_palette_probe test_xex_probe
```

Validation: 26 tests passed, including the real encrypted XEX, synthetic
PE/XEX images and malformed/truncated blocks and headers. Both Studio
scripts passed Node syntax checks. HTTP checks passed for the inspector and
the executable-data endpoint; the endpoint source hash matched `default.xex`.
No visual UI or runtime Xbox/Xenia validation was performed. The source hash
remained unchanged. A full disassembler dependency was unavailable over the
network; the retained decoder and all conclusions stay limited to the
explicit instruction forms described above.

## 2026-11-24 — Cross-platform patch research and delivery priorities

See `research/pes6_web_research.md` for primary-source URLs, observations,
access limitations and a patch delivery plan. The companion
`research/web_research_manifest.json` binds the research to local source
hashes; no external patch binary was downloaded or validated.

The local XEX execution-info optional header `0x40006` identifies Media ID
`617138EB` at its first BE32 word and Title ID `4B4E07DA` at offset +12.
These match the edition named by the NOBK project's documentation. Matching
identifiers do not establish whether its changes can run on the console.

Reproduce the local ID check:

```powershell
@'
from pathlib import Path
from pes6_xex_probe import u32
d = Path('default.xex').read_bytes()
headers = dict((u32(d,24+8*i),u32(d,28+8*i)) for i in range(u32(d,20)))
o = headers[0x40006]
print('Media ID: %08X; Title ID: %08X' % (u32(d,o),u32(d,o+12)))
'@ | & $pesPython -
```

Prioritize one visually verified club package (crest/name/kits), then
competition identities, then a single custom scoreboard. Automatic
scoreboard selection by competition remains a separate unproven console
feature. PC/PSP resource IDs, layouts and Kitserver DLLs must not be imported
as if they were Xbox 360 associations. No associations were added by this
research, and no original game files were changed.

## 2026-11-24 — Chelsea 2006/07 crest pilot

User selected Chelsea in the original 2006/07 season. A first, isolated
crest test is now built; this is not yet a complete licensed club package.

### Executable name/graphic table

Starting from the `London FC` ASCII string at image offset `0x0ac2c4`,
the image contains a BE32 pointer to that string at `0x0d55890`. The same
position in successive 24-byte records holds bounded full-name pointers;
+4 holds a short-name pointer. Walking valid paired pointers in both
directions yields the observed span `[0x0d55218, 0x0d56628)`, 214 records.
This span includes national teams, clubs and special/pseudo teams, not
214 ordinary clubs. This discovery did not derive graphic IDs from rosters.

For the exact original XEX hash, London FC's record at virtual address
`0x82d55890` stores `LDN` via the +4 pointer and BE16 values 62 at +10/+12.
Visual controls against original decoded crest artwork:

| Stored name | +10 | +12 | Crest artwork |
| --- | --- | --- | --- |
| Arsenal | 57 | 57 | Arsenal |
| Manchester United | 67 | 67 | Manchester United |
| R. Madrid | 146 | 146 | Real Madrid |
| London FC | 62 | 62 | Fictional shield, target of Chelsea correction |

Both reference fields agree throughout the observed table. Their separate
roles have not been differentiated; runtime access is still untraced.
`pes6_club_identity.py` rejects any XEX hash except the validated original.
It exports names and reference observations to `research/club_identity.json`.
No uniform IDs are inferred or saved.

### Source and output evidence

`cv.img` is exactly 624951296 bytes. SHA-256:
`c3c3f2aa3bd1623b650c9f356b9da85b9878feec0aceb89ab250a9abb5eb24dc`.
It matches `cv.img` at ISO offset 2387961856, partition base 265879552.
See `research/chelsea_2006_07/base_verification.json`.

- Entry 2710: offset 235087872, size 682640; nested part 62 is a
  compressed indexed8 WE00 crest, 128x128.
- Entry 2711: offset 235771904, size 390508; nested part 62 is a
  compressed indexed8 WE00 crest, 64x64.

Artwork was obtained externally from the Premier League badge CDN:
https://resources.premierleague.com/premierleague/badges/t8.png
Its SHA-256 is
`e677ef6cd08f37e2bfe80d53f18d5c348f0970b0dc09ea43ea99e672bc3592ad`.
The original download, resized PNGs and encoded previews are retained.
There are no generated uniform artworks or duplicate replacements.

`pes6_chelsea_crest_patch.py` verifies part boundaries, formats, dimensions
and byte equality of all unselected parts before making a new IMG. It
uses the existing fixed-size encoder and verified copier. Output IMG hash:
`1375558fd52798c05fbfe31e2e6435d96a1bd740d22258fca469531ba2a20967`.

An independent test ISO was built at
`research/chelsea_2006_07/iso_test/PES6_MOD.iso` using `pes6_iso.build`.
The existing builder compares the entire output with the original plus
the expected entry replacements. Original source files were preserved.
Names, XEX, uniforms, competitions and scoreboards were not changed.

### Reproduce

```powershell
& $pesPython pes6_club_identity.py
& $pesPython pes6_chelsea_crest_patch.py --prepare
& $pesPython pes6_chelsea_crest_patch.py --output research/chelsea_2006_07/cv_reproduced.img
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence test_profiles test_palette_probe test_xex_probe test_club_identity
```

To reproduce a test ISO into a new output directory:

```python
from pathlib import Path
from pes6_iso import build
edits = {}
for entry, size in ((2710, 128), (2711, 64)):
    original = Path(f'cv_we00_texturas/{entry}_part062_unpacked.png').read_bytes()
    replacement = Path(f'research/chelsea_2006_07/chelsea_crest_{size}.png').read_bytes()
    edits[entry] = {(f'{entry}_part062_unpacked',): (original, replacement)}
build(Path('../Pro Evolution Soccer 2006 [PAL].iso'),
      Path('research/chelsea_2006_07/iso_reproduced'), {'cv.img': edits}, 'iso')
```

### Verification and limits

29 tests passed, including the real team table, malformed string/table
bounds and independent verification of selected/unselected crest parts.
Node syntax checks and HTTP checks passed for the Studio gallery, club
page, table data and original/modified crest previews. Studio now includes
a Chelsea 2006/07 page via `/clubs`; source observations do not auto-populate
team-to-kit mappings. Browser rendering was not checked.

Automated visual access to Xenia was unavailable: both the bundled desktop
runtime and the unified desktop runtime failed before selecting an app.
No game was launched, no runtime validation is claimed, and the user must
observe the test ISO to confirm the London FC crest in selection, formation
and match. See `research/chelsea_2006_07/TESTE.md`.

### Subsequent user confirmation — 2026-11-24

The user reported: “Sim, o escudo do chelsea foi atualizado de forma PERFEITA!”
This confirms the Chelsea crest replacement in the supplied test, as a user
observation rather than an agent-controlled runtime trace. The evidence is
stored in `research/chelsea_2006_07/runtime_confirmation.json`, bound to the
original XEX/CV hashes and modified CV hash. No separate per-screen results,
kit links, executable name changes, or individual roles of fields +10/+12
are claimed. The Studio club status now reflects this scoped confirmation.

## 2026-11-25 — Self-service club editor, names and project integration

Studio v0.12 exposes a reusable `/clubs` editor instead of a Chelsea-only
research page. `PES6Studio.cmd` launches it using the installed Python and
the original ISO; `PES6STUDIO_LEIA-ME.md` documents the UI workflow.

### Crest editing

`pes6_club_editor.ClubEditor` resolves the two crest resources from each
observed executable record's explicit +10/+12 fields and the loaded WE00
catalog. It refuses missing or ambiguous resources, reports shared
references (not identical pixels), and distinguishes the user-confirmed
Chelsea crest from static references for other records.

`POST /clubs/stage` prepares both sizes, preflights compressed AFS entry
capacity with all pending changes in those entries, and commits only if
both conversions succeed. Failure leaves the previous edits intact.
`POST /clubs/undo` removes only the selected crest pair. The editor uses
the same texture edits, project save/load and ISO/IMG builder as the gallery.
Converted previews are supplied by `/edited`; no originals are overwritten.

The HTTP integration test in `research/studio_workflow_test/result.json`
prepared a single PNG, restored and reloaded the two resolutions, and
generated an IMG identical to the user-confirmed crest pilot. Folder
opening accepts only output directories generated by that server session.

### Club names and abbreviations

`pes6_name_editor.NameEditor` edits only the original UTF-8 string buffers
referenced by the validated 24-byte table. Full name and abbreviation have
separate capacities equal to their original encoded byte lengths. No
allocation, table pointer, code, section size or neighboring string is
changed. Empty/control-character strings, oversized replacements, unknown
source hashes and changes to buffers shared by multiple table fields are
rejected. This is intentionally a fixed-capacity editor; arbitrary longer
names are not supported yet.

For London FC (record 69): full name pointer `0x820ac2c4` (9 bytes plus NUL),
short name pointer `0x820ac2c0` (3 bytes plus NUL). `Chelsea` and `CHE` fit.
Shorter strings are NUL-padded within the original buffers. No graphic ID
or uniform association is changed by name editing.

`POST /clubs/name` prepares name/abbreviation together; `/clubs/nameUndo`
restores their original values. Project schema 1 remains readable: new
optional fields `club_names` and `name_source_sha256` preserve edits and
bind them to the validated executable. Loading validates names before
replacing either the texture or name edit state. Old projects without
name fields remain supported.

### Executable output

The source's basic-compression blocks are reconstructed in memory, only
the selected buffers are changed, and the stored block data is re-encrypted
using continuous AES-CBC. Omitted zero spans and allocation padding must
remain unchanged. The result is reconstructed again and compared exactly
to the intended image. Source and output lengths match; no executable
image is patched in place.

The original XEX header, including signature/digest fields, is preserved.
The executable is **not re-signed**. Binary reconstruction verification
does not establish cryptographic validity or console compatibility.
On-screen name behavior in Xenia and physical console operation have not
been confirmed. The UI and user guide state that runtime testing is required.

`pes6_iso.build` accepts a source-hash-checked `default.xex` replacement in
addition to texture edits. It supports names-only and mixed name/crest
projects. ISO output injects the same-length executable into a new ISO;
extracted output includes `default.xex` alongside any modified IMG files.
`club_names.json` in the output folder records before/after names, source
and modified executable hashes and the unverified runtime/signature status.

### Checks

40 tests passed, including real encrypted XEX no-op repacking, exact
decoded-image change boundaries, malformed names, overflow rejection,
unstored-region rejection, project compatibility, atomic crest updates
and source-guarded executable-only output. Node syntax checks passed for
the club editor and gallery scripts. The UI has not been visually inspected.

Reproduce the automated suite:

```powershell
& $pesPython -m unittest test_binary test_duplicates test_resource_map test_we00 test_evidence test_profiles test_palette_probe test_xex_probe test_club_identity test_club_editor test_name_editor
```

The additional HTTP integration run is retained in
`research/studio_name_workflow_test/result.json`. It exercised name-only
and mixed projects, save/restore/load, invalid-name rejection and both
extracted executable and ISO generation. The modified executable hash was
`7624f0f9a7b53576d01dfcafc74ad7d7177deeacda9df31fea1c2d0a32463153`.
Reading the generated ISO recovered that exact executable and the same
crest IMG hash as the user-confirmed pilot. These are binary checks,
not a claim that changed names were observed on screen.

## 2026-11-25 — League labels, competition artwork and source versioning

Studio v0.13 adds `/leagues`, with 19 source text labels and a visual picker
for 27 competition artwork resources from CV entry 2700. Selection of
artwork is manual and saved in the project; it is not a game relink or a
presumed correspondence between a text ID, image index and runtime competition.
Some labels (including German League and generic leagues) may be unused or
unavailable in menus. Their presence does not add playable competitions.

### Identified text structure

Source language IMG SHA-256 is the existing `KNOWN` PAL hash:
`be36cdd9a864cfaaeddc67ff170d867556db9fe84200b95b6d84f24471bfbcc1`.
The clean local file is `rv_e_limpo.img`; the differently hashed `rv_e.img`
and `rv_e_original.img` are not used as league text sources.

The English league-label block is byte-identical in entry 242 part 20 and
entry 254 part 0. The table has 140 records, an eight-byte header and 12-byte
records encoded as BE16 ID, BE16 auxiliary field, BE16 byte length including
NUL, BE16 Unicode character count, BE32 offset relative to the part. The
parser verifies bounds, terminators, UTF-8 counts, duplicate IDs and overlaps.
For example, source English text IDs 105–110 are England League, Ligue 1,
German League, Serie A, Eredivisie and Liga Española. These are **text IDs**,
not proven runtime competition IDs.

The enclosing parts container has a trailing table of 16-byte part names.
Its third directory word is a pointer into that footer, not a value that
may be copied unchanged if data moves. In entry 242 the footer begins at
105904 and contains 41 names; in entry 254 it begins at 30152 and contains
eight names. Footer strings include `weStrDataLCX1C`. The rebuilder verifies
this layout, preserves other parts and footer strings, and updates part
offsets, lengths and footer pointers after repacking changed labels.

### Controlled AFS growth

The original compressed entries have little spare compression capacity.
A fixed-compressed-size rewrite rejected even a reasonable label change.
League entries therefore use `EntryReplacement(..., allow_growth=True)`:
the AFS writer binds the original entry hash, checks non-overlap, limits
growth to the existing gap before the next nonempty entry and verifies
every newly consumed padding byte is zero. It updates the entry size in
the AFS index without moving any other entry or changing the IMG/ISO size.
All existing texture replacements retain their fixed-size behavior.

Names are limited to 64 UTF-8 bytes by the editor and checked against actual
archive capacity before staging. Both English label blocks are updated.
Other languages, achievement descriptions and unrelated label occurrences
are not replaced indiscriminately. No executable change is needed for these
league labels.

### Project and evidence

Optional schema-1 fields `league_names`, `league_logo_links` and
`league_source_sha256` preserve league edits alongside club names and
textures. Load validates all components before replacing active edit state.
`league_changes.json` in exported output records edited labels and manual
artwork selections. Runtime confirmation of league edits remains pending.
Source-bound research is in `research/league_identification.json` and the
local diagnostic artwork contact sheet `research/league_2700_contact.png`.
The completed HTTP test exported the real IMG files, recovered both edited
labels from both rebuilt tables, verified relocated footer pointers and
checked every unselected language AFS entry byte-for-byte against the source.
The artwork used in that test was diagnostic, not a distributed visual patch.

45 tests passed with local data. A source-only copy also passed its suite
(38 discovered tests, 16 skipped), without distributing game data. League
UI JavaScript passed Node syntax checking. The actual editor HTTP workflow
is recorded in `research/studio_league_workflow/result.json` when available.

### Git repository

Remote: https://github.com/evandrodsm17/pes6studio360

`.gitignore` is source-only: game binaries, ISO/IMG/XEX, generated art,
patches, personal projects, caches, emulators and generated research are
excluded. Tests requiring those files skip when they are absent. Dependency
versions in `requirements.txt` match the locally tested environment.

This managed environment denied writes to the root `.git/config`. Active
local Git metadata is therefore isolated in `research/versioning/git_metadata`
and accessed through `GitStudio.cmd`; a normal clone uses ordinary Git.
No global safe-directory exception or TLS-verification bypass is installed.
A local ignored CA bundle contains the existing trusted certificate roots
for transport verification. Only source and documentation are published.

## Scoreboard atlas editing (0.14)

The verified English archive contains the named parts below. These are
resource identities read from the part-name footer, not inferred from PC IDs.

| Archive | Entry | Part | Name | Dimensions |
| --- | ---: | ---: | --- | --- |
| rv_e | 249 | 0 | game2d_00 | 256 × 256 |
| rv_e | 249 | 1 | game2d_01 | 256 × 256 |
| rv_e | 249 | 2 | game2d_number | 256 × 128 |
| rv_e | 249 | 3 | replay | 256 × 128 |
| rv_e | 253 | 0 | game2d_number | 256 × 128 |

The two number parts are byte-identical and edited together. Parts 4 and 5
of entry 249 contain controller and other HUD artwork and are preserved.
The original atlas for game2d_00 visibly includes clock glyphs, stoppage-time
labels, radar and strategy elements; it is not solely a scoreboard backdrop.

`pes6_scoreboards.py` reads the original verified archive selected by the
league editor. It does not use possibly modified extracted images. Strict
PNG dimensions are required. Encoding preserves the WE00 header and fixed
uncompressed part length. Recompression changes WESYS length fields and
uses the existing checked AFS allocation policy. Part directories, offsets,
other parts and named footers remain byte-identical after decompression.
Staging checks archive capacity before accepting an edit. Optional schema-1
`scoreboard_textures` stores source-hash-bound encoded parts. All project
components are validated before replacing active edits. Export reports
`automatic_selection: false` and `runtime_verified: false` explicitly.

The real HTTP workflow combined HUD/numbers and a league-name change,
saved/restored/reloaded the project and exported a rebuilt `rv_e.img`.
Only entries 242, 249, 253 and 254 changed, every entry offset remained
unchanged, and the two number copies remained identical. The test uses
diagnostic pixels, not a designed or runtime-validated scoreboard.
Local report: `research/scoreboards/workflow.json`. Suite: 48 tests passed.

### Automatic competition selection: investigation, not implementation

Named layout parts in original `cv.img` entry 2703 are `scoretime` (part 0),
`game2d` (part 1), and `replay` (part 2). They are binary layouts rather than
WE00 images and are not modified by this editor.

In the reconstructed PAL executable, big-endian PPC `lis`/`addi` pairs
construct the following string addresses. Offsets are mapped-image RVAs;
runtime addresses are RVA + 0x82000000. The narrow scan does not establish
function boundaries, control flow, a loading hook or competition selection.

| String RVA | String | lis RVA | addi RVA |
| --- | --- | --- | --- |
| 0x000c8384 | game2d_number | 0x00465b84 | 0x00465b8c |
| 0x000c8384 | game2d_number | 0x004682bc | 0x004682c0 |
| 0x000c83f8 | scoretime | 0x00468088 | 0x0046808c |
| 0x000c83f8 | scoretime | 0x0046829c | 0x004682a0 |
| 0x000c8404 | game2d | 0x00468428 | 0x0046842c |
| 0x000c8410 | replay | 0x0046847c | 0x00468480 |
| 0x000c8410 | replay | 0x00472b1c | 0x00472b24 |

Source XEX SHA-256:
`b76db0fc2f86794f4e99bb4d93dd8148d31a00b518cb1e5c822ef0bc75ac1087`.
Local raw evidence: `research/scoreboards/named_parts.json` and `xrefs.json`.

Primary PC reference: [Pato_Lucas18's Scoreboard Server documentation](https://foro.pesretro.net/thread-12937-post-489077.html).
It describes a Kitserver DLL that selects folders through a competition map
and replaces resources at runtime. Its x86 hooks, memory addresses and IDs
cannot be assumed to apply to the Xbox 360 PPC executable. League text IDs
105–110 are not established as runtime competition IDs.

To implement an actual selector, trace the layout/resource loading calls,
identify the live match competition state with contrasting exhibition,
league and cup sessions, then establish resource selection/injection and
lifetime behavior. Only after those bindings are confirmed should the
Studio expose competition mappings. No placeholder mapping is exported as
if the original game could consume it. Automatic selection and layout
editing remain unimplemented; no claim of runtime success is made.

### Additional HUD loading observations (0.15)

`pes6_scoreboard_probe.py` reproduces a source-bound instruction check:
`li r3,2706` at RVA 0x468114 and `li r3,2703` at RVA 0x468184 precede
relative `bl` calls at 0x468118 and 0x46818c to 0x827292e0. The second
sequence contains one intervening `stw`, verified byte-for-byte. This is
a candidate resource-loading path because CV entry 2703 contains named HUD
layouts. It does not establish the callee's full ABI or execution in a match.
Local evidence: `research/scoreboards/loader_calls.json`.

Analysis through REA could not supply PowerPC decompilation in this Windows
environment: the XEX reconstructed PE machine 0x01f2 was rejected, and an
explicit diagnostic ELF wrapper of the code window was recognized as PPC
but had no configured/supported deep-analysis provider. The wrapper is an
analyst-generated container, not a game artifact or executable modification.
The narrow Python instruction check does not depend on that wrapper.
Competition-state identification, a selector hook and runtime validation
remain outstanding. No speculative executable patch is generated.

## Players and registrations (0.15)

The editor accepts only original CV SHA-256
`c3c3f2aa3bd1623b650c9f356b9da85b9878feec0aceb89ab250a9abb5eb24dc`.

| CV entry | Player records | Squad records | Part 0 | Part 1 | Part 2 |
| --- | ---: | ---: | --- | --- | --- |
| 6667 | 4415 | 188 | 152 bytes/player | 32 BE16 IDs/squad | 32 byte numbers/squad |
| 6668 | 4210 | 189 | 152 bytes/player | 32 BE16 IDs/squad | 32 byte numbers/squad |

Player record bytes 0–45 store the UTF-8 display name, bytes 46–61 the
shirt name, both zero-terminated. All bytes from 62 onward remain untouched.
Record zero is reserved by the editor. Empty registrations preserve source
IDs 0 or 65535; new empty registrations use 65535 and number 255. Number
editing accepts 0–99 or the original undefined value 255. Duplicate player
IDs within a squad are rejected; inscriptions across squads are permitted.
No team ownership is inferred from a single registration.

The two databases differ in roster contents, record counts and player IDs.
They are independently selectable and independently serialized. For example,
the same Chelsea squad slot 69 uses different IDs for Cech, Essien and
Drogba. The later Spanish club alignment also differs between databases.
Names from the executable table appear only as references in the 6668
selector and must be checked against membership. No labels are guessed for
6667; no team-to-kit mapping is derived from these squad indexes.

Transfers prepare the source and destination together, preserve other
registrations, and reject full destinations. All staging preflights checked
AFS capacity before replacing active state. Repacking changes only selected
name buffers, registration IDs and number bytes, plus compression metadata
and checked AFS size fields. Parts 0/1/2 retain their lengths; part 3 and
all other data are preserved. Formation data and player attribute bitfields
are not edited. Runtime interpretation and any option-file precedence still
need validation; aliases in entry 6666 are not rewritten speculatively.

Optional schema-1 `player_database` contains the CV source hash, player
changes keyed by database and ID, and complete changed squad arrays keyed
by database and slot. It is validated before any project state is replaced.
Output `player_changes.json` records exactly those changes and explicitly
marks runtime validation pending. Both CV databases can be exported together
with league names and scoreboard textures. The real HTTP workflow saves,
restores, reloads and exports those combined changes; its local report is
`research/player_editor/workflow.json`.

## Isolated database identification (0.16)

`PlayerEditor.probe()` source-checks the original Lampard name and Chelsea
slot membership in both databases, then returns independent entry replacements
for record 144 with `Lampard DB6667` / `Lampard DB6668` and matching shirt
markers. It passes explicit temporary player edits and an empty squad map
to the builder, so active player, squad and all other project edits are
neither included nor modified. `/players/probe` exports to a fresh directory,
records `database_test.json`, and supports the normal IMG/ISO output modes.
No automatic runtime conclusion is recorded from creating the test.

The HTTP verification staged another name first, exported the probe, checked
that pending state remained identical, recovered both distinct markers from
the generated CV, and compared every AFS entry. Only 6667/6668 changed; offsets
and unrelated entries were preserved. Evidence is local at
`research/player_editor/probe_workflow.json`. The eight player/probe tests
passed, including the pending-project isolation test and real-source checks.

### Packed HUD tokens

Additional source-bound sequences in `pes6_scoreboard_probe.py` construct
`0x020000f9` in r3, whose low 16 bits are 249, matching the identified English
HUD atlas entry. At RVA 0x467cc0 the instruction order is `lis r3,0x200`,
`li r4,1`, `ori r3,r3,0xf9`, then a relative call at 0x467ccc to 0x82729548.
At 0x468190 `lis`/`ori` are adjacent, followed by a call at 0x468198 to
0x82729598. The exact words are checked before reporting the observations.
These are candidate resource tokens, not proven archive identifiers or
competition IDs. The two callees' load/unload roles have not been traced.
No competition-dependent routing or executable modification is implemented.

## Ability value editing (0.17)

The 152-byte player records contain a consecutive 26-byte region at offsets
70–95. All 4415 records in CV 6667 and 4210 records in CV 6668 have values
in 0–99 when extracting each byte's high seven bits. This includes reserved
and unnamed records; the editor still forbids record zero. Each setter
changes only mask 0xfe and preserves bit zero. No flag interpretation is
assumed for that neighboring bit.

At mapped PAL XEX RVA 0x681a28, word 0x894a0051 is `lbz r10,81(r10)`.
At 0x681a30, word 0x554af87e is `rlwinm r10,r10,31,1,31` (right shift by
one). The intervening 0x7d08f82e loads another register and does not overwrite
r10. This supports that extraction for byte 81 in a native code path; it
does not independently prove every label or execute the path in a match.
The bounded source scan is recorded locally in
`research/player_editor/ability_getter_hits.json`.

The provisional labels follow the ordered 26 basic abilities in the primary
PC editor reference [PeterC10/PESEditor Stats.java](https://github.com/PeterC10/PESEditor/blob/11f78f21687771d4dcb733454b7cce4821f5c70a/src/editor/Stats.java).
The PC option-file layout is not imported as the console layout: it uses
124-byte records and different bit positions. Only the field-order reference
is compared; encoding is implemented from the observed console bytes. No
third-party source code is copied into the Studio. The reference checkout
is ignored under research and is not published with this repository.

Static controls in CV 6668 include Lampard: byte 70 -> 84, byte 73 -> 97,
byte 95 -> 50; Cech and Casillas have byte 95 -> 95 and 90. These are sanity
checks, not runtime confirmation of attack, stamina or goalkeeper semantics.
The UI explicitly presents the labels as provisional and requires loading
values before editing. Physical fields, positions, appearance and special
abilities remain untouched. No source player's attributes are mass-updated
or converted between databases.

Ability edits are an optional `abilities` list inside schema-1
`player_database`, keyed by database and player ID. Legacy projects load
with an empty ability map. Load validates abilities with all other project
components before committing state. The isolated database probe explicitly
passes an empty ability map, so it still excludes every pending user edit.

57 tests passed. Tests cover mask preservation, exact byte scope, invalid
values, project roundtrip, restoration and probe isolation with pending
ability edits. The HTTP workflow stages abilities and a player name,
saves/restores/reloads, then exports a real CV. Only entry 6668 changed;
all other entries, offsets and neighboring flag bits were preserved.
Local report: `research/player_editor/abilities_workflow.json`. Runtime
attribute validation and automatic scoreboard selection remain outstanding.
