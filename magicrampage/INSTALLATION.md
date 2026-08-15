# Magic Rampage — Installation / Instalação

## English

1. Install the release ZIP through PortMaster, or extract it at the ROM root so that
   `Magic Rampage.sh` is in `ports/` and this directory is `ports/magicrampage/`.
2. Create `ports/magicrampage/gamedata/`.
3. Copy your legally obtained Android APK into `gamedata/`; the filename is irrelevant.
4. Start **Magic Rampage** from the Ports menu. NXExtract validates and installs the
   owner data on first launch without deleting the APK. Its visible bilingual
   graphical extraction screen, with the approved SDL/framebuffer identity, is mandatory while installation is
   needed. After validation, the mandatory
   five-second bilingual **RETRO ELITE / NEXTOS** screen appears on every launch before
   the game, including launches where the data is already installed.

Tested reference owner data:

- Package ID: `com.asanteegames.magicrampage`
- ABI used by this port: `arm64-v8a` (AArch64 only)
- Game/build 1: Magic Rampage 7.8.2; APK size `162114946` bytes; APK
  SHA-256 `91adf146037def58867c23e705a26284d56adce7b56787b6e7eea417473021e6`.
- Game/build 2: Magic Rampage 7.8.7 (version code 1214); APKM size
  `170894843` bytes; APKM SHA-256
  `23f72590c725b2c4457136614e95f641be320b61e7f2db2453a934f77b905ae4`.
  Its selected base APK is `147950103` bytes, SHA-256
  `f2602fdda59f1326dc7d6045893373e14397fe80b5d3800892e7067b9c3cdaa9`.

Compatible 7.8.2 or 7.8.7 packaging variants may have a different container
name, size and whole-file SHA-256. They are accepted only when NXExtract proves
all of these:

- package ID `com.asanteegames.magicrampage`, ABI `arm64-v8a`, ZIP/APK magic and
  container size from `134217728` through `268435456` bytes;
- `libc++_shared.so`: `1253544` bytes, SHA-256
  `ad74bf43eb1fd576518168f664ad16a74e00eeda9595875c33dd87f6dd197869`;
- `libcrypto.so`: `5613536` bytes, SHA-256
  `97cad5581cdfe401251067ac41b507478ae434d7597fe8d08c78bc215a556587`;
- `libfmod.so`: `1472528` bytes, SHA-256
  `fbb2ee0f88bcbd79ad1449d74215f421efa2456b3397da49229986bcfc2f27ad`;
- `libmachine.so`: `4916048` bytes, SHA-256
  `a7d56f224bbc7277551a1e16b52b36383a780d356ad099f9197658509d17b4dc`.

An APK from another game version or with different critical native payload remains
rejected. This flexibility covers legitimate signing/repacking differences; it is not
an unrestricted APK bypass.

## Português

1. Instale o ZIP da release pelo PortMaster ou extraia-o na raiz das ROMs, deixando
   `Magic Rampage.sh` em `ports/` e esta pasta em `ports/magicrampage/`.
2. Crie `ports/magicrampage/gamedata/`.
3. Copie para `gamedata/` o APK Android obtido legalmente; o nome do arquivo não importa.
4. Abra **Magic Rampage** no menu Ports. O NXExtract valida e instala os dados do dono
   na primeira execução sem apagar o APK. A tela gráfica bilíngue de extração,
   com a identidade SDL/framebuffer aprovada, é obrigatória enquanto a instalação for necessária. Depois da
   validação, a tela bilíngue
   obrigatória **RETRO ELITE / NEXTOS** aparece por cinco segundos em toda abertura,
   inclusive quando os dados já estão instalados.

Dados de referência testados:

- Package ID: `com.asanteegames.magicrampage`
- ABI usada pelo port: `arm64-v8a` (somente AArch64)
- Jogo/build 1: Magic Rampage 7.8.2; APK com `162114946` bytes; SHA-256
  `91adf146037def58867c23e705a26284d56adce7b56787b6e7eea417473021e6`.
- Jogo/build 2: Magic Rampage 7.8.7 (version code 1214); APKM com
  `170894843` bytes; SHA-256
  `23f72590c725b2c4457136614e95f641be320b61e7f2db2453a934f77b905ae4`.
  O APK base selecionado tem `147950103` bytes, SHA-256
  `f2602fdda59f1326dc7d6045893373e14397fe80b5d3800892e7067b9c3cdaa9`.

Variantes de empacotamento compatíveis das versões 7.8.2 ou 7.8.7 podem ter
outro nome, tamanho e SHA-256 do container completo. Elas só são aceitas quando
o NXExtract comprova:

- package ID `com.asanteegames.magicrampage`, ABI `arm64-v8a`, magic ZIP/APK e
  tamanho do container entre `134217728` e `268435456` bytes;
- `libc++_shared.so`: `1253544` bytes, SHA-256
  `ad74bf43eb1fd576518168f664ad16a74e00eeda9595875c33dd87f6dd197869`;
- `libcrypto.so`: `5613536` bytes, SHA-256
  `97cad5581cdfe401251067ac41b507478ae434d7597fe8d08c78bc215a556587`;
- `libfmod.so`: `1472528` bytes, SHA-256
  `fbb2ee0f88bcbd79ad1449d74215f421efa2456b3397da49229986bcfc2f27ad`;
- `libmachine.so`: `4916048` bytes, SHA-256
  `a7d56f224bbc7277551a1e16b52b36383a780d356ad099f9197658509d17b4dc`.

APK de outra versão ou com payload nativo crítico diferente continua rejeitado. A
flexibilidade cobre diferenças legítimas de assinatura/empacotamento; não é uma
liberação irrestrita de APK.
