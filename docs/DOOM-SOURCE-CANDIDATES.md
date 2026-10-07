# Sources Doom préparatoires

Ces candidats ne constituent pas un package IW7 prêt. Le casque Slayer a passé
l'extraction réelle, le writer et le roundtrip FF le 2026-10-07 ; aucun rendu Doom
ni rig animé n'est encore prouvé. Les licences affichées restent attribuées à
leurs sources respectives.
Les sources téléchargées restent dans `runtime/doom-source-candidates` ignoré.

| Candidat | Source publique et auteur affiché | Preuve et limite |
| --- | --- | --- |
| Slayer | [The Models Resource, asset 326452](https://models.spriters-resource.com/pc_computer/doometernal/asset/326452/), uploader Gordon_Ulteam | ZIP public téléchargé normalement : 154635910 octets, SHA-256 `15F0908392F3E9E0DAAF9C286FC3E884243A62BAB17BFFDAE62A6F6B654DC361`. Central directory : DAE, FBX et PNG ; aucune licence affichée sur la page, rig/polycount non vérifiés. |
| Imp | [Publication publique ElVitt0ri0](https://www.patreon.com/ElVitt0ri0/posts/imp-doom-eternal-109524568) | Pièce jointe `.blend` publique, 12268984 octets, SHA-256 `C94068D904C5495FEB1F29779EBA04A43F6BD5EFD0D29D16729564574C9A2FD3`. Rig annoncé par l'auteur, non ouvert/vérifié. Conditions affichées : pas de NSFW, crédit Bethesda/id Software et du porteur. Ce n'est pas une licence générale sur les assets du jeu. |
| Super Shotgun | [irons3th, Sketchfab](https://sketchfab.com/3d-models/ff586a5ce02641959cc9b75dc15237bf) | API publique : 39183 triangles, 16983 sommets, CC BY 4.0 affichée ; archive non récupérée, téléchargement officiel exige authentification. |
| Shotgun alternatif | [tnnv, Sketchfab](https://sketchfab.com/3d-models/5929e6949d1e421e927116e117248f07) | 4074 triangles, 2097 sommets, CC BY 4.0 affichée ; archive non récupérée pour la même raison. Modèle original déclaré Blender/Quixel, pas un port Doom Eternal démontré. |
| Super Shotgun acquis | [ExodeCode, itch.io](https://exode.itch.io/super-shotgun-doom-2016) | Fan model Doom 2016, licence CC BY 4.0 affichée par l'auteur. Téléchargements publics normaux récupérés le 2026-10-07 : FBX binaire 7400 de 121132 octets, SHA-256 `2C9E169F36E2D8A2C1849BFCC6FB064367B549BA50415BA25C0732CA769BA9E5`, et cinq PNG 2048². Inspection complète bornée : un mesh statique, aucun Deformer ni AnimationStack/AnimationCurve ; port IW7 non vérifié. |

Les métadonnées publiques Sketchfab ont également été retenues pour Slayer
`bd2e6094f85041798066ee4824313e4d` (DevinBriggs, 226906 triangles, une animation)
et Imp `16fb0ec45bba4e048479b26df3564c8f` (DJ_Nugget, 34488 triangles).
Ces pages affichent CC BY 4.0, mais leurs archives nécessitent aussi le mécanisme
authentifié de la [Download API officielle](https://sketchfab.com/developers/download-api/downloading-models).
Aucun accès protégé n'a été contourné. La nouvelle arme publique ExodeCode est
acquise. Prochaine étape : rendu géométrique protégé du casque, matériau original
à UV connus, puis preuve originale de skinning avec deux os avant tout grand rig.

## Inspection locale bornée — 2026-10-07

`ops/doom-source/inspect_sources.py` vérifie d'abord les deux hashes source.
Il lit le DAE en mémoire (9.17 MB au plus dans ce candidat), les seuls headers
FBX/PNG et les blocs Blender en flux, sans écrire ni ouvrir les assets dans un
logiciel 3D. Sortie locale : `runtime/doom-source-candidates/source-inspection.local.json`.
Le module [zstandard 0.25.0](https://pypi.org/project/zstandard/0.25.0/) est installé
uniquement dans `runtime/doom-source-candidates/inspector-deps` ; aucun Python
global n'a été modifié. Limite de sortie Blender : 32 MiB / 65536 blocs.
Lecture réelle : 19156076 octets jusqu'à ENDB ; contexte décodeur 2285396 octets.

| Source | Structure démontrée | Ce qui reste inconnu |
| --- | --- | --- |
| Slayer `doomslayer_cine_3p_LOD0` | FBX binaire 7400 ; COLLADA 1.4.1 export Cinema4D 15.064, Y_UP, centimètres. 15 géométries, 65300 positions source, 86223 triangles déclarés, 255 nœuds JOINT, 15 contrôleurs skin. 15 matériaux/15 images référencées, toutes présentes ; 59 PNG de 128² à 4096². Aucun channel/clip d'animation dans le DAE. | Les positions source ne comptent pas les sommets séparés par UV/normale du mesh exporté. Hiérarchie, bind pose, poids et animations éventuelles du FBX non importés ; source « cine 3p », pas un viewmodel FPS démontré. |
| Imp ElVitt0ri0 | `.blend` Blender 4.01, 64 bits little-endian, Zstandard. Inventaire de blocs complet : 130 Mesh, une armature ; SDNA du fichier résout 670 Bone, 670 pose channels, six ArmatureModifierData, dix Image et neuf ImagePackedFile/PackedFile. 182 FCurve, aucun bloc bAction. | Les courbes peuvent être des drivers : aucun clip de marche/attaque/death validé. Mapping mesh/texture/poids et compatibilité IW7 inconnus. Le fichier contient aussi un Text avec 2001 TextLine ; ne jamais exécuter ce code embarqué lors d'une future inspection. |

Ces counts viennent des sources exactes. Les 670 Bone de l'Imp incluent
potentiellement des contrôleurs/helpers ; ils ne doivent pas devenir directement
670 bones moteur. Le SDK ZoneTool IW7 retenu déclare `numBones` et `numRootBones`
en octets, `numClientBones` en ushort, `parentList` en octets. La présence de
client bones n'est pas la preuve d'une chaîne de skinning compatible avec ce rig.
Les surfaces ont `vertCount`/`triCount` en ushort : garder des surfaces séparées
et compter les sommets après séparation UV/normales, avant sérialisation.

## Pipeline candidat à partir du cube rendu

1. Conserver le cube LOD1M comme contrôle géométrique : single LOD, shadow6,
   collision255, diagnostic GPU et A/B deux poses. Ajouter d'abord une texture
   originale de contrôle avec UV connus pour prouver image → material → pixels.
   Les normales/tangentes et le packing général ne sont pas validés par un cube
   sombre simplement visible.
2. Exporter un seul élément Slayer rigidifié, par exemple casque, en bind pose,
   avec un seul matériau et `tag_origin`, puis comparer silhouette/UV/normales
   avant/après roundtrip XModel/XSurface/FF. Convertir Y_UP explicitement ; choisir
   une échelle depuis une hauteur cible mesurée dans la scène de test, sans
   supposer que « centimètre source » égale « unité moteur ».
3. Prouver une armature originale de deux bones et un mouvement simple avant de
   porter un personnage : parents, bind/inverse-bind, poids quantifiés, flags
   SKINNED et buffers de blends doivent survivre au reader et au rendu animé.
   L'écriture rigid actuelle n'a ni blends ni animation ; il faut une nouvelle
   capacité testée, pas remplacer son compteur de bones.
4. Inspecter les rigs sous réservation avec Blender 4.1 compatible, lancement
   `--factory-startup --disable-autoexec --background` et un script inspecteur
   local contrôlé. Pour l'Imp, extraire un squelette de déformation limité,
   résoudre les drivers/contraintes puis bake des poses et clips explicites.
   Le retarget sur une animation IW7 devra être évalué séparément de l'apparence.
5. Seulement après ces preuves : materials/textures dédiées bornées, animations
   locomotion/attaque/dégâts/death, acteur naturel et cleanup. Slayer troisième
   personne, mains FPS et arme sont trois livrables distincts. Aucun statut
   « Doom ready » tant que les critères visuels et gameplay manquent.

Nouvelle recherche arme : Models Resource ne liste que BFG pour Doom Eternal.
[BlacksmithingGamer/Thingiverse 4236707](https://www.thingiverse.com/thing:4236707)
et sa [republication Nexprint](https://www.nexprint.com/en/models/G6686129)
proposent un Super Shotgun pour impression (neuf STL, 20.23 MB annoncés, CC BY
affichée sur Nexprint), sans textures/rig démontrés. La page auteur est accessible,
mais la route normale `/zip` renvoie du HTML, aucune archive. Aucun endpoint de
viewer ni mécanisme protégé n'a été utilisé pour obtenir ces meshes.

## Casque sélectionné et writer source

L'introspection DAE identifie `ID346 / KoreLibMesh08`, controller `ID545`,
géométrie `ID546` et binding `Material1 → ID58 / doomslayer_game_helmet`.
Le diffuse suit `effect ID59 → sampler ID62 → surface ID61 → image ID60`,
fichier `doomslayer_game_helmet.png`. Cette pièce comporte 2852 positions,
2852 normales, 2839 UV et 4092 triangles déclarés. Les tuples position/normal/UV
ont été séparés : le compte exporté réel est 2852 sommets et 4092 triangles.
Le node est directement dans la scène, rotation zéro, scale unitaire et
bind-shape identité ; la petite translation source est conservée.

`ops/doom-source/prepare_rigid_mesh.py` prépare uniquement cette géométrie bind,
cm vers mètres et Y_UP vers Z_UP par `(x,-z,y)`, determinant positif,
pivot au centre AABB des positions utilisées. UV conservés sans flip/clamp,
normales normalisées, indices et winding contrôlés ; aucune pose skin évaluée.
L'extraction réelle a réussi sans réduire les gardes UV/winding. Elle relève
17 triangles à UV miroirs ; la handedness des tangentes reste à vérifier au rendu.

`prepare_writer.py` et `writer_rigid.cpp` constituent un candidat prop rigide
indépendant, single material et root bone. Une hauteur cible explicite de
16 unités moteur détermine le facteur unités/mètre depuis la hauteur source,
avec bbox/radius réels, counts ushort bornés, LOD1M, shadow6 et collision255.
Le packing UV IEEE half général est testé ; normals/tangents, handedness et
rendu restent non validés. La compilation réelle MSVC `/W4 /WX` a réussi sans
warning. Le reader a comparé tous les vertices/indices. Hauteur source 0.31681 m,
facteur 50.5034563302926 unités/m, demi-bbox (6.9457654953, 7.8899784088, 8),
radius 9.6318130493 ; ce sont les mesures du casque, pas du cube.

Pour le second candidat texturé, le pin ZoneTool `fab935826c898806855376662a8a03317b3ad8f1`
charge DDS ou TGA via DirectXTex (`iw7/assets/gfximage.cpp`), pas PNG directement.
Le Texconv source est présent dans `deps/DirectXTex/Texconv`; aucun exécutable
mesuré n'a été trouvé. Une conversion PNG vers DDS et une texture originale
de contrôle doivent d'abord vérifier format, mip count, UV et couleur au rendu.
Le matériau peut reprendre seulement le petit JSON de référence, validé par
son hash, puis remplacer son image diffuse par un nom custom explicite ; aucune
texture retail n'est copiée. Les chemins de référence material/image du pin
utilisent `paris_enemy_` pour le nom FF : ce préfixe est requis pour les dépendances
custom dans cette implémentation. Garder un nom d'asset `paris_doom_*` distinct.
Le candidat géométrique initial conserve le matériau retail mesuré ; les deux
étapes doivent avoir des manifests séparés et rester `ready=false` avant rendu.

## Staging FF indépendant et nouvelle source d'arme

`ops/doom-source/prepare_ff.py` n'accepte que le nouveau writer rigide mesuré :
manifest source inchangé, reader binaire mesuré, hashes XMB/XSB, counts réels et
roundtrip complet. Il génère cinq entrées explicites, sans texture/material retail
copié. Le nom FF est `paris_enemy_doom_helmet_rigid_a` ; le modèle conserve
`paris_doom_helmet_rigid_a`. Le wrapper `Build-FF.ps1` réutilise les helpers de
process/transaction/restauration existants, avec un schéma Doom et une inventory
exacte indépendants. Admission : 8 GiB RAM / 11 GiB commit, bootstrap borné et
seulement `assetfile1.pak`. Le reader recontrôle tous les vertices/indices issus
du FF. Les trois tests Python de staging et 22 gardes PowerShell passent sur des
fixtures synthétiques. Le run réel `helmet-rigid-a-ff-build` a terminé les
processus build/verify/dump/reader avec code zéro. Le FF fait 91036 octets,
SHA-256 `AD570ACED38C25305AF1C4C608B294C42C9951E71EE5C79E536E67D596166711` ;
le writer/reader fait foi avec SHA-256
`BD957348470618B577F2DD1C765261E9BD6DCB18D32A24BB9FA451231065C129`.
Les cinq assets attendus et la géométrie complète ont été vérifiés. Restauration
confirmée, stock préservé, aucune cleanup error ni lease retenue ; registre vide
à 10:30:15.875 UTC. Les répertoires `helmet-rigid-a`, `helmet-rigid-a-writer`,
`helmet-rigid-a-ff-source` et `helmet-rigid-a-ff-build` restent ignorés.

Le rendu prépare un helper distinct `Doom-ModelLab.ps1`, une route HTTP dédiée
et le tuple FF/reader exact ci-dessus. Sans `-Run`, il ne lance et ne réserve rien.
Le dry-run a validé l'archive native 3B9F mesurée et les hashes de ses 26 sources,
en distinguant les sources archivées des dépendances inchangées du projet.
Le parse GSC réel a réussi ; 22 gardes runtime/HTTP passent, dont livraison du
vrai payload, refus de la route cube, journal frais et fermeture du worker.
Le GO de coordination a permis le rendu réel décrit ci-dessous. Aucun diagnostic
GPU cube n'est attribué au casque, et `ready=false` demeure jusqu'aux preuves
visuelles/gameplay.

Le premier run `runtime/doom-model-lab/20261007-112529-712-338258f4` échoue sur
`PairOwnership` absent du contexte client unique sous StrictMode, puis pendant
cleanup pour la même raison. `manual-recovery.local.json` conserve les identités,
la clôture exacte après30 secondes UDP à zéro clients et les trois transactions
restaurées ; la lease est libérée à11:28:12 UTC. Le constructeur partagé est
corrigé avec valeurs réelles/null, sans coercition de l'objet de paire. Huit tests
exécutent ce constructeur et les chemins update/cleanup ordinary et dispatch pair.

Le replay `runtime/doom-model-lab/20261007-113022-458-eb383a90` réutilise le FF
AD570 et l'exécutable archivé3B9F, avec admission14GiB/15GiB. Un GET frais et le
cache client prouvent la livraison des91036 octets ; heartbeat frais godmode=1,
inactivity=0, cheats=0 précède les captures. Le scénario capture-only réussit,
avec zéro assertion gameplay. Inspection réelle des deux BMP1280x720 : le clown
retail est visible à gauche initialement, puis à droite après échange des modèles
aux mêmes poses ; le casque est invisible aux deux emplacements. Le résultat
visuel est négatif. Les trois restaurations sont confirmées, HTTP arrêté,
Failure/CleanupError null, aucun processus IW7 et leases vides à11:32:52 UTC.
`doom-runtime.local.json` conserve PixelsVerified/GameplayVerified/Ready=false.
Les BMPs et `visual-assessment.local.json` restent ignorés. Le prochain diagnostic
doit mesurer le modèle Doom réel (bounds/surface/material), sans attribuer le
diagnostic GPU du cube à ce candidat ou affaiblir les gardes source.

La route gratuite publique de l'auteur ExodeCode a fourni le FBX et cinq textures
PBR, sans compte, paiement ni résolution de CAPTCHA. Les fichiers sont conservés
dans `runtime/doom-source-candidates/ssg-exode-20261007`, avec tous les hashes dans
`source-acquisition.local.json`. La texture diffuse fait 4423931 octets, SHA-256
`DB1AF4FBFE7816908ED6B2B837473049A2FD0BACDE9A6B580EA7798D45008A3D`.
Toutes sont 2048² : la normal map est RGB 16 bits ; les quatre autres PNG sont
RGB 8 bits. La conversion doit conserver ou déclarer explicitement cette
précision, puis mesurer le mapping roughness/metalness vers le matériau IW7.
Le modèle est une création fan Doom 2016, pas un asset Doom Eternal démontré.
`inspect_fbx.py` a lu les 371 nœuds et 225000 octets d'arrays décompressés, sous
bornes de taille/profondeur, avec contrôle de fin zlib, floats et indices.
Les arrays réels contiennent 1395 positions et 1752 polygones : 993 quads,
754 triangles, cinq pentagones. Leur compte par éventail vaut 2755 triangles,
mais aucune triangulation ni séparation UV/normales n'a été exécutée.
L'inventaire Objects complet n'a aucun Deformer, AnimationStack ou AnimationCurve.
Quatre tests bornés passent. `fbx-inventory.local.json` conserve les preuves.
L'attribution locale conserve titre, auteur, URL, licence et état des modifications ;
la licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) affichée
concerne cette création fan et ne constitue pas une licence générale sur Doom.
