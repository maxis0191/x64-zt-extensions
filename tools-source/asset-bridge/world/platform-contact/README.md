# One authored platform and one player-contact box — SOURCE

World owns this small correspondence reader. SDK owns the authoring project and
Use behavior; serializer/material owners own geometry/material preparation and
readback. Physics owns the existing a572 player fixture; caller55 owns loading,
the retained session, protection and restoration. This does not add a serializer,
native ABI, driver or lab framework. Frozen original-arena writer D is unchanged.

`platform_contact.py` consumes the existing `iw7.original-mesh-source/1` geometry
document. It checks one rigid identity root, one surface/LOD, 24 face-local
vertices and 12 outward triangles forming all six complete faces. Merely matching
the bounding box is insufficient: dents, absent/overlapping faces, wrong normals
and inward triangles are refused. Mesh generation remains with the authoring
owners. A named material reference is recorded without proving its payload.

The fixed a572 fixture has no bounds parameter. The authored platform must use
local minimum `(-128,-128,0)`, maximum `(128,128,16)`, angles zero and scale one.
Given the same player anchor **P** frozen after protected readiness/ground checks:

| Quantity | Exact IW7 game coordinates |
| --- | --- |
| Render origin O | P + (0,0,96) |
| Absolute box minimum | P + (-128,-128,96) |
| Absolute box maximum | P + (128,128,112) |
| Native center C / half size | P + (0,0,104) / (128,128,8) |
| Player test start | P + (0,0,208) |

Anchor P must stay within a572's existing ±30000 envelope on every axis.
All anchor/offset/endpoints must remain exact float32, with absolute box widths
exactly (256,256,16) so an earlier float64 addition cannot hide collapsed bounds.
Rendering and the native
midpoint/half-size reconstruction must yield identical endpoints. The native
provider already applies its internal 1/32 conversion; callers pass absolute
IW7 coordinates once. The collision owner is a distinct `script_model`, solid
before `collision_createbox(minimum,maximum,1)`, in world0 with identity rotation.
Its entity transform is not implicitly applied to these absolute coordinates.
This profile refuses a differently sized source instead of adapting a572 silently.

From the product root, using absolute paths for the two JSON files:

```powershell
python -B tools-source/asset-bridge/world/platform-contact/platform_contact.py --geometry-source <geometry.source.json> --source-anchor 0 0 0 --output <fresh-contact.source.json>
python -B -m unittest discover -s tools-source/asset-bridge/world/platform-contact -p test_platform_contact.py
```

The example anchor is a SOURCE preview, never an actual admitted pose. The reader
binds the geometry's actual bytes by SHA-256, uses the existing bounded strict
JSON/path reader and creates only a fresh JSON. It reads no stock, PE or FF and
launches no build/game. The output cannot claim actual-anchor, material, render,
native contact, movement, prediction, cooperative-client or runtime acceptance.

## Behavior jointure and remaining caller work

The visual must stay present through all three phases and contribute **zero**
additional colliders/physics assets. F0: no native body and a measured fall. F1:
one body, landing, standing600ms, ordinary forward movement300ms with measured
distance4..64units. After released-stable250ms, one coordinated Use press produces
one counter increment/toggle and requests F2 removal. F2 clears the body while
the owner remains alive, measures a new fall, then deletes the owner. The SDK
counter observes that same action; a second input driver is not introduced.

These are requirements for later integration, not measured behavior. The current
caller246 collision route is exclusive with empty `fs_game`; it does not already
load the authored model/material/SDK package. Native785 collision/protect/input
capabilities do not imply inclusion of later a572 helpers or caller246. SDK's
existing beacon notification is not a frozen generic World instance interface.
Thus `sdk_project_bound` and `caller_asset_loading_bound` stay false. Once the
authoring owners publish their exact namespace/model/script inputs, caller55
must bind that cohort and a shared audited P in a separate reviewed source change.

No FF/CPP/PE/stock/lease/Game GO is included. Actual render identity, asymmetric
texture orientation/alpha, identical rendered bounds, absence of implicit
colliders, fresh engine protection/inactivity state, F0/F1/F2 contact and ordinary
movement require a separately reviewed admitted run. Client prediction/co-op
remain separate. This platform is a prop/floor augmentation in a retail map;
it does not qualify an authored GfxWorld, clipmap, navigation, lights, visibility,
map spawns or a complete new map. No BO3 donor/extraction is needed for the
authored source correspondence, and no deleted stock/lab is restored.

Source review corrected two initial omissions: an exact float32 anchor such as
2**100 could lose offsets during the earlier float64 addition, and32768 was
outside a572's anchor envelope despite preserving the box dimensions. The reader
now checks exact absolute dimensions and the existing ±30000 limit independently;
targeted negatives exercise both refusals, with both boundary signs accepted.
