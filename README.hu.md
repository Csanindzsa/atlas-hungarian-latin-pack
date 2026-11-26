# Human Anatomy Atlas 7.4.01 — magyar–latin nyelvi csomag (v1.0)

Nem hivatalos, közösségi fordítás tanuláshoz. **Nem orvosilag lektorált tananyag.** A vizsgán mindig a saját tankönyved és jegyzeted a mérvadó.

## Mit tartalmaz?
- Magyar kezelőfelület (241 sor) és 4 643 anatómiai név; az eredeti **latin nevek és a latin nézet változatlanok**.
- Magyar definíciók, betegségleírások, kvízkérdések és feliratok (11 385 szövegmező).
- Magyar keresés, ékezettel és ékezet nélkül is (pl. „gégefedő” és „gegefedo”).
- **Két névstílus**, telepítéskor választhatsz (mindkettőt elfogadják az egyetemen):
  - **1 = magyaros:** oldalsó / belső (pl. „Oldalsó combcsont körüli ér”).
  - **2 = latinos:** laterális / mediális (pl. „Laterális combcsont körüli ér”). Csak ott változik, ahol a latin név is lateralis/medialis; a belső = internus (pl. „Belső csípőér”) mindkét stílusban marad.
- A program az angol nyelvi helyet használja: a programban az **English** nyelvet válaszd, ennek helyén jelenik meg a magyar.

## Telepítés (Windows)
1. Saját, működő **Atlas 7.4.01** telepítés szükséges. A csomag nem tartalmazza a programot. Más verzión nem működik, és nem is módosít semmit.
2. Csomagold ki a ZIP teljes tartalmát egy mappába.
3. Zárd be az Atlast.
4. Jobb gomb az `Install.cmd` fájlon, majd **Futtatás rendszergazdaként**. A Windows engedélykérését neked kell jóváhagynod.
5. Írd be: `1` (magyaros) vagy `2` (latinos), majd Enter.
6. Indítsd el az Atlast, és válaszd az **English** nyelvet.

A telepítő magától megkeresi az Atlas 7.4.01 mappáját (Program Files és a Windows telepített programjainak listája alapján), és csak akkor használja, ha a fájljai pontosan egyeznek a 7.4.01-es verzióval. Ha nem találja, vagy több telepítés is van, rendszergazdai PowerShellben add meg a mappát:

```powershell
& .\Install-Pack.ps1 -PackDirectory $PWD.Path -AtlasDirectory 'D:\SajatAtlasMappa' -Variant magyar   # vagy latinos
```

**Stílusváltás:** futtasd újra az `Install.cmd` fájlt, és válaszd a másik számot. Nem kell előbb visszaállítani.

## Visszaállítás az eredeti angolra
Zárd be az Atlast, majd futtasd rendszergazdaként a `Restore.cmd` fájlt. A telepítő a két érintett eredeti fájlról ellenőrzött másolatot tesz a `HungarianLatinPack-backup-7.4.01` mappába; ezt ne töröld.

A csomag nem módosítja a joystick- és egyéb beállításokat, a kedvenceket, az aktiválást vagy a védelmi beállításokat. Minden fájlt ellenőrzőösszeggel vizsgál: sérült csomag vagy ismeretlen fájl esetén leáll, és nem ír semmit.

## Mi maradt angolul?
- A betöltő- és Névjegy-képernyő képeibe égetett feliratok (márkanév, áruházi gombok).
- A kiejtési hangfájlok és a videók.
- Néhány belső, normál használatkor nem látható fejlesztői szöveg.

## Pontosság
- Minden név és szöveg gépi ellenőrzésen ment át (irány: felső/alsó, elülső/hátsó, medialis/lateralis, bal/jobb; képlettípus: artéria/véna/ideg/izom; mozgások, számok, tagadások, a latin név egyezése, magyar nyelvhelyesség), a gyanús helyeket kézzel néztük át; a neveket ezen felül egyenként is átnéztük.
- Az eredeti angol szövegben talált néhány szakmai hibát a fordításban javítottuk (pl. a nervus obturatorius a comb közelítőizmait látja el, nem a távolítókat).
- Kb. 280 név esetében a pontos képlet vagy a legjobb magyar alak nem dönthető el biztosan (pl. ha az angol és a latin név ellentmond egymásnak). Ezek a `translations/NYITOTT-KERDESEK.csv` fájlban vannak. Ha hibát találsz, jelezd a csomag készítőjének.
- Ez nem orvosi szaklektorálás. Szakmai lektor nem ellenőrizte; a készítő ennek tudatában adja ki tanulási segédletként.

## Továbbadás
Csak ezt a nyelvi csomagot add tovább, az Atlas programot ne. Mindenkinek saját, jogszerű Atlas 7.4.01 példány kell hozzá.
