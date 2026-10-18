// AUTHORED, NOT COMPILED/LINKED/EXECUTED at Source preparation.
// Ordinary typed owners + REAL preflight, synthetic components only. No native
// core, actual arena/FILE/route, provider, admission, engine or activation.
// ONE literal case copied without producer/import from Asset ecb0c2577462c951702552760b84760ae98b2b20:
// test_native_pair_bodies.cpp blob f97648d0490f04517511fd1b9ec52c1db0d385a4,
// 111018B/SHA256 63626107a51483559cf1bd17e2bc4f2e6a8e7b688924d5749e31c4671d49d802.
#include "native_pair_owned_session.hpp"
#include <cstdlib>
#include <exception>
#include <iostream>
#include <new>
#include <string_view>

namespace input = player_pair_input;
namespace owned = player_pair_owned_session;
namespace bodies = iw7::neutral::player_pair_bodies;
using Json = nlohmann::ordered_json;
struct Guard;
struct Observation;
struct Primary;
static void record_raw_delete() noexcept;
namespace allocation_fault {
    struct Failure : std::bad_alloc {};
    bool armed = false, watch_raw = false, moved_before_raw = false;
    std::size_t remaining = 0, attempts = 0, last_size = 0, live = 0, raw_deletes = 0;
    void* raw_address = nullptr;
    std::unique_ptr<Guard>* caller_guard = nullptr;
    Observation* observer = nullptr;
    const Failure* primary = nullptr; // Compared only while the receiving handler is alive.
}
void* operator new(std::size_t bytes) {
    ++allocation_fault::attempts; allocation_fault::last_size = bytes;
    if (allocation_fault::watch_raw && bytes == sizeof(input::OwnedInput) && !allocation_fault::raw_address)
        allocation_fault::moved_before_raw = allocation_fault::caller_guard && !*allocation_fault::caller_guard;
    if (allocation_fault::armed && !allocation_fault::remaining) {
        try { throw allocation_fault::Failure(); }
        catch (const allocation_fault::Failure& error) { allocation_fault::primary = &error; throw; }
    }
    if (allocation_fault::armed) --allocation_fault::remaining;
    if (void* value = std::malloc(bytes ? bytes : 1)) {
        ++allocation_fault::live;
        if (allocation_fault::watch_raw && bytes == sizeof(input::OwnedInput) && !allocation_fault::raw_address)
            allocation_fault::raw_address = value;
        return value;
    }
    throw std::bad_alloc();
}
void operator delete(void* value) noexcept {
    if (!value) return;
    if (value == allocation_fault::raw_address) { ++allocation_fault::raw_deletes; record_raw_delete(); }
    --allocation_fault::live; std::free(value);
}
void* operator new[](std::size_t bytes) { return ::operator new(bytes); }
void operator delete[](void* value) noexcept { ::operator delete(value); }
void operator delete(void* value, std::size_t) noexcept { ::operator delete(value); }
void operator delete[](void* value, std::size_t) noexcept { ::operator delete(value); }
static void check(bool value) { if (!value) throw std::runtime_error("Typed ingress authored witness refused"); }
// Original four literals only; no old header/runtime or renderer is consumed.
static const std::array<std::string_view,4> original_raw{{
    R"IW7AUTH({"schema":"iw7.neutral-weapon-clone/1","profile":"iw7-shredder-neutral-1-0","weapon":"sdk_shredder_clone_zm","pap_attachment":"sdk_shredder_clone_pap_zm","source_weapon":"iw7_shredder_zm","source_pap_attachment":"shredderpap1","pap_attachment_slot":"attachments6","upgraded_engine_variant":"sdk_shredder_clone_zm+sdk_shredder_clone_pap_zm","observed_base_type":1,"observed_pap_type":0,"source_enum_map":{"base":"WEAPTYPE_BULLET","pap":"WEAPTYPE_NONE"},"source_layout_pin":"fab935826c898806855376662a8a03317b3ad8f1","json_mechanics_fields_preserved":true,"external_name_driven_gameplay":"unverified: private names do not inherit Shredder GSC callbacks","visuals":"unchanged IW7 references; dependency bodies not captured","input_sha256":{"manifest":"fc2aa7f5cdb55ac98f48f2fe05b73e76c487f4b4a916754635dfdc3020a199c1","weapon":"49b3b2f15b599c94a72dad0b7b30103bab147eb8b17ce6b82c4526e797c6b92a","pap":"dbd47e9e246bb55de944cf4ba7ca9ed8d15d30afc91f5dc3be292ec7709abeea"},"files":[{"path":"weapons/sdk_shredder_clone_zm.json","bytes":22356,"sha256":"0da006d96531b0d8afc74e6da211911a3c5b71b34c8104101926222bd5f9aa03"},{"path":"attachments/sdk_shredder_clone_pap_zm.json","bytes":1806,"sha256":"088c665ca39c03daa3a6c8b84821318389611a5ef5b895223e263a5cdbe5969b"},{"path":"zone_source/sdk_shredder_clone_zm.csv","bytes":66,"sha256":"f539cb31e182b7648cac4eb4da369e344d0a8da1a877c4fbed1dc23ef105f2c8"}],"bo3_assets_authenticated":false,"external_name_driven_gameplay_verified":false,"native_parser_verified":false,"ff_built":false,"roundtrip_verified":false,"runtime_abi_verified":false,"lifetime_verified":false,"weapon_granted":false,"projectile_damage_verified":false,"physics_qualified":false,"retail_pap_transaction_verified":false,"gameplay_accepted":false,"ready":false})IW7AUTH",
    R"IW7AUTH({"szInternalName":"sdk_shredder_clone_zm","szDisplayName":"A","szLootTable":null,"hideTags":null,"attachments":null,"attachments2":null,"attachments3":null,"attachments4":null,"attachments5":null,"attachments6":["sdk_shredder_clone_pap_zm"],"notetrackSoundMapKeys":null,"notetrackSoundMapValues":null,"notetrackOverrides":null,"notetrackSuitEntries":null,"fAdsZoomFov":0,"iAdsTransInTime":0,"iAdsTransOutTime":0,"iClipSize":0,"vfxImpactType":0,"sfxImpactType":0,"meleeImpactType":0,"penetrateMultiplier":0,"fAdsViewKickCenterSpeed":0,"fHipViewKickCenterSpeed":0,"szAltWeaponName":"abcde","killIcon":null,"dpadIcon":null,"ammoDropStockMax":0,"adsDofStart":0,"adsDofEnd":0,"accuracyGraphKnots":[null,null],"motionTracker":false,"enhanced":false,"dpadIconShowsAmmo":false,"luiWeaponInfoWidgetUsesScopeStencil":false,"szAdsrBaseSetting":null,"szLUIWeaponInfoWidgetName":null,"szLUIWeaponInfoWidgetTag":null,"szLUICrosshairWidget":null,"weapDef":{"szOverlayName":null,"szModeName":null,"szAmmoName":null,"szSharedAmmoCapName":null,"szUseHintString":null,"dropHintString":null,"szScript":null,"gunXModel":null,"gunXModelLeftHand":null,"gunXModelRightHand":null,"defaultViewModel":null,"defaultWorldModelLeftHand":null,"defaultWorldModelRightHand":null,"worldModel":null,"worldXModelLeftHand":null,"worldXModelRightHand":null,"defaultWorldModel":null,"playerShadowModel":null,"playerShadowModelLeftHand":null,"playerShadowModelRightHand":null,"handXModel":null,"complexWorldModel":null,"complexWorldModelLeftHand":null,"complexWorldModelRightHand":null,"complexGunXModel":null,"complexGunXModelLeftHand":null,"complexGunXModelRightHand":null,"camoWorldModelMaterialOverride":[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],"camoViewModelMaterialOverride":[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],"szXAnims":null,"szXAnimsRightHanded":null,"szXAnimsLeftHanded":null,"notetrackRumbleMapKeys":null,"notetrackRumbleMapValues":null,"notetrackFXMapKeys":null,"notetrackFXMapValues":null,"notetrackFXMapTagValues":null,"playerAnimType":0,"scriptedAnimEvent":0,"scriptedAnimType":0,"weapType":1,"whizbyType":0,"weapClass":0,"penetrateType":0,"deathAnimDamageType":0,"inventoryType":0,"fireType":0,"targetAssistType":0,"targetAssistBehavior":0,"targetAssistRange":0,"targetAssistAngle":0,"targetAssistLosOffsetForward":0,"targetAssistLosOffsetRight":0,"targetAssistLosOffsetUp":0,"targetAssistOnlyAvailableInAds":false,"offhandClass":0,"stance":0,"stickiness":0,"dualWieldType":0,"slot":0,"iFireTime":0,"iFireDelay":0,"iFireTimeAkimbo":0,"iFireDelayAkimbo":0,"bSegmentedReload":false,"burstFireCooldown":0,"burstFireAuto":false,"vfxPackage":null,"sfxPackage":null,"reticleType":0,"reticleCenter":null,"reticleSide":null,"reticleOnePiece":null,"iReticleCenterSize":0,"iReticleSideSize":0,"iReticleMinOfs":0,"reticleCenterPulse":false,"activeReticleType":0,"vStandMove":[0,0,0],"vStandRot":[0,0,0],"strafeMove":[0,0,0],"strafeRot":[0,0,0],"vDuckedOfs":[0,0,0],"vDuckedMove":[0,0,0],"vDuckedRot":[0,0,0],"vProneOfs":[0,0,0],"vProneMove":[0,0,0],"vProneRot":[0,0,0],"fPosMoveRate":0,"fPosProneMoveRate":0,"fStandMoveMinSpeed":0,"fDuckedMoveMinSpeed":0,"fProneMoveMinSpeed":0,"fPosRotRate":0,"fPosProneRotRate":0,"fStandRotMinSpeed":0,"fDuckedRotMinSpeed":0,"fProneRotMinSpeed":0,"worldClipModel":null,"rocketModel":null,"knifeModel":null,"worldKnifeModel":null,"hudIcon":null,"pickupIcon":null,"dangerIcon":null,"throwBackIcon":null,"hideWarningIcons":false,"warningIconsDelay":0,"ammoCounterIcon":null,"ammoCounterClip":0,"iStartAmmo":0,"iPerkStartAmmo":0,"iPerkMaxAmmo":0,"iMaxAmmo":0,"shotCount":0,"iSharedAmmoCap":0,"iAmmoUsedPerShot":0,"requireAmmoUsedPerShot":false,"lowAmmoWarningThreshold":0,"disableNoAmmoWarning":false,"damage":0,"playerDamage":0,"meleeDamage":0,"iDamageType":0,"autoAimRange":0,"aimAssistRange":0,"aimAssistRangeAds":0,"aimAssistPitchSlowdown":0,"aimAssistPitchSlowdownAds":0,"aimAssistYawSlowdown":0,"aimAssistYawSlowdownAds":0,"aimAssistLockonStrength":0,"aimPadding":0,"enemyCrosshairRange":)IW7AUTH"
    R"IW7AUTH(0,"moveSpeedScale":0,"adsMoveSpeedScale":0,"sprintDurationScale":0,"sprintRestoreDelay":0,"fAdsZoomInFrac":0,"fAdsZoomOutFrac":0,"overlay":{"shader":null,"shaderLowRes":null,"shaderEMP":null,"shaderEMPLowRes":null,"reticle":0,"width":0,"height":0,"widthSplitscreen":0,"heightSplitscreen":0},"overlayInterface":0,"fAdsBobFactor":0,"fAdsViewBobMult":0,"fHipSpreadStandMin":0,"fHipSpreadDuckedMin":0,"fHipSpreadProneMin":0,"hipSpreadSprintMin":0,"hipSpreadInAirMin":0,"hipSpreadStandMax":0,"hipSpreadDuckedMax":0,"hipSpreadProneMax":0,"hipSpreadSprintMax":0,"hipSpreadInAirMax":0,"fHipSpreadDecayRate":0,"fHipSpreadFireAdd":0,"fHipSpreadTurnAdd":0,"fHipSpreadMoveAdd":0,"fHipSpreadDuckedDecay":0,"fHipSpreadProneDecay":0,"hipSpreadSprintDecay":0,"hipSpreadInAirDecay":0,"fHipReticleSidePos":0,"fAdsIdleAmount":0,"fHipIdleAmount":0,"adsIdleSpeed":0,"hipIdleSpeed":0,"fIdleCrouchFactor":0,"fIdleProneFactor":0,"fGunMaxPitch":0,"fGunMaxYaw":0,"adsIdleLerpStartTime":0,"adsIdleLerpTime":0,"slideSpreadMin":0,"slideSpreadMax":0,"slideSpreadDecayRate":0,"slideSpreadFireAdd":0,"slideSpreadTurnAdd":0,"swayMaxAngleSteadyAim":0,"swayMaxAngle":0,"swayLerpSpeed":0,"swayPitchScale":0,"swayYawScale":0,"swayHorizScale":0,"swayVertScale":0,"swayShellShockScale":0,"adsSwayMaxAngle":0,"adsSwayLerpSpeed":0,"adsSway_UNKNOWN_Scale":0,"adsSwayPitchScale":0,"adsSwayYawScale":0,"adsSwayHorizScale":0,"adsSwayVertScale":0,"adsFireRateScale":0,"adsDamageRangeScale":0,"adsFireAnimFrac":0,"fireTimerLerpToAdsScale":0,"alwaysFireAtMaxRangeInAds":false,"dualWieldViewModelOffset":0,"fScopeDriftDelay":0,"fScopeDriftLerpInTime":0,"fScopeDriftSteadyTime":0,"fScopeDriftLerpOutTime":0,"fScopeDriftSteadyFactor":0,"fScopeDriftUnsteadyFactor":0,"killIconRatio":0,"iReloadAmmoAdd":0,"iReloadStartAdd":0,"ammoDropStockMin":0,"ammoDropClipPercentMin":0,"ammoDropClipPercentMax":0,"iExplosionRadius":0,"iExplosionRadiusMin":0,"iExplosionForceRadius":0,"iExplosionInnerDamage":0,"iExplosionOuterDamage":0,"damageConeAngle":0,"bulletExplDmgMult":0,"bulletExplRadiusMult":0,"iProjectileSpeed":0,"iProjectileSpeedUp":0,"iProjectileSpeedForward":0,"iProjectileActivateDist":0,"iProjectileDetonationRadius":0,"projLifetime":0,"projLifetimeStdDeviation":0,"timeToAccelerate":0,"projectileCurvature":0,"projectileModel":null,"projExplosionEffect":{"type":0,"fx":"authored_fx0001"},"projDudEffect":{"type":1,"fx":"authored_fx0001"},"projBodyEffect":null,"projTrailEffect":null,"projBeaconEffect":null,"projIgnitionEffect":null,"ricochetChance":0,"riotShieldEnableDamage":false,"riotShieldHealth":0,"riotShieldDamageMult":0,"vProjectileColor":[0,0,0],"guidedMissileType":0,"maxSteeringAccel":0,"projIgnitionDelay":0,"parallelBounce":null,"perpendicularBounce":null,"fAdsAimPitch":0,"fAdsCrosshairInFrac":0,"fAdsCrosshairOutFrac":0,"adsInCrosshairAlphaStart":0,"adsInCrosshairAlphaEnd":0,"adsOutCrosshairAlphaStart":0,"adsOutCrosshairAlphaEnd":0,"adsShouldShowCrosshair":false,"adsGunKickReducedKickBullets":0,"adsGunKickReducedKickPercent":0,"fAdsGunKickPitchMin":0,"fAdsGunKickPitchMax":0,"fAdsGunKickYawMin":0,"fAdsGunKickYawMax":0,"fAdsGunKickMagMin":0,"fAdsGunKickAccel":0,"fAdsGunKickSpeedMax":0,"fAdsGunKickSpeedDecay":0,"fAdsGunKickStaticDecay":0,"fAdsViewKickPitchMin":0,"fAdsViewKickPitchMax":0,"fAdsViewKickYawMin":0,"fAdsViewKickYawMax":0,"fAdsViewKickMagMin":0,"fAdsViewScatterMin":0,"fAdsViewScatterMax":0,"fAdsSpread":0,"iVisibilityAxis":0,"fVisibilityUpOffset":0,"hipGunKickReducedKickBullets":0,"hipGunKickReducedKickPercent":0,"fHipGunKickPitchMin":0,"fHipGunKickPitchMax":0,"fHipGunKickYawMin":0,"fHipGunKickYawMax":0,"fHipGunKickMagMin":0,"fHipGunKickAccel":0,"fHipGunKickSpeedMax":0,"fHipGunKickSpeedDecay":0,"fHipGunKickStaticDecay":0,"fHipViewKickPitchMin":0,"fHipViewKickPitchMax":0,"fHipViewKickYawMin":0,"fHipViewKickYawMax":0,"fHipViewKickMagMin":0,"fHipViewScatterMin":0,"fHipViewScatterMax":0,"multipleReloadClipPercentage":0,"kickAlignedInputScalar":0,"kickOpposedInputScalar":0,"fightDist":0,"maxDist":0,"accuracyGraphName":[null,null],"originalAccuracyGraphKnotCount":[0,0],"iPositionReload)IW7AUTH"
    R"IW7AUTH(TransTime":0,"leftArc":0,"rightArc":0,"topArc":0,"bottomArc":0,"softLeftRightArc":false,"accuracy":0,"aiSpread":0,"playerSpread":0,"minTurnSpeed":[0,0],"maxTurnSpeed":[0,0],"pitchConvergenceTime":0,"yawConvergenceTime":0,"suppressTime":0,"maxRange":0,"fAnimHorRotateInc":0,"fPlayerPositionDist":0,"horizViewJitter":0,"vertViewJitter":0,"scanSpeed":0,"scanAccel":0,"scanPauseTime":0,"adsSpeedMs":[0,0],"minDamage":0,"minPlayerDamage":0,"mid1Damage":0,"mid2Damage":0,"mid3Damage":0,"mid1PlayerDamage":0,"mid2PlayerDamage":0,"mid3PlayerDamage":0,"maxDamageRange":0,"mid1DamageRange":0,"mid2DamageRange":0,"mid3DamageRange":0,"minDamageRange":0,"destabilizationRateTime":0,"destabilizationCurvatureMax":0,"destabilizeDistance":0,"robotechMaxPitch":0,"robotechMaxYaw":0,"robotechFrequency":0,"robotechVariancePitch":0,"robotechVarianceYaw":0,"robotechVarianceFrequency":0,"locationDamageMultipliers":null,"hitLocPriorityMap":null,"unittypeMultipliers":[0,0,0,0,0,0,0,0,0],"fireRumble":null,"meleeImpactRumble":null,"tracerStyle":0,"tracerType":null,"overchargeTracerType":null,"laserTypeFriendly":null,"laserTypeEnemy":null,"turretADSEnabled":false,"turretADSTime":0,"turretFov":0,"turretFovADS":0,"turretScopeZoomRate":0,"turretScopeZoomMin":0,"turretScopeZoomMax":0,"turretOverheatUpRate":0,"turretOverheatDownRate":0,"turretOverheatPenalty":0,"turretOverheatSound":null,"turretOverheatEffect":null,"turretBarrelSpinRumble":null,"turretBarrelSpinSpeed":0,"turretBarrelSpinUpTime":0,"turretBarrelSpinDownTime":0,"turretBarrelSpinMaxSnd":null,"turretBarrelSpinUpSnd":[null,null,null,null],"turretBarrelSpinDownSnd":[null,null,null,null],"missileConeSoundAlias":null,"missileConeSoundAliasAtBase":null,"missileConeSoundRadiusAtTop":0,"missileConeSoundRadiusAtBase":0,"missileConeSoundHeight":0,"missileConeSoundOriginOffset":0,"missileConeSoundVolumescaleAtCore":0,"missileConeSoundVolumescaleAtEdge":0,"missileConeSoundVolumescaleCoreSize":0,"missileConeSoundPitchAtTop":0,"missileConeSoundPitchAtBottom":0,"missileConeSoundPitchTopSize":0,"missileConeSoundPitchBottomSize":0,"missileConeSoundCrossfadeTopSize":0,"missileConeSoundCrossfadeBottomSize":0,"knifeAttachTagOverride":"authored_wtag01","knifeAttachTagOverride2":null,"knifeAlwaysAttached":false,"meleeOverrideValues":false,"aim_automelee_lerp":0,"aim_automelee_region_height":0,"aim_automelee_region_width":0,"aim_automelee_maxPitchMovement":0,"aim_automelee_maxYawMovement":0,"player_meleeHeight":0,"player_meleeWidth":0,"playerMeleeRangeStanding":0,"playerMeleeRangeCrouched":0,"playerMeleeRangeProne":0,"playerMeleeRangeChargeStanding":0,"playerMeleeRangeChargeCrouched":0,"playerMeleeChargeHeightTolerance":0,"shieldAllowFiring":false,"shieldUnkBool":false,"shieldMaxSpeed":0,"shieldAlwaysDisplay":false,"shieldDeployGesture":null,"shieldFireWeapGesture":null,"shieldDeployWhileFiring":null,"shieldRetractWhileFiring":null,"shieldBashGesture":null,"shieldMeleeFx":null,"shieldMeleeFxDelay":0,"HitEarthquakeScale":0,"HitEarthquakeDuration":0,"HitEarthquakeRadius":0,"shieldHitRumble":null,"MissEarthquakeScale":0,"MissEarthquakeDuration":0,"MissEarthquakeRadius":0,"shieldMissRumble":null,"shieldDeployButton":0,"shieldUsesEnergy":false,"shieldMaxEnergy":0,"shieldConsumptionRate":0,"shieldMeleeEnergyCost":0,"shieldMeleeHitEnergyCost":0,"reactiveMotionRadiusScale":0,"reactiveMotionFrequencyScale":0,"reactiveMotionAmplitudeScale":0,"reactiveMotionFalloff":0,"reactiveMotionLifetime":0,"hasAnyTransientModels":false,"sharedAmmo":false,"lockonSupported":false,"requireLockonToFire":false,"isAirburstWeapon":false,"bigExplosion":false,"noAdsWhenMagEmpty":false,"avoidDropCleanup":false,"allowGrenadeSwitching":false,"inheritsPerks":false,"crosshairColorChange":false,"bRifleBullet":false,"bEnergyBullet":false,"armorPiercing":false,"impaling":false,"bBoltAction":false,"aimDownSight":false,"canHoldBreath":false,"meleeOnly":false,"supportsAlternateMelee":false,"canVariableZoom":false,"bRechamberWhileAds":false,"bBulletExplosiveDamage":false,"bCookOffHold":false,"reticleSpin45":false,"bClipOnly":false,"bDoesNotConsume)IW7AUTH"
    R"IW7AUTH(Ammo":false,"bRemoveWeaponOnEmpty":false,"noAmmoPickup":false,"adsFireOnly":false,"cancelAutoHolsterWhenEmpty":false,"disableSwitchToWhenEmpty":false,"suppressAmmoPrimaryDisplay":false,"suppressAmmoReserveDisplay":false,"laserSightDuringNightvision":false,"markableViewmodel":false,"flipKillIcon":false,"bNoPartialReload":false,"reloadDisabled":false,"blocksProne":false,"silenced":false,"isRollingGrenade":false,"dropGrenadeHeldOnDeath":false,"projExplosionEffectForceNormalUp":false,"projExplosionEffectInheritParentDirection":false,"bProjImpactExplode":false,"disableProjectileCrumpleCheck":false,"bProjTrajectoryEvents":false,"bProjWhizByEnabled":false,"stickToPlayers":false,"stickToVehicles":false,"stickToTurrets":false,"stickToNonStick":false,"projEnableMissileStickiness":false,"thrownSideways":false,"hasDetonator":false,"disableFiring":false,"firesOnWeaponSwitch":false,"disableHolding":false,"timedDetonation":false,"explosiveDamageDelay":0,"fuseTime":0,"aiFuseTime":0,"maxHoldTime":0,"holdButtonToThrow":false,"infiniteHold":false,"freezeMovementWhenFiring":false,"offhandAllowsSprint":false,"thermalScope":false,"thermalToggle":false,"outlineEnemies":false,"outlineDepthTest":false,"outlineFill":false,"enemyOutlineR":0,"enemyOutlineG":0,"enemyOutlineB":0,"enemyOutlineA":0,"allyOutlineR":0,"allyOutlineG":0,"allyOutlineB":0,"allyOutlineA":0,"depthScan":false,"depthScanThickness":0,"depthScanR":0,"depthScanG":0,"depthScanB":0,"depthScanA":0,"depthScanOutlineThickness":0,"depthScanOutlineR":0,"depthScanOutlineG":0,"depthScanOutlineB":0,"depthScanOutlineA":0,"depthScanOverlay":false,"depthScanOverlayStrength":0,"depthScanOverlayXTiles":0,"depthScanOverlayYTiles":0,"depthScanOverlayXScroll":0,"depthScanOverlayYScroll":0,"blurSceneAdsInFraction":0,"blurSceneAdsOutFraction":0,"altModeSameWeapon":false,"turretBarrelSpinEnabled":false,"missileConeSoundEnabled":false,"missileConeSoundPitchshiftEnabled":false,"missileConeSoundCrossfadeEnabled":false,"offhandHoldIsCancelable":false,"doNotAllowAttachmentsToOverrideSpread":false,"useScopeDrift":false,"alwaysShatterGlassOnImpact":false,"oldWeapon":false,"jumpSpread":false,"noFullViewmodelAnimations":false,"killcamOffset":0,"useDualFOV":false,"disableDrop":false,"preferredDrop":false,"gestureAnimation":null,"gestureFireStateTime":0,"gesturePullback":null,"minPullbackTime":0,"gestureThrow":null,"gestureFireTime":0,"gestureDetonate":null,"gestureDetonationTime":0,"unk_433":0,"unknownString1":null,"unk_434":0,"unknownString2":null,"gesturesDisablePrimary":false,"cameraFireEffect":null,"cameraFireEffectDurationSec":0,"changedFireTime":0,"changedFireTimeAkimbo":0,"changedFireTimeNumBullets":0,"chargeType":0,"chargeGain":0,"chargeCostPerShot":0,"chargeLossWhenIdle":0,"chargeEmptyCooldown":0,"chargeFireAtMaxDamageMultiplier":0,"chargeMeterEffectBoneCount":0,"chargeMeterEffect":null,"chargeUpSound":null,"chargeDownSound":null,"chargeUpSoundPlayer":null,"chargeDownSoundPlayer":null,"chargeDownToUpSound":null,"chargeDownToUpSoundPlayer":null,"chargeUpToDownSound":null,"chargeUpToDownSoundPlayer":null,"chargeMaxSound":null,"chargeMaxSoundPlayer":null,"chargeHudReveal":false,"chargeRumble":null,"stowTag":null,"stowOffsetModel":null,"maxTargetAngle":0,"spaceshipSecondaryWeapon":false,"impulseFieldRadius":0,"impulseFieldInitialSpeed":0,"impulseFieldMaxSpeed":0,"impulseFieldAcceleration":0,"impulseFieldInAirImpulseMultiplier":0,"impulseFieldInAirImpulseMultiplierInterpTime":0,"impulseFieldSlideMultiplier":0,"impulseFieldSlideMultiplierInterpTime":0,"impulseFieldIsPush":false,"impulseFieldAffectsFriendlies":false,"impulseFieldAffectsSelf":false,"impulseFieldAffectsProne":false,"regenerationEnabled":false,"regenerationTimeMs":0,"regenerationAddTimeMs":0,"regenerationAmount":0,"regenerationConsumeStock":false,"regenerationDisableWhileFiring":false,"deployRequireOnWalkableSurface":false,"deployRequireOnNavmesh":false,"deployRequireSkyAbove":false,"deployRequireNoOverhang":false,"deployAlwaysUpright":false,"deployEdgeSnap":false,"deployCylinderRadius":0,"deployCylinderHeight":0,"deployMaxDista)IW7AUTH"
    R"IW7AUTH(nce":0,"deployEffect":null,"deployValidGroupId":0,"deployIndoorGroupId":0,"deployInvalidGroupId":0,"deployOutOfRangeGroupId":0,"reactiveEmitterDelay":0,"grenadeDangerIconDistance":0,"unk_466_0":false,"unk_0":0,"unk_1":0,"unk_2":0,"unk_3":0,"unk_4_0":false,"unk_4_1":false,"rotationParams":{"initialPitch":0,"initialYaw":0,"initialRoll":0,"rotationPitchDir":0,"rotationPitchMin":0,"rotationPitchMax":0,"rotationYawDir":0,"rotationYawMin":0,"rotationYawMax":0,"rotationRollDir":0,"rotationRollMin":0,"rotationRollMax":0,"rotate":false},"animOverrides":[{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null}],"sfxOverrides":[{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null}],"vfxOverrides":[{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attach)IW7AUTH"
    R"IW7AUTH(ment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null},{"attachment1":null,"attachment2":null,"overrides":null,"overridesAlt":null}],"unk0":{"material":null,"unk_18":0,"unk_19":0,"unk_20":0,"unk_21":0,"unk_22":0,"unk_23":0,"unk_24":0,"unk_25":0,"unk_26":0,"unk_27":0,"unk_28":0,"unk_29":0,"unk_30":0,"unk_31":0,"unk_32":0,"unk_33":0,"unk_34":0,"unk_35":0,"unk_36":0,"unk_37":0,"unk_38":0,"unk_39":0,"unk_40":0,"unk_41":0,"unk_42":0,"unk_43":0,"unk_44":0,"unk_45":0,"unk_46":0,"unk_47":0,"unk_48":0,"unk_49":0,"unk_50":0,"unk_51":0,"unk_52":0,"unk_53":0,"unk_54":0,"unk_55":0,"unk_56":0,"unk_57":0,"unk_58":0,"unk_59":0,"unk_60":0,"unk_61":0,"unk_62":0,"unk_63":0,"unk_64":0,"unk_65_0":false,"unk_65_1":false,"unk_65_2":false,"unk_65_3":false}}})IW7AUTH",
    R"IW7AUTH({"szInternalName":"sdk_shredder_clone_pap_zm","szDisplayName":"abcde","papAttachment":true,"type":0,"weaponType":0,"weaponClass":0,"worldModelCamo":null,"viewModelCamo":null,"worldModelVariations":null,"viewModelVariations":null,"worldModelCamoMaterials":null,"viewModelCamoMaterials":null,"attachPoint":"authored_atag01","reticles":["authored_rt0001"],"altReticles":null,"ammogeneral":null,"tracer":null,"penetration":null,"sight":null,"holdBreath":null,"reload":null,"addOns":null,"laser":null,"general":null,"aimAssist":null,"targetAssist":null,"unkAtt01":null,"ammunition":null,"damage":null,"idleSettings":null,"adsSettings":null,"adsSettingsMain":null,"scopeDriftSettings":null,"scopeDriftSettingsMain":null,"hipSpread":null,"slideSpread":null,"gunKick":null,"viewKick":null,"adsOverlay":null,"outline":null,"ui":null,"rumbles":null,"projectile":null,"charged":null,"adsAltSwitch":null,"regeneration":null,"movement":null,"burst":null,"locationDamage":null,"ammunitionScale":0,"damageScale":0,"stateTimersScale":0,"reloadTimersScale":0,"fireTimeOverride":0,"fireTimeAkimboOverride":0,"fireTimersScale":0,"burstFireCooldownScale":0,"idleHipMotionScale":0,"idleADSMotionScale":0,"idleADSMotionTimeScale":0,"adsSettingsScale":0,"adsSettingsScaleMain":0,"hipSpreadScale":0,"slideSpreadScale":0,"gunKickScale":0,"viewKickScale":0,"viewCenterScale":0,"adsSwayScale":0,"adsSwayScale2":0,"adsSwayScale3":0,"iAmmoIndex":0,"loadIndex":0,"useAlternateViewModelLaser":false,"hideIronSightsWithThisAttachment":false,"shareAmmoWithAlt":false,"useLeftTriggerAltFire":false,"containsIKTag":false,"isAkimboAttachment":false,"attachLeftWeaponAkimbo":false,"attachRightWeaponAkimbo":false,"luiWeaponInfoWidgetUsesScopeStencil":false,"szAltModeName":null,"szLUIWeaponInfoWidgetName":null,"szLUIWeaponInfoWidgetTag":null})IW7AUTH",
    R"IW7AUTH(weapon,sdk_shredder_clone_zm
attachment,sdk_shredder_clone_pap_zm
)IW7AUTH",
}};

struct Data {
    std::array<std::string,4> raw, hashes;
    input::Inputs incoming;
    input::Pins pins;
    Data() { for (std::size_t i=0;i<4;++i) raw[i]=original_raw[i]; bind(); }
    void bind() {
        for (std::size_t i=0;i<4;++i) {
            hashes[i]=input::detail::sha256(raw[i]);
            incoming[i]=raw[i]; pins[i]={raw[i].size(),hashes[i]};
        }
    }
    void rebind_report(bool mismatched=false) {
        auto report=Json::parse(raw[0]);
        report["files"][0]["bytes"]=raw[1].size();
        report["files"][0]["sha256"]=mismatched?std::string(64,'0'):input::detail::sha256(raw[1]);
        raw[0]=report.dump();bind();
    }
    std::unique_ptr<input::OwnedInput> own() const {
        input::Counters counters;
        auto result=std::make_unique<input::OwnedInput>(incoming,pins,counters);
        check(counters.copies==4&&counters.hashes==4);return result;
    }
};
struct Observation {
    std::array<unsigned,12> order{};
    std::size_t used=0, first_route_attempt=0, first_route_size=0;
    unsigned calls=0, guard_destroys=0;
    bool guard_live=false, raw_before_guard=false, component_views_live=true, cleanup_failed=false;
    const input::OwnedInput* expected_raw=nullptr;
    const void* expected_guard=nullptr;
    const void* expected_arena=nullptr;
    const Primary* primary = nullptr; // Non-owning witness across the bare rethrow.
    void record(unsigned id) noexcept { if(used<order.size())order[used++]=id;else component_views_live=false; }
};
static void record_raw_delete() noexcept {
    if(allocation_fault::observer)allocation_fault::observer->record(1);
}
struct Guard {
    Observation& report;
    explicit Guard(Observation& r):report(r){report.guard_live=true;report.expected_guard=this;}
    ~Guard() noexcept {
        report.raw_before_guard=!allocation_fault::raw_address||allocation_fault::raw_deletes==1;
        report.guard_live=false;++report.guard_destroys;report.record(0);
    }
};
template<unsigned Id> struct Node {
    Observation& report;
    const input::OwnedInput& raw;
    Node(Observation& r,const input::OwnedInput& input):report(r),raw(input){}
    ~Node() noexcept {
        if(allocation_fault::raw_deletes==0)report.component_views_live&=!raw.bytes(input::Role::weapon).empty();
        else report.component_views_live=false;
        if constexpr(Id==2){if(cleanup_failure)report.cleanup_failed=true;}
        report.record(Id);
    }
    bool cleanup_failure=false; // Authored cleanup diagnostic only, no OS result.
};
struct Primary : std::exception { const char* what() const noexcept override{return "authored component primary";} };
static void raise_primary(Observation& report) {
    try{throw Primary();}catch(const Primary& error){report.primary=&error;throw;}
}
struct Components {
    using Route=Node<2>;using Arena=Node<3>;using WeaponMap=Node<4>;using AttachmentMap=Node<5>;
    struct Weapon{};struct Attachment{};struct Inventory{};
    Observation& report;
    unsigned fail_at=0, null_at=0;
    bool failed_cleanup=false, fail_wrapper_allocation=false;
    explicit Components(Observation& r):report(r){}
    void enter(unsigned id,const input::OwnedInput& raw) {
        ++report.calls;check(&raw==report.expected_raw&&report.guard_live);
        if(fail_at==id)raise_primary(report);
    }
    std::unique_ptr<Route> route(const input::OwnedInput& raw) {
        report.first_route_attempt=allocation_fault::attempts;report.first_route_size=allocation_fault::last_size;
        enter(2,raw);if(null_at==2)return {};
        auto value=std::make_unique<Route>(report,raw);value->cleanup_failure=failed_cleanup;return value;
    }
    std::unique_ptr<Arena> arena(const input::OwnedInput& raw) {
        enter(3,raw);if(null_at==3)return {};
        auto value=std::make_unique<Arena>(report,raw);report.expected_arena=value.get();return value;
    }
    std::unique_ptr<WeaponMap> weapon_map(const input::OwnedInput& raw,Arena& arena) {
        enter(4,raw);check(&arena==report.expected_arena);if(null_at==4)return {};
        return std::make_unique<WeaponMap>(report,raw);
    }
    std::unique_ptr<AttachmentMap> attachment_map(const input::OwnedInput& raw,Arena& arena) {
        enter(5,raw);check(&arena==report.expected_arena);if(null_at==5)return {};
        auto value=std::make_unique<AttachmentMap>(report,raw);
        if(fail_wrapper_allocation){allocation_fault::remaining=0;allocation_fault::armed=true;}
        return value;
    }
};
using Ingress=owned::OwnedIngress<Guard>;
using Session=owned::TypedOwnedPair<Guard,Components>;
using LegacyPair=owned::detail::Pair<Guard,Components>;
static void watch(Observation& report,void* raw=nullptr,std::unique_ptr<Guard>* caller=nullptr) {
    allocation_fault::raw_address=raw;allocation_fault::raw_deletes=0;
    allocation_fault::observer=&report;allocation_fault::caller_guard=caller;
    allocation_fault::watch_raw=caller!=nullptr;allocation_fault::moved_before_raw=false;
    allocation_fault::primary=nullptr;allocation_fault::armed=false;
}
static void unwatch() noexcept {
    allocation_fault::observer=nullptr;allocation_fault::caller_guard=nullptr;
    allocation_fault::watch_raw=false;allocation_fault::raw_address=nullptr;allocation_fault::armed=false;
}
static std::unique_ptr<Ingress> adopt(Data& data,Observation& report) {
    auto raw=data.own();auto guard=std::make_unique<Guard>(report);
    report.expected_raw=raw.get();watch(report,raw.get());
    auto ingress=owned::adopt_owned(std::move(guard),std::move(raw));
    check(!guard&&!raw&&&ingress->input()==report.expected_raw);return ingress;
}
static void closed(const Observation& report) {
    check(!report.guard_live&&report.guard_destroys==1&&report.raw_before_guard&&
        report.component_views_live&&allocation_fault::raw_deletes==1);
}
static void copy_ingress_guarded_construction() {
    Data data;Observation report;input::Counters counters;auto guard=std::make_unique<Guard>(report);
    const auto* original_guard=guard.get();watch(report,nullptr,&guard);
    auto ingress=owned::copy_with_guards(std::move(guard),data.incoming,data.pins,counters);
    check(!guard&&report.expected_guard==original_guard&&allocation_fault::moved_before_raw&&
        counters.copies==4&&counters.hashes==4&&&ingress->input()==allocation_fault::raw_address);
    check(ingress->input().bytes(input::Role::weapon)==data.raw[1]);
    ingress.reset();closed(report);check(report.used==2&&report.order[0]==1&&report.order[1]==0);unwatch();
}
static void adopt_same_objects_no_history() {
    Data data;Observation report;
    // Deliberately construct raw BEFORE guards: adopt must not invent coverage.
    auto raw=data.own();const auto* original_raw_owner=raw.get();
    check(!report.guard_live);auto guard=std::make_unique<Guard>(report);const auto* original_guard=guard.get();
    watch(report,raw.get());auto ingress=owned::adopt_owned(std::move(guard),std::move(raw));
    check(!raw&&!guard&&&ingress->input()==original_raw_owner&&report.expected_guard==original_guard);
    ingress.reset();closed(report);unwatch();
}
static void real_preflight_before_components() {
    for(unsigned kind=0;kind<2;++kind){
        Data data;data.raw[1]="malformed-before-components";data.rebind_report(kind==0);
        Observation report;auto ingress=adopt(data,report);Components components(report);bool refused=false;
        try{auto pair=owned::make_validated_owned_pair(std::move(ingress),components);(void)pair;}
        catch(const player_pair_report::ReportError& e){check(kind==0&&std::string_view(e.what())=="Report row does not bind SAME owned role");refused=true;}
        catch(const bodies::detail::BodyError& e){check(kind==1&&std::string_view(e.what()).find("weapon:")==0);refused=true;}
        check(refused&&!ingress&&report.calls==0);closed(report);unwatch();
    }
}
static void null_and_consumed_ingress_refuse() {
    Data data;
    {Observation report;input::Counters counters;std::unique_ptr<Guard> guard;watch(report);bool refused=false;
        try{auto value=owned::copy_with_guards(std::move(guard),data.incoming,data.pins,counters);(void)value;}
        catch(const std::logic_error&){refused=true;}
        check(refused&&counters.copies==0&&counters.hashes==0&&report.guard_destroys==0);unwatch();}
    for(bool missing_raw:{false,true}){
        Observation report;auto raw=missing_raw?std::unique_ptr<input::OwnedInput>{}:data.own();
        auto guard=missing_raw?std::make_unique<Guard>(report):std::unique_ptr<Guard>{};watch(report,raw.get());bool refused=false;
        try{auto value=owned::adopt_owned(std::move(guard),std::move(raw));(void)value;}
        catch(const std::logic_error&){refused=true;}
        check(refused&&!raw&&!guard&&report.guard_destroys==(missing_raw?1u:0u));
        check(allocation_fault::raw_deletes==(missing_raw?0u:1u));unwatch();
    }
    {Observation report;auto ingress=adopt(data,report);Components components(report);
        auto pair=owned::make_validated_owned_pair(std::move(ingress),components);check(!ingress);bool refused=false;
        try{auto second=owned::make_validated_owned_pair(std::move(ingress),components);(void)second;}
        catch(const std::logic_error&){refused=true;}
        check(refused&&report.calls==4&&pair->input().bytes(input::Role::weapon)==data.raw[1]);
        pair.reset();closed(report);unwatch();}
}
static void partial_components_reverse_unwind() {
    Data data;
    for(unsigned at=2;at<=5;++at)for(bool return_null:{false,true}){
        Observation report;auto ingress=adopt(data,report);Components components(report);
        components.fail_at=return_null?0:at;components.null_at=return_null?at:0;bool refused=false;
        try{auto pair=owned::make_validated_owned_pair(std::move(ingress),components);(void)pair;}
        catch(const Primary& error){check(!return_null && &error==report.primary);report.primary=nullptr;refused=true;}
        catch(const std::logic_error&){check(return_null);refused=true;}
        check(refused&&!ingress&&report.calls==at-1);closed(report);
        std::size_t index=0;for(unsigned id=at-1;id>=2;--id)check(report.order[index++]==id);
        check(report.order[index++]==1&&report.order[index++]==0&&index==report.used);unwatch();
    }
}
static void stable_pair_view_and_builder_lifetime() {
    static_assert(!std::is_constructible_v<owned::detail::Transfer<Guard,Components>,
        std::unique_ptr<Ingress>&&,Components&>); // External code cannot split guards/raw.
    static_assert(!std::is_copy_constructible_v<Ingress>&&!std::is_move_constructible_v<Ingress>);
    static_assert(!std::is_copy_constructible_v<Session>&&!std::is_move_constructible_v<Session>);
    static_assert(std::is_same_v<decltype(std::declval<const Session&>().input()),const input::OwnedInput&>);
    static_assert(noexcept(std::declval<owned::detail::Transfer<Guard,Components>&>().guards()));
    static_assert(noexcept(std::declval<owned::detail::Transfer<Guard,Components>&>().raw()));
    Data data;Observation report;auto ingress=adopt(data,report);std::unique_ptr<Session> pair;
    {Components components(report);pair=owned::make_validated_owned_pair(std::move(ingress),components);}
    for(auto& value:data.raw)value="caller storage replaced";
    check(&pair->input()==report.expected_raw&&pair->input().bytes(input::Role::weapon)==original_raw[1]);
    check(report.calls==4&&report.used==0&&report.guard_live);pair.reset();closed(report);
    const unsigned expected[]{5,4,3,2,1,0};check(report.used==6);
    for(std::size_t i=0;i<6;++i)check(report.order[i]==expected[i]);unwatch();
}
static void standard_allocation_frontiers() {
    Data data;
    // Fail initial ingress storage, then Raw storage, then a partial owned copy.
    for(std::size_t budget:{std::size_t(0),std::size_t(1),std::size_t(4)}){
        Observation report;input::Counters counters;auto guard=std::make_unique<Guard>(report);
        auto* original=guard.get();watch(report,nullptr,&guard);const auto live=allocation_fault::live;bool refused=false;
        allocation_fault::remaining=budget;allocation_fault::armed=true;
        try{auto value=owned::copy_with_guards(std::move(guard),data.incoming,data.pins,counters);(void)value;}
        catch(const allocation_fault::Failure& error){allocation_fault::armed=false;check(&error==allocation_fault::primary);allocation_fault::primary=nullptr;refused=true;}
        allocation_fault::armed=false;check(refused&&counters.hashes==0);
        if(budget==0){check(guard.get()==original&&report.guard_destroys==0&&allocation_fault::live==live);guard.reset();}
        else{check(!guard&&report.guard_destroys==1&&report.raw_before_guard&&allocation_fault::live+1==live);}
        if(budget==4)check(counters.copies==1);unwatch();
    }
    // Observe the REAL successful prefix first. Immediately before route(), the
    // last allocation is Pair storage: only two noexcept pointer moves intervene.
    // This is not a claim that an earlier JSON/hash allocation reached Pair.
    std::size_t pair_attempt=0;
    {Observation report;auto ingress=adopt(data,report);Components components(report);allocation_fault::attempts=0;
        auto pair=owned::make_validated_owned_pair(std::move(ingress),components);
        pair_attempt=report.first_route_attempt;check(pair_attempt>0&&report.first_route_size==sizeof(LegacyPair));
        pair.reset();closed(report);unwatch();}
    {Observation report;auto ingress=adopt(data,report);Components components(report);bool refused=false;
        allocation_fault::attempts=0;allocation_fault::remaining=pair_attempt-1;allocation_fault::armed=true;
        try{auto pair=owned::make_validated_owned_pair(std::move(ingress),components);(void)pair;}
        catch(const allocation_fault::Failure& error){allocation_fault::armed=false;check(&error==allocation_fault::primary);allocation_fault::primary=nullptr;refused=true;}
        allocation_fault::armed=false;check(refused&&allocation_fault::attempts==pair_attempt&&
            allocation_fault::last_size==sizeof(LegacyPair)&&report.calls==0&&!ingress);closed(report);unwatch();}
    // Arm only AFTER attachment map construction, immediately before the wrapper
    // allocation. The completed Pair must unwind if publication storage fails.
    {Observation report;auto ingress=adopt(data,report);Components components(report);components.fail_wrapper_allocation=true;bool refused=false;
        try{auto pair=owned::make_validated_owned_pair(std::move(ingress),components);(void)pair;}
        catch(const allocation_fault::Failure& error){allocation_fault::armed=false;check(&error==allocation_fault::primary);allocation_fault::primary=nullptr;refused=true;}
        allocation_fault::armed=false;check(refused&&report.calls==4);closed(report);unwatch();}
    // Adopt's storage allocation failure leaves BOTH existing caller variables.
    {Observation report;auto raw=data.own();auto guard=std::make_unique<Guard>(report);auto* original_raw_owner=raw.get();auto* original_guard=guard.get();
        watch(report,raw.get());allocation_fault::remaining=0;allocation_fault::armed=true;bool refused=false;
        try{auto value=owned::adopt_owned(std::move(guard),std::move(raw));(void)value;}
        catch(const allocation_fault::Failure&){allocation_fault::armed=false;allocation_fault::primary=nullptr;refused=true;}
        allocation_fault::armed=false;check(refused&&raw.get()==original_raw_owner&&guard.get()==original_guard);
        raw.reset();guard.reset();closed(report);unwatch();}
}
static void primary_and_cleanup_kept_distinct() {
    Data data;Observation report;auto ingress=adopt(data,report);Components components(report);
    components.fail_at=5;components.failed_cleanup=true;bool refused=false;
    try{auto pair=owned::make_validated_owned_pair(std::move(ingress),components);(void)pair;}
    catch(const Primary& error){check(&error==report.primary);report.primary=nullptr;refused=true;}
    check(refused&&report.cleanup_failed&&report.calls==4);closed(report);unwatch();
    // An ordinary model guard/report is no native admission or cleanup success.
    bool still_inactive=false;try{player_pair_session::reject_native_activation();}
    catch(const std::logic_error&){still_inactive=true;}check(still_inactive);
}
int main() {
    const struct {const char* name;void(*run)();} groups[]{
        {"copy_ingress_guarded_construction",copy_ingress_guarded_construction},
        {"adopt_same_objects_no_history",adopt_same_objects_no_history},
        {"real_preflight_before_components",real_preflight_before_components},
        {"null_and_consumed_ingress_refuse",null_and_consumed_ingress_refuse},
        {"partial_components_reverse_unwind",partial_components_reverse_unwind},
        {"stable_pair_view_and_builder_lifetime",stable_pair_view_and_builder_lifetime},
        {"standard_allocation_frontiers",standard_allocation_frontiers},
        {"primary_and_cleanup_kept_distinct",primary_and_cleanup_kept_distinct}};
    try{for(const auto& group:groups){group.run();std::cout<<"PASS "<<group.name<<'\n';}
        std::cout<<"IW7_TYPED_OWNED_PAIR=8\n";return 0;}
    catch(const std::exception& error){allocation_fault::armed=false;std::cerr<<error.what()<<'\n';return 2;}
}
