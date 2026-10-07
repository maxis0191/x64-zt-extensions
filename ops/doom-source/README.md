# Inspection Doom source, sans logiciel 3D

Ne pas committer les fichiers source ou les sorties. Les conserver dans
`runtime/doom-source-candidates`. Ce script n'extrait pas les archives sur disque,
ne charge pas Blender et n'évalue aucun code embarqué. Il lit le DAE borné,
les headers FBX/PNG et l'inventaire des blocs `.blend` avec son SDNA propre.
Les counts ne constituent ni un port de rig ni une preuve d'animation fonctionnelle.

Installation locale reproductible sous Python 3.12 Windows x64 :

```powershell
python -m pip install --no-deps --only-binary=:all: --require-hashes `
  --target runtime/doom-source-candidates/inspector-deps `
  -r ops/doom-source/requirements-win-cp312.txt
```

Inspection des deux téléchargements exacts :

```powershell
python ops/doom-source/inspect_sources.py `
  --slayer runtime/doom-source-candidates/doom-eternal-slayer-models-resource-326452.zip `
  --slayer-sha 15F0908392F3E9E0DAAF9C286FC3E884243A62BAB17BFFDAE62A6F6B654DC361 `
  --imp runtime/doom-source-candidates/doom-eternal-imp-ElVitt0ri0.blend `
  --imp-sha C94068D904C5495FEB1F29779EBA04A43F6BD5EFD0D29D16729564574C9A2FD3 `
  --dependency-dir runtime/doom-source-candidates/inspector-deps `
  --output runtime/doom-source-candidates/source-inspection.local.json
python ops/doom-source/test_inspect_sources.py
```

La sortie reste `ready=false`. Les fichiers réels ont été inspectés sans démarrer
d'outil 3D. Pour une future inspection/export Blender, obtenir une réservation
et utiliser `--factory-startup --disable-autoexec` avant de charger le fichier,
avec un inspecteur local contrôlé : l'Imp contient un datablock Text.

L'exporteur futur doit partir d'une pièce rigidifiée, puis prouver textures et
skinning avec les petits contrôles originaux décrits dans
`docs/DOOM-SOURCE-CANDIDATES.md`. Garder des assets isolés et des dépendances
minimales ; ne pas charger une zone entière pour obtenir une surface.

## Préparation du prop casque

Les commandes suivantes ont été exécutées sur les assets exacts le 2026-10-07,
sous admissions séparées extraction, writer et FF. Pour un nouveau run, attendre
le GO de coordination et la libération de la réservation.
L'export garde la géométrie bind source, sans évaluer le rig. Il refuse toute
sélection ambiguë, triangle dégénéré, winding contradictoire ou UV hors borne.

```powershell
python ops/doom-source/prepare_rigid_mesh.py `
  --archive runtime/doom-source-candidates/doom-eternal-slayer-models-resource-326452.zip `
  --sha256 15F0908392F3E9E0DAAF9C286FC3E884243A62BAB17BFFDAE62A6F6B654DC361 `
  --dae-member doomslayer_cine_3p/doomslayer_cine_3p_LOD0.dae `
  --material doomslayer_game_helmet `
  --output-root runtime/doom-source-candidates/helmet-rigid-a
python ops/doom-source/prepare_writer.py `
  --intermediate runtime/doom-source-candidates/helmet-rigid-a/rigid-source.json `
  --source tools/x64-zt-enemy `
  --output runtime/doom-source-candidates/helmet-rigid-a-writer `
  --name paris_doom_helmet_rigid_a --height-engine-units 16
```

`writer_rigid.cpp` est une adaptation indépendante du writer cube, compilée
avec MSVC `/W4 /WX` sans warnings. Son header généré fixe les counts, la bbox et le radius réels,
une racine, le LOD1M et l'échelle unités moteur/mètre. Le roundtrip réel a comparé
tous les 2852 vertices/4092 triangles et ces champs ; il ne prouve pas les pixels.
Le premier candidat garde le matériau retail mesuré pour isoler la géométrie.

Après préparation, `Build-Writer.ps1 -PreparedRoot <racine> -DryRun` vérifie le
pin et tous les hashes, recalcule le header et les metrics depuis l'intermédiaire,
et montre la commande MSVC single TU `/W4 /WX`. La même commande sans `-DryRun`
prend une réservation Build 2/3 GiB et écrit le roundtrip et les hashes des deux
assets. **Ne pas l'exécuter sans GO du parent.** Des warnings des headers upstream
peuvent encore refuser ce premier full TU ; garder le log, sans retirer `/WX`
silencieusement. La version cube existante n'est pas ce builder.

Tests sans assets ni moteur :

```powershell
python ops/doom-source/test_inspect_sources.py
python ops/doom-source/test_prepare_rigid_mesh.py
python ops/doom-source/test_prepare_writer.py
pwsh -NoProfile -File ops/doom-source/test_writer.ps1
python ops/doom-source/test_prepare_ff.py
python ops/doom-source/test_inspect_fbx.py
pwsh -NoProfile -File ops/doom-source/test_ff.ps1
pwsh -NoProfile -File ops/doom-source/test_runtime.ps1
```

Le packing UV half a un test C++ séparé `test_half_uv.cpp`. Compiler avec MSVC
`/std:c++17 /EHsc /W4 /WX /Od /RTC1`, sans lancer le writer complet.

## FF minimal du nouveau writer

Après un writer réellement compilé et son roundtrip mesuré :

```powershell
python ops/doom-source/prepare_ff.py --writer-run <writer réel> --output <racine fraîche>
pwsh -NoProfile -File ops/doom-source/Build-FF.ps1 -SourceRoot <racine fraîche> `
  -ReaderRun <writer réel> -StockToolRoot <dt retenu> `
  -ToolProvenance <provenance tool pinnée> -RunRoot <run neuf> -DryRun
```

Retirer `-DryRun` seulement après GO/admission. Le writer et le FF utilisent
des builders distincts du cube : aucun changement de ses compteurs, noms,
inventory ou allowlist de hashes. Le FF conserve le matériau retail comme
référence, puis re-dump et compare toute la géométrie avec le nouveau reader.
Les empreintes de la source FF, du reader et du tool sont relues après chaque
processus. La réservation est libérée après restauration confirmée.

L'orchestrateur local ignoré `runtime/doom-source-candidates/Invoke-HelmetRigid.ps1`
expose séparément `Plan`, `Source`, `WriterPlan`, `Writer`, `FFSource`, `FFPlan`
et `FF`. Sa valeur par défaut est `Plan`, sans extraction, compilation ni jeu.
Le rendu nécessite ensuite une scène/route/cache spécifiques et une admission
du candidat FF/hash/reader mesuré ; le runner cube refuse ce nouveau payload.

Le run FF mesuré fait 91036 octets, SHA-256
`AD570ACED38C25305AF1C4C608B294C42C9951E71EE5C79E536E67D596166711`.
Le reader est `BD957348470618B577F2DD1C765261E9BD6DCB18D32A24BB9FA451231065C129`.
Build, verification, dump et roundtrip complet ont réussi ; stock/restauration
confirmés et lease libérée. Les fichiers/provenances restent dans les quatre
racines `helmet-rigid-a*` ignorées. Les pixels, tangentes et gameplay manquent.

## Préflight rendu indépendant

```powershell
pwsh -NoProfile -File ops/doom-source/test_runtime.ps1 `
  -MeasuredRun runtime/doom-source-candidates/helmet-rigid-a-ff-build
pwsh -NoProfile -File ops/doom-source/Doom-ModelLab.ps1 `
  -GameRoot <client de base> -CandidateRoot <dedicated retenu> `
  -DoomBuildRun runtime/doom-source-candidates/helmet-rigid-a-ff-build
```

Sans `-Run`, ce dernier valide le FF, l'archive native 3B9F, la fixture/scénario
et le plan, sans réservation ni lancement. Le véritable rendu exige le GO puis
`-Run`. Le helper réutilise transactions/base client/cleanup actuels, mais garde
route, modèle, dvars, inventaire et hashes propres au Doom. La fixture effectue
deux captures et échange les modèles aux mêmes poses sans toucher les angles
du joueur. Elle ne prétend ni DObj/GPU ni pixels par son seul `setmodel`.

## Image originale et petit squelette

`prepare_checker.py` prépare, sans compiler ni lancer, un TGA original 256²
BGRA avec alpha255, coins rouge/vert/bleu/jaune et axes asymétriques. Il transforme
seulement l'image de couleur semantic14 du petit JSON mesuré et conserve normal
retail/technique comme références ; cinq sidecars de state/constantbuffer sont
renommés et hashés dans le manifest local. Aucun pixel retail n'est copié.
Le checker utilise le chemin custom DDS/TGA resident `streamed=0` du pin :
pixelData dans le FF, pas un PAK de streams inventé. Les éventuelles images
streamées ultérieures réutiliseront les contrôles Rhino de descriptors/.pak.

La même préparation écrit un ruban original de six vertices/quatre triangles,
deux bones parentés, poids1/.5 et poses bind/45°, avec oracle CPU indépendant.
Les trois tests `test_prepare_checker.py` vérifient axes image, topologie,
poids et transformation bind/pose. Le writer skinned et l'animation moteur
restent à implémenter/mesurer ; ce petit contrôle ne vaut pas un retarget Doom.

## Blender portable pour l'Imp

L'archive officielle Blender4.2.23 LTS Windows x64 est acquise et hashée :
383193007 octets, SHA-256
`82E791475779A7342424A480BDDE9A20B43710DA9264C60346125AA16CD910CB`.
`Acquire-Blender.ps1` montre le plan par défaut ; `-Download` utilise le ZIP et
le checksum du [répertoire officiel](https://download.blender.org/release/Blender4.2/).
L'acquisition n'extrait, n'installe et ne lance rien.

Sous une future réservation complète, après extraction fraîche vérifiée :

```powershell
<blender portable> --factory-startup --disable-autoexec --background --threads 4 `
  <Imp exact .blend> --python-exit-code 23 --python <inspect_blender.py absolu> `
  -- --output <inspection neuve absolue>
```

L'ordre des flags avant le `.blend` suit la [documentation CLI officielle](https://docs.blender.org/manual/en/4.2/advanced/command_line/arguments.html).
L'inspecteur local borne les datablocks, vérifie hash/source et autoexec,
recense raw bones/use_deform/parents/bind matrices, meshes/UV/materials,
modifiers/groupes, images packées et actions. Il ne demande ni depsgraph,
évaluation de drivers ni exécution de Text. Il n'a pas encore été exécuté dans
Blender : aucune nouvelle preuve de rig/bake/clip n'en découle à ce stade.
