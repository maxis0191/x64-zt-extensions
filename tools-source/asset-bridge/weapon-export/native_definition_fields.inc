#pragma once
// Generated finite readset for native fab935; see generate_definition_readset.py.
// Macro fields and manually reviewed nested/loop readsets together precede serializer entry.
namespace player_definition_readset
{
    inline bool validate(Reader& r, const AnimOverride* asset);
    inline bool validate(Reader& r, const SFXOverride* asset);
    inline bool validate(Reader& r, const VFXOverride* asset);
    inline bool validate(Reader& r, const GrenadeRotationParams* asset);
    inline bool validate(Reader& r, const ADSOverlay* asset);
    inline bool validate(Reader& r, const WeaponDef* asset, const WeaponCompleteDef* parent);
    inline bool validate(Reader& r, const NoteTrackToSoundEntry* asset);
    inline bool validate(Reader& r, const NoteTrackToSuitSoundEntry* asset);
    inline bool validate(Reader& r, const WeaponCompleteDef* asset);
    inline bool validate(Reader& r, const AttAmmoGeneral* asset);
    inline bool validate(Reader& r, const AttAmmoTracer* asset);
    inline bool validate(Reader& r, const AttPenetration* asset);
    inline bool validate(Reader& r, const AttSight* asset);
    inline bool validate(Reader& r, const AttHoldBreath* asset);
    inline bool validate(Reader& r, const AttReload* asset);
    inline bool validate(Reader& r, const AttAddOns* asset);
    inline bool validate(Reader& r, const AttGeneral* asset);
    inline bool validate(Reader& r, const AttLaser* asset);
    inline bool validate(Reader& r, const AttAimAssist* asset);
    inline bool validate(Reader& r, const AttTargetAssist* asset);
    inline bool validate(Reader& r, const AttUnknown01* asset);
    inline bool validate(Reader& r, const AttAmmunition* asset);
    inline bool validate(Reader& r, const AttDamage* asset);
    inline bool validate(Reader& r, const AttIdleSettings* asset);
    inline bool validate(Reader& r, const AttADSSettings* asset);
    inline bool validate(Reader& r, const AttScopeDriftSettings* asset);
    inline bool validate(Reader& r, const AttHipSpread* asset);
    inline bool validate(Reader& r, const AttSlideSpread* asset);
    inline bool validate(Reader& r, const AttGunKick* asset);
    inline bool validate(Reader& r, const AttViewKick* asset);
    inline bool validate(Reader& r, const AttADSOverlay* asset);
    inline bool validate(Reader& r, const AttOutline* asset);
    inline bool validate(Reader& r, const AttUI* asset);
    inline bool validate(Reader& r, const AttRumbles* asset);
    inline bool validate(Reader& r, const AttProjectile* asset);
    inline bool validate(Reader& r, const AttCharged* asset);
    inline bool validate(Reader& r, const AdsAltSwitch* asset);
    inline bool validate(Reader& r, const AttRegeneration* asset);
    inline bool validate(Reader& r, const AttMovement* asset);
    inline bool validate(Reader& r, const AttBurst* asset);
    inline bool validate(Reader& r, const WeaponAttachment* asset);
    template<class T> inline bool optional(Reader& r, T* const* address, const char* field)
    {
        T* value;
        return r.json_token(4, field) && r.load(address, value, field) && (!value || validate(r, value));
    }
    // assets/weapondef.cpp: dump(AnimOverride*), 4 exact macro fields.
    inline bool validate(Reader& r, const AnimOverride* asset)
    {
        if (!r.object(asset, "AnimOverride")) return false;
        if (!r.script_field(&asset->attachment1, "AnimOverride.attachment1")) return false;
        if (!r.script_field(&asset->attachment2, "AnimOverride.attachment2")) return false;
        if (!r.asset_field(&asset->overrides, "AnimOverride.overrides")) return false;
        if (!r.asset_field(&asset->overridesAlt, "AnimOverride.overridesAlt")) return false;
        return true;
    }
    // assets/weapondef.cpp: dump(SFXOverride*), 4 exact macro fields.
    inline bool validate(Reader& r, const SFXOverride* asset)
    {
        if (!r.object(asset, "SFXOverride")) return false;
        if (!r.script_field(&asset->attachment1, "SFXOverride.attachment1")) return false;
        if (!r.script_field(&asset->attachment2, "SFXOverride.attachment2")) return false;
        if (!r.asset_field(&asset->overrides, "SFXOverride.overrides")) return false;
        if (!r.asset_field(&asset->overridesAlt, "SFXOverride.overridesAlt")) return false;
        return true;
    }
    // assets/weapondef.cpp: dump(VFXOverride*), 4 exact macro fields.
    inline bool validate(Reader& r, const VFXOverride* asset)
    {
        if (!r.object(asset, "VFXOverride")) return false;
        if (!r.script_field(&asset->attachment1, "VFXOverride.attachment1")) return false;
        if (!r.script_field(&asset->attachment2, "VFXOverride.attachment2")) return false;
        if (!r.asset_field(&asset->overrides, "VFXOverride.overrides")) return false;
        if (!r.asset_field(&asset->overridesAlt, "VFXOverride.overridesAlt")) return false;
        return true;
    }
    // assets/weapondef.cpp: dump(GrenadeRotationParams*), 13 exact macro fields.
    inline bool validate(Reader& r, const GrenadeRotationParams* asset)
    {
        if (!r.object(asset, "GrenadeRotationParams")) return false;
        if (!r.scalar(&asset->initialPitch, "GrenadeRotationParams.initialPitch")) return false;
        if (!r.scalar(&asset->initialYaw, "GrenadeRotationParams.initialYaw")) return false;
        if (!r.scalar(&asset->initialRoll, "GrenadeRotationParams.initialRoll")) return false;
        if (!r.scalar(&asset->rotationPitchDir, "GrenadeRotationParams.rotationPitchDir")) return false;
        if (!r.scalar(&asset->rotationPitchMin, "GrenadeRotationParams.rotationPitchMin")) return false;
        if (!r.scalar(&asset->rotationPitchMax, "GrenadeRotationParams.rotationPitchMax")) return false;
        if (!r.scalar(&asset->rotationYawDir, "GrenadeRotationParams.rotationYawDir")) return false;
        if (!r.scalar(&asset->rotationYawMin, "GrenadeRotationParams.rotationYawMin")) return false;
        if (!r.scalar(&asset->rotationYawMax, "GrenadeRotationParams.rotationYawMax")) return false;
        if (!r.scalar(&asset->rotationRollDir, "GrenadeRotationParams.rotationRollDir")) return false;
        if (!r.scalar(&asset->rotationRollMin, "GrenadeRotationParams.rotationRollMin")) return false;
        if (!r.scalar(&asset->rotationRollMax, "GrenadeRotationParams.rotationRollMax")) return false;
        if (!r.scalar(&asset->rotate, "GrenadeRotationParams.rotate")) return false;
        return true;
    }
    // assets/weapondef.cpp: dump(ADSOverlay*), 9 exact macro fields.
    inline bool validate(Reader& r, const ADSOverlay* asset)
    {
        if (!r.object(asset, "ADSOverlay")) return false;
        if (!r.asset_field(&asset->shader, "ADSOverlay.shader")) return false;
        if (!r.asset_field(&asset->shaderLowRes, "ADSOverlay.shaderLowRes")) return false;
        if (!r.asset_field(&asset->shaderEMP, "ADSOverlay.shaderEMP")) return false;
        if (!r.asset_field(&asset->shaderEMPLowRes, "ADSOverlay.shaderEMPLowRes")) return false;
        if (!r.scalar(&asset->reticle, "ADSOverlay.reticle")) return false;
        if (!r.scalar(&asset->width, "ADSOverlay.width")) return false;
        if (!r.scalar(&asset->height, "ADSOverlay.height")) return false;
        if (!r.scalar(&asset->widthSplitscreen, "ADSOverlay.widthSplitscreen")) return false;
        if (!r.scalar(&asset->heightSplitscreen, "ADSOverlay.heightSplitscreen")) return false;
        return true;
    }
    // assets/weapondef.cpp: dump_weapondef(WeaponDef*), 682 exact macro fields.
    inline bool validate(Reader& r, const WeaponDef* asset, const WeaponCompleteDef* parent)
    {
        if (!r.object(asset, "WeaponDef")) return false;
        if (!r.inline_objects(&asset->animOverrides, "WeaponDef.animOverrides", [&](const auto* value) { return validate(r, value); })) return false;
        if (!r.inline_objects(&asset->sfxOverrides, "WeaponDef.sfxOverrides", [&](const auto* value) { return validate(r, value); })) return false;
        if (!r.inline_objects(&asset->vfxOverrides, "WeaponDef.vfxOverrides", [&](const auto* value) { return validate(r, value); })) return false;
        if (!r.string_field(&asset->szOverlayName, "WeaponDef.szOverlayName")) return false;
        if (!r.string_field(&asset->szModeName, "WeaponDef.szModeName")) return false;
        if (!r.string_field(&asset->szAmmoName, "WeaponDef.szAmmoName")) return false;
        if (!r.string_field(&asset->szSharedAmmoCapName, "WeaponDef.szSharedAmmoCapName")) return false;
        if (!r.string_field(&asset->szUseHintString, "WeaponDef.szUseHintString")) return false;
        if (!r.string_field(&asset->dropHintString, "WeaponDef.dropHintString")) return false;
        if (!r.string_field(&asset->szScript, "WeaponDef.szScript")) return false;
        if (!r.asset_field(&asset->gunXModel, "WeaponDef.gunXModel")) return false;
        if (!r.asset_field(&asset->gunXModelLeftHand, "WeaponDef.gunXModelLeftHand")) return false;
        if (!r.asset_field(&asset->gunXModelRightHand, "WeaponDef.gunXModelRightHand")) return false;
        if (!r.asset_field(&asset->defaultViewModel, "WeaponDef.defaultViewModel")) return false;
        if (!r.asset_field(&asset->defaultWorldModelLeftHand, "WeaponDef.defaultWorldModelLeftHand")) return false;
        if (!r.asset_field(&asset->defaultWorldModelRightHand, "WeaponDef.defaultWorldModelRightHand")) return false;
        if (!r.asset_field(&asset->worldModel, "WeaponDef.worldModel")) return false;
        if (!r.asset_field(&asset->worldXModelLeftHand, "WeaponDef.worldXModelLeftHand")) return false;
        if (!r.asset_field(&asset->worldXModelRightHand, "WeaponDef.worldXModelRightHand")) return false;
        if (!r.asset_field(&asset->defaultWorldModel, "WeaponDef.defaultWorldModel")) return false;
        if (!r.asset_field(&asset->playerShadowModel, "WeaponDef.playerShadowModel")) return false;
        if (!r.asset_field(&asset->playerShadowModelLeftHand, "WeaponDef.playerShadowModelLeftHand")) return false;
        if (!r.asset_field(&asset->playerShadowModelRightHand, "WeaponDef.playerShadowModelRightHand")) return false;
        if (!r.asset_field(&asset->handXModel, "WeaponDef.handXModel")) return false;
        if (!r.counted_array(&asset->complexWorldModel, &asset->numComplexModels, "WeaponDef.complexWorldModel", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexWorldModel"); })) return false;
        if (!r.counted_array(&asset->complexWorldModelLeftHand, &asset->numComplexModels, "WeaponDef.complexWorldModelLeftHand", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexWorldModelLeftHand"); })) return false;
        if (!r.counted_array(&asset->complexWorldModelRightHand, &asset->numComplexModels, "WeaponDef.complexWorldModelRightHand", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexWorldModelRightHand"); })) return false;
        if (!r.counted_array(&asset->complexGunXModel, &asset->numComplexModels, "WeaponDef.complexGunXModel", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexGunXModel"); })) return false;
        if (!r.counted_array(&asset->complexGunXModelLeftHand, &asset->numComplexModels, "WeaponDef.complexGunXModelLeftHand", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexGunXModelLeftHand"); })) return false;
        if (!r.counted_array(&asset->complexGunXModelRightHand, &asset->numComplexModels, "WeaponDef.complexGunXModelRightHand", [&](const auto* value) { return r.asset_field(value, "WeaponDef.complexGunXModelRightHand"); })) return false;
        if (!r.inline_objects(&asset->camoWorldModelMaterialOverride, "WeaponDef.camoWorldModelMaterialOverride", [&](const auto* value) { return r.asset_field(value, "WeaponDef.camoWorldModelMaterialOverride"); })) return false;
        if (!r.inline_objects(&asset->camoViewModelMaterialOverride, "WeaponDef.camoViewModelMaterialOverride", [&](const auto* value) { return r.asset_field(value, "WeaponDef.camoViewModelMaterialOverride"); })) return false;
        if (!r.asset_field(&asset->szXAnims, "WeaponDef.szXAnims")) return false;
        if (!r.asset_field(&asset->szXAnimsRightHanded, "WeaponDef.szXAnimsRightHanded")) return false;
        if (!r.asset_field(&asset->szXAnimsLeftHanded, "WeaponDef.szXAnimsLeftHanded")) return false;
        if (!r.pointer_array(&asset->notetrackRumbleMapKeys, 16, "WeaponDef.notetrackRumbleMapKeys", [&](const auto* value) { return r.script_field(value, "WeaponDef.notetrackRumbleMapKeys"); })) return false;
        if (!r.pointer_array(&asset->notetrackRumbleMapValues, 16, "WeaponDef.notetrackRumbleMapValues", [&](const auto* value) { return r.script_field(value, "WeaponDef.notetrackRumbleMapValues"); })) return false;
        if (!r.pointer_array(&asset->notetrackFXMapKeys, 16, "WeaponDef.notetrackFXMapKeys", [&](const auto* value) { return r.script_field(value, "WeaponDef.notetrackFXMapKeys"); })) return false;
        if (!r.pointer_array(&asset->notetrackFXMapValues, 16, "WeaponDef.notetrackFXMapValues", [&](const auto* value) { return r.fx(*value, "WeaponDef.notetrackFXMapValues"); })) return false;
        if (!r.pointer_array(&asset->notetrackFXMapTagValues, 16, "WeaponDef.notetrackFXMapTagValues", [&](const auto* value) { return r.script_field(value, "WeaponDef.notetrackFXMapTagValues"); })) return false;
        if (!r.scalar(&asset->playerAnimType, "WeaponDef.playerAnimType")) return false;
        if (!r.scalar(&asset->scriptedAnimEvent, "WeaponDef.scriptedAnimEvent")) return false;
        if (!r.scalar(&asset->scriptedAnimType, "WeaponDef.scriptedAnimType")) return false;
        if (!r.scalar(&asset->weapType, "WeaponDef.weapType")) return false;
        if (!r.scalar(&asset->whizbyType, "WeaponDef.whizbyType")) return false;
        if (!r.scalar(&asset->weapClass, "WeaponDef.weapClass")) return false;
        if (!r.scalar(&asset->penetrateType, "WeaponDef.penetrateType")) return false;
        if (!r.scalar(&asset->deathAnimDamageType, "WeaponDef.deathAnimDamageType")) return false;
        if (!r.scalar(&asset->inventoryType, "WeaponDef.inventoryType")) return false;
        if (!r.scalar(&asset->fireType, "WeaponDef.fireType")) return false;
        if (!r.scalar(&asset->targetAssistType, "WeaponDef.targetAssistType")) return false;
        if (!r.scalar(&asset->targetAssistBehavior, "WeaponDef.targetAssistBehavior")) return false;
        if (!r.scalar(&asset->targetAssistRange, "WeaponDef.targetAssistRange")) return false;
        if (!r.scalar(&asset->targetAssistAngle, "WeaponDef.targetAssistAngle")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetForward, "WeaponDef.targetAssistLosOffsetForward")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetRight, "WeaponDef.targetAssistLosOffsetRight")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetUp, "WeaponDef.targetAssistLosOffsetUp")) return false;
        if (!r.scalar(&asset->targetAssistOnlyAvailableInAds, "WeaponDef.targetAssistOnlyAvailableInAds")) return false;
        if (!r.scalar(&asset->offhandClass, "WeaponDef.offhandClass")) return false;
        if (!r.scalar(&asset->stance, "WeaponDef.stance")) return false;
        if (!r.scalar(&asset->stickiness, "WeaponDef.stickiness")) return false;
        if (!r.scalar(&asset->dualWieldType, "WeaponDef.dualWieldType")) return false;
        if (!r.scalar(&asset->slot, "WeaponDef.slot")) return false;
        if (!r.scalar(&asset->iFireTime, "WeaponDef.iFireTime")) return false;
        if (!r.scalar(&asset->iFireDelay, "WeaponDef.iFireDelay")) return false;
        if (!r.scalar(&asset->iFireTimeAkimbo, "WeaponDef.iFireTimeAkimbo")) return false;
        if (!r.scalar(&asset->iFireDelayAkimbo, "WeaponDef.iFireDelayAkimbo")) return false;
        if (!r.scalar(&asset->bSegmentedReload, "WeaponDef.bSegmentedReload")) return false;
        if (!r.scalar(&asset->burstFireCooldown, "WeaponDef.burstFireCooldown")) return false;
        if (!r.scalar(&asset->burstFireAuto, "WeaponDef.burstFireAuto")) return false;
        if (!r.asset_field(&asset->vfxPackage, "WeaponDef.vfxPackage")) return false;
        if (!r.asset_field(&asset->sfxPackage, "WeaponDef.sfxPackage")) return false;
        if (!r.scalar(&asset->reticleType, "WeaponDef.reticleType")) return false;
        if (!r.asset_field(&asset->reticleCenter, "WeaponDef.reticleCenter")) return false;
        if (!r.asset_field(&asset->reticleSide, "WeaponDef.reticleSide")) return false;
        if (!r.asset_field(&asset->reticleOnePiece, "WeaponDef.reticleOnePiece")) return false;
        if (!r.scalar(&asset->iReticleCenterSize, "WeaponDef.iReticleCenterSize")) return false;
        if (!r.scalar(&asset->iReticleSideSize, "WeaponDef.iReticleSideSize")) return false;
        if (!r.scalar(&asset->iReticleMinOfs, "WeaponDef.iReticleMinOfs")) return false;
        if (!r.scalar(&asset->reticleCenterPulse, "WeaponDef.reticleCenterPulse")) return false;
        if (!r.scalar(&asset->activeReticleType, "WeaponDef.activeReticleType")) return false;
        if (!r.fixed_scalars(&asset->vStandMove, 3, "WeaponDef.vStandMove")) return false;
        if (!r.fixed_scalars(&asset->vStandRot, 3, "WeaponDef.vStandRot")) return false;
        if (!r.fixed_scalars(&asset->strafeMove, 3, "WeaponDef.strafeMove")) return false;
        if (!r.fixed_scalars(&asset->strafeRot, 3, "WeaponDef.strafeRot")) return false;
        if (!r.fixed_scalars(&asset->vDuckedOfs, 3, "WeaponDef.vDuckedOfs")) return false;
        if (!r.fixed_scalars(&asset->vDuckedMove, 3, "WeaponDef.vDuckedMove")) return false;
        if (!r.fixed_scalars(&asset->vDuckedRot, 3, "WeaponDef.vDuckedRot")) return false;
        if (!r.fixed_scalars(&asset->vProneOfs, 3, "WeaponDef.vProneOfs")) return false;
        if (!r.fixed_scalars(&asset->vProneMove, 3, "WeaponDef.vProneMove")) return false;
        if (!r.fixed_scalars(&asset->vProneRot, 3, "WeaponDef.vProneRot")) return false;
        if (!r.scalar(&asset->fPosMoveRate, "WeaponDef.fPosMoveRate")) return false;
        if (!r.scalar(&asset->fPosProneMoveRate, "WeaponDef.fPosProneMoveRate")) return false;
        if (!r.scalar(&asset->fStandMoveMinSpeed, "WeaponDef.fStandMoveMinSpeed")) return false;
        if (!r.scalar(&asset->fDuckedMoveMinSpeed, "WeaponDef.fDuckedMoveMinSpeed")) return false;
        if (!r.scalar(&asset->fProneMoveMinSpeed, "WeaponDef.fProneMoveMinSpeed")) return false;
        if (!r.scalar(&asset->fPosRotRate, "WeaponDef.fPosRotRate")) return false;
        if (!r.scalar(&asset->fPosProneRotRate, "WeaponDef.fPosProneRotRate")) return false;
        if (!r.scalar(&asset->fStandRotMinSpeed, "WeaponDef.fStandRotMinSpeed")) return false;
        if (!r.scalar(&asset->fDuckedRotMinSpeed, "WeaponDef.fDuckedRotMinSpeed")) return false;
        if (!r.scalar(&asset->fProneRotMinSpeed, "WeaponDef.fProneRotMinSpeed")) return false;
        if (!r.asset_field(&asset->worldClipModel, "WeaponDef.worldClipModel")) return false;
        if (!r.asset_field(&asset->rocketModel, "WeaponDef.rocketModel")) return false;
        if (!r.asset_field(&asset->knifeModel, "WeaponDef.knifeModel")) return false;
        if (!r.asset_field(&asset->worldKnifeModel, "WeaponDef.worldKnifeModel")) return false;
        if (!r.asset_field(&asset->hudIcon, "WeaponDef.hudIcon")) return false;
        if (!r.asset_field(&asset->pickupIcon, "WeaponDef.pickupIcon")) return false;
        if (!r.asset_field(&asset->dangerIcon, "WeaponDef.dangerIcon")) return false;
        if (!r.asset_field(&asset->throwBackIcon, "WeaponDef.throwBackIcon")) return false;
        if (!r.scalar(&asset->hideWarningIcons, "WeaponDef.hideWarningIcons")) return false;
        if (!r.scalar(&asset->warningIconsDelay, "WeaponDef.warningIconsDelay")) return false;
        if (!r.asset_field(&asset->ammoCounterIcon, "WeaponDef.ammoCounterIcon")) return false;
        if (!r.scalar(&asset->ammoCounterClip, "WeaponDef.ammoCounterClip")) return false;
        if (!r.scalar(&asset->iStartAmmo, "WeaponDef.iStartAmmo")) return false;
        if (!r.scalar(&asset->iPerkStartAmmo, "WeaponDef.iPerkStartAmmo")) return false;
        if (!r.scalar(&asset->iPerkMaxAmmo, "WeaponDef.iPerkMaxAmmo")) return false;
        if (!r.scalar(&asset->iMaxAmmo, "WeaponDef.iMaxAmmo")) return false;
        if (!r.scalar(&asset->shotCount, "WeaponDef.shotCount")) return false;
        if (!r.scalar(&asset->iSharedAmmoCap, "WeaponDef.iSharedAmmoCap")) return false;
        if (!r.scalar(&asset->iAmmoUsedPerShot, "WeaponDef.iAmmoUsedPerShot")) return false;
        if (!r.scalar(&asset->requireAmmoUsedPerShot, "WeaponDef.requireAmmoUsedPerShot")) return false;
        if (!r.scalar(&asset->lowAmmoWarningThreshold, "WeaponDef.lowAmmoWarningThreshold")) return false;
        if (!r.scalar(&asset->disableNoAmmoWarning, "WeaponDef.disableNoAmmoWarning")) return false;
        if (!r.scalar(&asset->damage, "WeaponDef.damage")) return false;
        if (!r.scalar(&asset->playerDamage, "WeaponDef.playerDamage")) return false;
        if (!r.scalar(&asset->meleeDamage, "WeaponDef.meleeDamage")) return false;
        if (!r.scalar(&asset->iDamageType, "WeaponDef.iDamageType")) return false;
        if (!r.scalar(&asset->autoAimRange, "WeaponDef.autoAimRange")) return false;
        if (!r.scalar(&asset->aimAssistRange, "WeaponDef.aimAssistRange")) return false;
        if (!r.scalar(&asset->aimAssistRangeAds, "WeaponDef.aimAssistRangeAds")) return false;
        if (!r.scalar(&asset->aimAssistPitchSlowdown, "WeaponDef.aimAssistPitchSlowdown")) return false;
        if (!r.scalar(&asset->aimAssistPitchSlowdownAds, "WeaponDef.aimAssistPitchSlowdownAds")) return false;
        if (!r.scalar(&asset->aimAssistYawSlowdown, "WeaponDef.aimAssistYawSlowdown")) return false;
        if (!r.scalar(&asset->aimAssistYawSlowdownAds, "WeaponDef.aimAssistYawSlowdownAds")) return false;
        if (!r.scalar(&asset->aimAssistLockonStrength, "WeaponDef.aimAssistLockonStrength")) return false;
        if (!r.scalar(&asset->aimPadding, "WeaponDef.aimPadding")) return false;
        if (!r.scalar(&asset->enemyCrosshairRange, "WeaponDef.enemyCrosshairRange")) return false;
        if (!r.scalar(&asset->moveSpeedScale, "WeaponDef.moveSpeedScale")) return false;
        if (!r.scalar(&asset->adsMoveSpeedScale, "WeaponDef.adsMoveSpeedScale")) return false;
        if (!r.scalar(&asset->sprintDurationScale, "WeaponDef.sprintDurationScale")) return false;
        if (!r.scalar(&asset->sprintRestoreDelay, "WeaponDef.sprintRestoreDelay")) return false;
        if (!r.scalar(&asset->fAdsZoomInFrac, "WeaponDef.fAdsZoomInFrac")) return false;
        if (!r.scalar(&asset->fAdsZoomOutFrac, "WeaponDef.fAdsZoomOutFrac")) return false;
        if (!r.scalar(&asset->overlayInterface, "WeaponDef.overlayInterface")) return false;
        if (!r.scalar(&asset->fAdsBobFactor, "WeaponDef.fAdsBobFactor")) return false;
        if (!r.scalar(&asset->fAdsViewBobMult, "WeaponDef.fAdsViewBobMult")) return false;
        if (!r.scalar(&asset->fHipSpreadStandMin, "WeaponDef.fHipSpreadStandMin")) return false;
        if (!r.scalar(&asset->fHipSpreadDuckedMin, "WeaponDef.fHipSpreadDuckedMin")) return false;
        if (!r.scalar(&asset->fHipSpreadProneMin, "WeaponDef.fHipSpreadProneMin")) return false;
        if (!r.scalar(&asset->hipSpreadSprintMin, "WeaponDef.hipSpreadSprintMin")) return false;
        if (!r.scalar(&asset->hipSpreadInAirMin, "WeaponDef.hipSpreadInAirMin")) return false;
        if (!r.scalar(&asset->hipSpreadStandMax, "WeaponDef.hipSpreadStandMax")) return false;
        if (!r.scalar(&asset->hipSpreadDuckedMax, "WeaponDef.hipSpreadDuckedMax")) return false;
        if (!r.scalar(&asset->hipSpreadProneMax, "WeaponDef.hipSpreadProneMax")) return false;
        if (!r.scalar(&asset->hipSpreadSprintMax, "WeaponDef.hipSpreadSprintMax")) return false;
        if (!r.scalar(&asset->hipSpreadInAirMax, "WeaponDef.hipSpreadInAirMax")) return false;
        if (!r.scalar(&asset->fHipSpreadDecayRate, "WeaponDef.fHipSpreadDecayRate")) return false;
        if (!r.scalar(&asset->fHipSpreadFireAdd, "WeaponDef.fHipSpreadFireAdd")) return false;
        if (!r.scalar(&asset->fHipSpreadTurnAdd, "WeaponDef.fHipSpreadTurnAdd")) return false;
        if (!r.scalar(&asset->fHipSpreadMoveAdd, "WeaponDef.fHipSpreadMoveAdd")) return false;
        if (!r.scalar(&asset->fHipSpreadDuckedDecay, "WeaponDef.fHipSpreadDuckedDecay")) return false;
        if (!r.scalar(&asset->fHipSpreadProneDecay, "WeaponDef.fHipSpreadProneDecay")) return false;
        if (!r.scalar(&asset->hipSpreadSprintDecay, "WeaponDef.hipSpreadSprintDecay")) return false;
        if (!r.scalar(&asset->hipSpreadInAirDecay, "WeaponDef.hipSpreadInAirDecay")) return false;
        if (!r.scalar(&asset->fHipReticleSidePos, "WeaponDef.fHipReticleSidePos")) return false;
        if (!r.scalar(&asset->fAdsIdleAmount, "WeaponDef.fAdsIdleAmount")) return false;
        if (!r.scalar(&asset->fHipIdleAmount, "WeaponDef.fHipIdleAmount")) return false;
        if (!r.scalar(&asset->adsIdleSpeed, "WeaponDef.adsIdleSpeed")) return false;
        if (!r.scalar(&asset->hipIdleSpeed, "WeaponDef.hipIdleSpeed")) return false;
        if (!r.scalar(&asset->fIdleCrouchFactor, "WeaponDef.fIdleCrouchFactor")) return false;
        if (!r.scalar(&asset->fIdleProneFactor, "WeaponDef.fIdleProneFactor")) return false;
        if (!r.scalar(&asset->fGunMaxPitch, "WeaponDef.fGunMaxPitch")) return false;
        if (!r.scalar(&asset->fGunMaxYaw, "WeaponDef.fGunMaxYaw")) return false;
        if (!r.scalar(&asset->adsIdleLerpStartTime, "WeaponDef.adsIdleLerpStartTime")) return false;
        if (!r.scalar(&asset->adsIdleLerpTime, "WeaponDef.adsIdleLerpTime")) return false;
        if (!r.scalar(&asset->slideSpreadMin, "WeaponDef.slideSpreadMin")) return false;
        if (!r.scalar(&asset->slideSpreadMax, "WeaponDef.slideSpreadMax")) return false;
        if (!r.scalar(&asset->slideSpreadDecayRate, "WeaponDef.slideSpreadDecayRate")) return false;
        if (!r.scalar(&asset->slideSpreadFireAdd, "WeaponDef.slideSpreadFireAdd")) return false;
        if (!r.scalar(&asset->slideSpreadTurnAdd, "WeaponDef.slideSpreadTurnAdd")) return false;
        if (!r.scalar(&asset->swayMaxAngleSteadyAim, "WeaponDef.swayMaxAngleSteadyAim")) return false;
        if (!r.scalar(&asset->swayMaxAngle, "WeaponDef.swayMaxAngle")) return false;
        if (!r.scalar(&asset->swayLerpSpeed, "WeaponDef.swayLerpSpeed")) return false;
        if (!r.scalar(&asset->swayPitchScale, "WeaponDef.swayPitchScale")) return false;
        if (!r.scalar(&asset->swayYawScale, "WeaponDef.swayYawScale")) return false;
        if (!r.scalar(&asset->swayHorizScale, "WeaponDef.swayHorizScale")) return false;
        if (!r.scalar(&asset->swayVertScale, "WeaponDef.swayVertScale")) return false;
        if (!r.scalar(&asset->swayShellShockScale, "WeaponDef.swayShellShockScale")) return false;
        if (!r.scalar(&asset->adsSwayMaxAngle, "WeaponDef.adsSwayMaxAngle")) return false;
        if (!r.scalar(&asset->adsSwayLerpSpeed, "WeaponDef.adsSwayLerpSpeed")) return false;
        if (!r.scalar(&asset->adsSway_UNKNOWN_Scale, "WeaponDef.adsSway_UNKNOWN_Scale")) return false;
        if (!r.scalar(&asset->adsSwayPitchScale, "WeaponDef.adsSwayPitchScale")) return false;
        if (!r.scalar(&asset->adsSwayYawScale, "WeaponDef.adsSwayYawScale")) return false;
        if (!r.scalar(&asset->adsSwayHorizScale, "WeaponDef.adsSwayHorizScale")) return false;
        if (!r.scalar(&asset->adsSwayVertScale, "WeaponDef.adsSwayVertScale")) return false;
        if (!r.scalar(&asset->adsFireRateScale, "WeaponDef.adsFireRateScale")) return false;
        if (!r.scalar(&asset->adsDamageRangeScale, "WeaponDef.adsDamageRangeScale")) return false;
        if (!r.scalar(&asset->adsFireAnimFrac, "WeaponDef.adsFireAnimFrac")) return false;
        if (!r.scalar(&asset->fireTimerLerpToAdsScale, "WeaponDef.fireTimerLerpToAdsScale")) return false;
        if (!r.scalar(&asset->alwaysFireAtMaxRangeInAds, "WeaponDef.alwaysFireAtMaxRangeInAds")) return false;
        if (!r.scalar(&asset->dualWieldViewModelOffset, "WeaponDef.dualWieldViewModelOffset")) return false;
        if (!r.scalar(&asset->fScopeDriftDelay, "WeaponDef.fScopeDriftDelay")) return false;
        if (!r.scalar(&asset->fScopeDriftLerpInTime, "WeaponDef.fScopeDriftLerpInTime")) return false;
        if (!r.scalar(&asset->fScopeDriftSteadyTime, "WeaponDef.fScopeDriftSteadyTime")) return false;
        if (!r.scalar(&asset->fScopeDriftLerpOutTime, "WeaponDef.fScopeDriftLerpOutTime")) return false;
        if (!r.scalar(&asset->fScopeDriftSteadyFactor, "WeaponDef.fScopeDriftSteadyFactor")) return false;
        if (!r.scalar(&asset->fScopeDriftUnsteadyFactor, "WeaponDef.fScopeDriftUnsteadyFactor")) return false;
        if (!r.scalar(&asset->killIconRatio, "WeaponDef.killIconRatio")) return false;
        if (!r.scalar(&asset->iReloadAmmoAdd, "WeaponDef.iReloadAmmoAdd")) return false;
        if (!r.scalar(&asset->iReloadStartAdd, "WeaponDef.iReloadStartAdd")) return false;
        if (!r.scalar(&asset->ammoDropStockMin, "WeaponDef.ammoDropStockMin")) return false;
        if (!r.scalar(&asset->ammoDropClipPercentMin, "WeaponDef.ammoDropClipPercentMin")) return false;
        if (!r.scalar(&asset->ammoDropClipPercentMax, "WeaponDef.ammoDropClipPercentMax")) return false;
        if (!r.scalar(&asset->iExplosionRadius, "WeaponDef.iExplosionRadius")) return false;
        if (!r.scalar(&asset->iExplosionRadiusMin, "WeaponDef.iExplosionRadiusMin")) return false;
        if (!r.scalar(&asset->iExplosionForceRadius, "WeaponDef.iExplosionForceRadius")) return false;
        if (!r.scalar(&asset->iExplosionInnerDamage, "WeaponDef.iExplosionInnerDamage")) return false;
        if (!r.scalar(&asset->iExplosionOuterDamage, "WeaponDef.iExplosionOuterDamage")) return false;
        if (!r.scalar(&asset->damageConeAngle, "WeaponDef.damageConeAngle")) return false;
        if (!r.scalar(&asset->bulletExplDmgMult, "WeaponDef.bulletExplDmgMult")) return false;
        if (!r.scalar(&asset->bulletExplRadiusMult, "WeaponDef.bulletExplRadiusMult")) return false;
        if (!r.scalar(&asset->iProjectileSpeed, "WeaponDef.iProjectileSpeed")) return false;
        if (!r.scalar(&asset->iProjectileSpeedUp, "WeaponDef.iProjectileSpeedUp")) return false;
        if (!r.scalar(&asset->iProjectileSpeedForward, "WeaponDef.iProjectileSpeedForward")) return false;
        if (!r.scalar(&asset->iProjectileActivateDist, "WeaponDef.iProjectileActivateDist")) return false;
        if (!r.scalar(&asset->iProjectileDetonationRadius, "WeaponDef.iProjectileDetonationRadius")) return false;
        if (!r.scalar(&asset->projLifetime, "WeaponDef.projLifetime")) return false;
        if (!r.scalar(&asset->projLifetimeStdDeviation, "WeaponDef.projLifetimeStdDeviation")) return false;
        if (!r.scalar(&asset->timeToAccelerate, "WeaponDef.timeToAccelerate")) return false;
        if (!r.scalar(&asset->projectileCurvature, "WeaponDef.projectileCurvature")) return false;
        if (!r.asset_field(&asset->projectileModel, "WeaponDef.projectileModel")) return false;
        if (!r.fx(asset->projExplosionEffect, "WeaponDef.projExplosionEffect")) return false;
        if (!r.fx(asset->projDudEffect, "WeaponDef.projDudEffect")) return false;
        if (!r.fx(asset->projBodyEffect, "WeaponDef.projBodyEffect")) return false;
        if (!r.fx(asset->projTrailEffect, "WeaponDef.projTrailEffect")) return false;
        if (!r.fx(asset->projBeaconEffect, "WeaponDef.projBeaconEffect")) return false;
        if (!r.fx(asset->projIgnitionEffect, "WeaponDef.projIgnitionEffect")) return false;
        if (!r.scalar(&asset->ricochetChance, "WeaponDef.ricochetChance")) return false;
        if (!r.scalar(&asset->riotShieldEnableDamage, "WeaponDef.riotShieldEnableDamage")) return false;
        if (!r.scalar(&asset->riotShieldHealth, "WeaponDef.riotShieldHealth")) return false;
        if (!r.scalar(&asset->riotShieldDamageMult, "WeaponDef.riotShieldDamageMult")) return false;
        if (!r.fixed_scalars(&asset->vProjectileColor, 3, "WeaponDef.vProjectileColor")) return false;
        if (!r.scalar(&asset->guidedMissileType, "WeaponDef.guidedMissileType")) return false;
        if (!r.scalar(&asset->maxSteeringAccel, "WeaponDef.maxSteeringAccel")) return false;
        if (!r.scalar(&asset->projIgnitionDelay, "WeaponDef.projIgnitionDelay")) return false;
        if (!r.pointer_array(&asset->parallelBounce, 64, "WeaponDef.parallelBounce", [&](const auto* value) { return r.scalar(value, "WeaponDef.parallelBounce"); })) return false;
        if (!r.pointer_array(&asset->perpendicularBounce, 64, "WeaponDef.perpendicularBounce", [&](const auto* value) { return r.scalar(value, "WeaponDef.perpendicularBounce"); })) return false;
        if (!r.scalar(&asset->fAdsAimPitch, "WeaponDef.fAdsAimPitch")) return false;
        if (!r.scalar(&asset->fAdsCrosshairInFrac, "WeaponDef.fAdsCrosshairInFrac")) return false;
        if (!r.scalar(&asset->fAdsCrosshairOutFrac, "WeaponDef.fAdsCrosshairOutFrac")) return false;
        if (!r.scalar(&asset->adsInCrosshairAlphaStart, "WeaponDef.adsInCrosshairAlphaStart")) return false;
        if (!r.scalar(&asset->adsInCrosshairAlphaEnd, "WeaponDef.adsInCrosshairAlphaEnd")) return false;
        if (!r.scalar(&asset->adsOutCrosshairAlphaStart, "WeaponDef.adsOutCrosshairAlphaStart")) return false;
        if (!r.scalar(&asset->adsOutCrosshairAlphaEnd, "WeaponDef.adsOutCrosshairAlphaEnd")) return false;
        if (!r.scalar(&asset->adsShouldShowCrosshair, "WeaponDef.adsShouldShowCrosshair")) return false;
        if (!r.scalar(&asset->adsGunKickReducedKickBullets, "WeaponDef.adsGunKickReducedKickBullets")) return false;
        if (!r.scalar(&asset->adsGunKickReducedKickPercent, "WeaponDef.adsGunKickReducedKickPercent")) return false;
        if (!r.scalar(&asset->fAdsGunKickPitchMin, "WeaponDef.fAdsGunKickPitchMin")) return false;
        if (!r.scalar(&asset->fAdsGunKickPitchMax, "WeaponDef.fAdsGunKickPitchMax")) return false;
        if (!r.scalar(&asset->fAdsGunKickYawMin, "WeaponDef.fAdsGunKickYawMin")) return false;
        if (!r.scalar(&asset->fAdsGunKickYawMax, "WeaponDef.fAdsGunKickYawMax")) return false;
        if (!r.scalar(&asset->fAdsGunKickMagMin, "WeaponDef.fAdsGunKickMagMin")) return false;
        if (!r.scalar(&asset->fAdsGunKickAccel, "WeaponDef.fAdsGunKickAccel")) return false;
        if (!r.scalar(&asset->fAdsGunKickSpeedMax, "WeaponDef.fAdsGunKickSpeedMax")) return false;
        if (!r.scalar(&asset->fAdsGunKickSpeedDecay, "WeaponDef.fAdsGunKickSpeedDecay")) return false;
        if (!r.scalar(&asset->fAdsGunKickStaticDecay, "WeaponDef.fAdsGunKickStaticDecay")) return false;
        if (!r.scalar(&asset->fAdsViewKickPitchMin, "WeaponDef.fAdsViewKickPitchMin")) return false;
        if (!r.scalar(&asset->fAdsViewKickPitchMax, "WeaponDef.fAdsViewKickPitchMax")) return false;
        if (!r.scalar(&asset->fAdsViewKickYawMin, "WeaponDef.fAdsViewKickYawMin")) return false;
        if (!r.scalar(&asset->fAdsViewKickYawMax, "WeaponDef.fAdsViewKickYawMax")) return false;
        if (!r.scalar(&asset->fAdsViewKickMagMin, "WeaponDef.fAdsViewKickMagMin")) return false;
        if (!r.scalar(&asset->fAdsViewScatterMin, "WeaponDef.fAdsViewScatterMin")) return false;
        if (!r.scalar(&asset->fAdsViewScatterMax, "WeaponDef.fAdsViewScatterMax")) return false;
        if (!r.scalar(&asset->fAdsSpread, "WeaponDef.fAdsSpread")) return false;
        if (!r.scalar(&asset->iVisibilityAxis, "WeaponDef.iVisibilityAxis")) return false;
        if (!r.scalar(&asset->fVisibilityUpOffset, "WeaponDef.fVisibilityUpOffset")) return false;
        if (!r.scalar(&asset->hipGunKickReducedKickBullets, "WeaponDef.hipGunKickReducedKickBullets")) return false;
        if (!r.scalar(&asset->hipGunKickReducedKickPercent, "WeaponDef.hipGunKickReducedKickPercent")) return false;
        if (!r.scalar(&asset->fHipGunKickPitchMin, "WeaponDef.fHipGunKickPitchMin")) return false;
        if (!r.scalar(&asset->fHipGunKickPitchMax, "WeaponDef.fHipGunKickPitchMax")) return false;
        if (!r.scalar(&asset->fHipGunKickYawMin, "WeaponDef.fHipGunKickYawMin")) return false;
        if (!r.scalar(&asset->fHipGunKickYawMax, "WeaponDef.fHipGunKickYawMax")) return false;
        if (!r.scalar(&asset->fHipGunKickMagMin, "WeaponDef.fHipGunKickMagMin")) return false;
        if (!r.scalar(&asset->fHipGunKickAccel, "WeaponDef.fHipGunKickAccel")) return false;
        if (!r.scalar(&asset->fHipGunKickSpeedMax, "WeaponDef.fHipGunKickSpeedMax")) return false;
        if (!r.scalar(&asset->fHipGunKickSpeedDecay, "WeaponDef.fHipGunKickSpeedDecay")) return false;
        if (!r.scalar(&asset->fHipGunKickStaticDecay, "WeaponDef.fHipGunKickStaticDecay")) return false;
        if (!r.scalar(&asset->fHipViewKickPitchMin, "WeaponDef.fHipViewKickPitchMin")) return false;
        if (!r.scalar(&asset->fHipViewKickPitchMax, "WeaponDef.fHipViewKickPitchMax")) return false;
        if (!r.scalar(&asset->fHipViewKickYawMin, "WeaponDef.fHipViewKickYawMin")) return false;
        if (!r.scalar(&asset->fHipViewKickYawMax, "WeaponDef.fHipViewKickYawMax")) return false;
        if (!r.scalar(&asset->fHipViewKickMagMin, "WeaponDef.fHipViewKickMagMin")) return false;
        if (!r.scalar(&asset->fHipViewScatterMin, "WeaponDef.fHipViewScatterMin")) return false;
        if (!r.scalar(&asset->fHipViewScatterMax, "WeaponDef.fHipViewScatterMax")) return false;
        if (!r.scalar(&asset->multipleReloadClipPercentage, "WeaponDef.multipleReloadClipPercentage")) return false;
        if (!r.scalar(&asset->kickAlignedInputScalar, "WeaponDef.kickAlignedInputScalar")) return false;
        if (!r.scalar(&asset->kickOpposedInputScalar, "WeaponDef.kickOpposedInputScalar")) return false;
        if (!r.scalar(&asset->fightDist, "WeaponDef.fightDist")) return false;
        if (!r.scalar(&asset->maxDist, "WeaponDef.maxDist")) return false;
        if (!r.scalar(&asset->iPositionReloadTransTime, "WeaponDef.iPositionReloadTransTime")) return false;
        if (!r.scalar(&asset->leftArc, "WeaponDef.leftArc")) return false;
        if (!r.scalar(&asset->rightArc, "WeaponDef.rightArc")) return false;
        if (!r.scalar(&asset->topArc, "WeaponDef.topArc")) return false;
        if (!r.scalar(&asset->bottomArc, "WeaponDef.bottomArc")) return false;
        if (!r.scalar(&asset->softLeftRightArc, "WeaponDef.softLeftRightArc")) return false;
        if (!r.scalar(&asset->accuracy, "WeaponDef.accuracy")) return false;
        if (!r.scalar(&asset->aiSpread, "WeaponDef.aiSpread")) return false;
        if (!r.scalar(&asset->playerSpread, "WeaponDef.playerSpread")) return false;
        if (!r.fixed_scalars(&asset->minTurnSpeed, 2, "WeaponDef.minTurnSpeed")) return false;
        if (!r.fixed_scalars(&asset->maxTurnSpeed, 2, "WeaponDef.maxTurnSpeed")) return false;
        if (!r.scalar(&asset->pitchConvergenceTime, "WeaponDef.pitchConvergenceTime")) return false;
        if (!r.scalar(&asset->yawConvergenceTime, "WeaponDef.yawConvergenceTime")) return false;
        if (!r.scalar(&asset->suppressTime, "WeaponDef.suppressTime")) return false;
        if (!r.scalar(&asset->maxRange, "WeaponDef.maxRange")) return false;
        if (!r.scalar(&asset->fAnimHorRotateInc, "WeaponDef.fAnimHorRotateInc")) return false;
        if (!r.scalar(&asset->fPlayerPositionDist, "WeaponDef.fPlayerPositionDist")) return false;
        if (!r.scalar(&asset->horizViewJitter, "WeaponDef.horizViewJitter")) return false;
        if (!r.scalar(&asset->vertViewJitter, "WeaponDef.vertViewJitter")) return false;
        if (!r.scalar(&asset->scanSpeed, "WeaponDef.scanSpeed")) return false;
        if (!r.scalar(&asset->scanAccel, "WeaponDef.scanAccel")) return false;
        if (!r.scalar(&asset->scanPauseTime, "WeaponDef.scanPauseTime")) return false;
        if (!r.fixed_scalars(&asset->adsSpeedMs, 2, "WeaponDef.adsSpeedMs")) return false;
        if (!r.scalar(&asset->minDamage, "WeaponDef.minDamage")) return false;
        if (!r.scalar(&asset->minPlayerDamage, "WeaponDef.minPlayerDamage")) return false;
        if (!r.scalar(&asset->mid1Damage, "WeaponDef.mid1Damage")) return false;
        if (!r.scalar(&asset->mid2Damage, "WeaponDef.mid2Damage")) return false;
        if (!r.scalar(&asset->mid3Damage, "WeaponDef.mid3Damage")) return false;
        if (!r.scalar(&asset->mid1PlayerDamage, "WeaponDef.mid1PlayerDamage")) return false;
        if (!r.scalar(&asset->mid2PlayerDamage, "WeaponDef.mid2PlayerDamage")) return false;
        if (!r.scalar(&asset->mid3PlayerDamage, "WeaponDef.mid3PlayerDamage")) return false;
        if (!r.scalar(&asset->maxDamageRange, "WeaponDef.maxDamageRange")) return false;
        if (!r.scalar(&asset->mid1DamageRange, "WeaponDef.mid1DamageRange")) return false;
        if (!r.scalar(&asset->mid2DamageRange, "WeaponDef.mid2DamageRange")) return false;
        if (!r.scalar(&asset->mid3DamageRange, "WeaponDef.mid3DamageRange")) return false;
        if (!r.scalar(&asset->minDamageRange, "WeaponDef.minDamageRange")) return false;
        if (!r.scalar(&asset->destabilizationRateTime, "WeaponDef.destabilizationRateTime")) return false;
        if (!r.scalar(&asset->destabilizationCurvatureMax, "WeaponDef.destabilizationCurvatureMax")) return false;
        if (!r.scalar(&asset->destabilizeDistance, "WeaponDef.destabilizeDistance")) return false;
        if (!r.scalar(&asset->robotechMaxPitch, "WeaponDef.robotechMaxPitch")) return false;
        if (!r.scalar(&asset->robotechMaxYaw, "WeaponDef.robotechMaxYaw")) return false;
        if (!r.scalar(&asset->robotechFrequency, "WeaponDef.robotechFrequency")) return false;
        if (!r.scalar(&asset->robotechVariancePitch, "WeaponDef.robotechVariancePitch")) return false;
        if (!r.scalar(&asset->robotechVarianceYaw, "WeaponDef.robotechVarianceYaw")) return false;
        if (!r.scalar(&asset->robotechVarianceFrequency, "WeaponDef.robotechVarianceFrequency")) return false;
        if (!r.pointer_array(&asset->locationDamageMultipliers, 22, "WeaponDef.locationDamageMultipliers", [&](const auto* value) { return r.scalar(value, "WeaponDef.locationDamageMultipliers"); })) return false;
        if (!r.pointer_array(&asset->hitLocPriorityMap, 22, "WeaponDef.hitLocPriorityMap", [&](const auto* value) { return r.scalar(value, "WeaponDef.hitLocPriorityMap"); })) return false;
        if (!r.fixed_scalars(&asset->unittypeMultipliers, 9, "WeaponDef.unittypeMultipliers")) return false;
        if (!r.asset_field(&asset->fireRumble, "WeaponDef.fireRumble")) return false;
        if (!r.asset_field(&asset->meleeImpactRumble, "WeaponDef.meleeImpactRumble")) return false;
        if (!r.scalar(&asset->tracerStyle, "WeaponDef.tracerStyle")) return false;
        if (!r.asset_field(&asset->tracerType, "WeaponDef.tracerType")) return false;
        if (!r.asset_field(&asset->overchargeTracerType, "WeaponDef.overchargeTracerType")) return false;
        if (!r.asset_field(&asset->laserTypeFriendly, "WeaponDef.laserTypeFriendly")) return false;
        if (!r.asset_field(&asset->laserTypeEnemy, "WeaponDef.laserTypeEnemy")) return false;
        if (!r.scalar(&asset->turretADSEnabled, "WeaponDef.turretADSEnabled")) return false;
        if (!r.scalar(&asset->turretADSTime, "WeaponDef.turretADSTime")) return false;
        if (!r.scalar(&asset->turretFov, "WeaponDef.turretFov")) return false;
        if (!r.scalar(&asset->turretFovADS, "WeaponDef.turretFovADS")) return false;
        if (!r.scalar(&asset->turretScopeZoomRate, "WeaponDef.turretScopeZoomRate")) return false;
        if (!r.scalar(&asset->turretScopeZoomMin, "WeaponDef.turretScopeZoomMin")) return false;
        if (!r.scalar(&asset->turretScopeZoomMax, "WeaponDef.turretScopeZoomMax")) return false;
        if (!r.scalar(&asset->turretOverheatUpRate, "WeaponDef.turretOverheatUpRate")) return false;
        if (!r.scalar(&asset->turretOverheatDownRate, "WeaponDef.turretOverheatDownRate")) return false;
        if (!r.scalar(&asset->turretOverheatPenalty, "WeaponDef.turretOverheatPenalty")) return false;
        if (!r.string_field(&asset->turretOverheatSound, "WeaponDef.turretOverheatSound")) return false;
        if (!r.fx(asset->turretOverheatEffect, "WeaponDef.turretOverheatEffect")) return false;
        if (!r.asset_field(&asset->turretBarrelSpinRumble, "WeaponDef.turretBarrelSpinRumble")) return false;
        if (!r.scalar(&asset->turretBarrelSpinSpeed, "WeaponDef.turretBarrelSpinSpeed")) return false;
        if (!r.scalar(&asset->turretBarrelSpinUpTime, "WeaponDef.turretBarrelSpinUpTime")) return false;
        if (!r.scalar(&asset->turretBarrelSpinDownTime, "WeaponDef.turretBarrelSpinDownTime")) return false;
        if (!r.string_field(&asset->turretBarrelSpinMaxSnd, "WeaponDef.turretBarrelSpinMaxSnd")) return false;
        if (!r.native_string_array(&asset->turretBarrelSpinUpSnd, 4, "WeaponDef.turretBarrelSpinUpSnd")) return false;
        if (!r.native_string_array(&asset->turretBarrelSpinDownSnd, 4, "WeaponDef.turretBarrelSpinDownSnd")) return false;
        if (!r.string_field(&asset->missileConeSoundAlias, "WeaponDef.missileConeSoundAlias")) return false;
        if (!r.string_field(&asset->missileConeSoundAliasAtBase, "WeaponDef.missileConeSoundAliasAtBase")) return false;
        if (!r.scalar(&asset->missileConeSoundRadiusAtTop, "WeaponDef.missileConeSoundRadiusAtTop")) return false;
        if (!r.scalar(&asset->missileConeSoundRadiusAtBase, "WeaponDef.missileConeSoundRadiusAtBase")) return false;
        if (!r.scalar(&asset->missileConeSoundHeight, "WeaponDef.missileConeSoundHeight")) return false;
        if (!r.scalar(&asset->missileConeSoundOriginOffset, "WeaponDef.missileConeSoundOriginOffset")) return false;
        if (!r.scalar(&asset->missileConeSoundVolumescaleAtCore, "WeaponDef.missileConeSoundVolumescaleAtCore")) return false;
        if (!r.scalar(&asset->missileConeSoundVolumescaleAtEdge, "WeaponDef.missileConeSoundVolumescaleAtEdge")) return false;
        if (!r.scalar(&asset->missileConeSoundVolumescaleCoreSize, "WeaponDef.missileConeSoundVolumescaleCoreSize")) return false;
        if (!r.scalar(&asset->missileConeSoundPitchAtTop, "WeaponDef.missileConeSoundPitchAtTop")) return false;
        if (!r.scalar(&asset->missileConeSoundPitchAtBottom, "WeaponDef.missileConeSoundPitchAtBottom")) return false;
        if (!r.scalar(&asset->missileConeSoundPitchTopSize, "WeaponDef.missileConeSoundPitchTopSize")) return false;
        if (!r.scalar(&asset->missileConeSoundPitchBottomSize, "WeaponDef.missileConeSoundPitchBottomSize")) return false;
        if (!r.scalar(&asset->missileConeSoundCrossfadeTopSize, "WeaponDef.missileConeSoundCrossfadeTopSize")) return false;
        if (!r.scalar(&asset->missileConeSoundCrossfadeBottomSize, "WeaponDef.missileConeSoundCrossfadeBottomSize")) return false;
        if (!r.script_field(&asset->knifeAttachTagOverride, "WeaponDef.knifeAttachTagOverride")) return false;
        if (!r.script_field(&asset->knifeAttachTagOverride2, "WeaponDef.knifeAttachTagOverride2")) return false;
        if (!r.scalar(&asset->knifeAlwaysAttached, "WeaponDef.knifeAlwaysAttached")) return false;
        if (!r.scalar(&asset->meleeOverrideValues, "WeaponDef.meleeOverrideValues")) return false;
        if (!r.scalar(&asset->aim_automelee_lerp, "WeaponDef.aim_automelee_lerp")) return false;
        if (!r.scalar(&asset->aim_automelee_region_height, "WeaponDef.aim_automelee_region_height")) return false;
        if (!r.scalar(&asset->aim_automelee_region_width, "WeaponDef.aim_automelee_region_width")) return false;
        if (!r.scalar(&asset->aim_automelee_maxPitchMovement, "WeaponDef.aim_automelee_maxPitchMovement")) return false;
        if (!r.scalar(&asset->aim_automelee_maxYawMovement, "WeaponDef.aim_automelee_maxYawMovement")) return false;
        if (!r.scalar(&asset->player_meleeHeight, "WeaponDef.player_meleeHeight")) return false;
        if (!r.scalar(&asset->player_meleeWidth, "WeaponDef.player_meleeWidth")) return false;
        if (!r.scalar(&asset->playerMeleeRangeStanding, "WeaponDef.playerMeleeRangeStanding")) return false;
        if (!r.scalar(&asset->playerMeleeRangeCrouched, "WeaponDef.playerMeleeRangeCrouched")) return false;
        if (!r.scalar(&asset->playerMeleeRangeProne, "WeaponDef.playerMeleeRangeProne")) return false;
        if (!r.scalar(&asset->playerMeleeRangeChargeStanding, "WeaponDef.playerMeleeRangeChargeStanding")) return false;
        if (!r.scalar(&asset->playerMeleeRangeChargeCrouched, "WeaponDef.playerMeleeRangeChargeCrouched")) return false;
        if (!r.scalar(&asset->playerMeleeChargeHeightTolerance, "WeaponDef.playerMeleeChargeHeightTolerance")) return false;
        if (!r.scalar(&asset->shieldAllowFiring, "WeaponDef.shieldAllowFiring")) return false;
        if (!r.scalar(&asset->shieldUnkBool, "WeaponDef.shieldUnkBool")) return false;
        if (!r.scalar(&asset->shieldMaxSpeed, "WeaponDef.shieldMaxSpeed")) return false;
        if (!r.scalar(&asset->shieldAlwaysDisplay, "WeaponDef.shieldAlwaysDisplay")) return false;
        if (!r.asset_field(&asset->shieldDeployGesture, "WeaponDef.shieldDeployGesture")) return false;
        if (!r.asset_field(&asset->shieldFireWeapGesture, "WeaponDef.shieldFireWeapGesture")) return false;
        if (!r.asset_field(&asset->shieldDeployWhileFiring, "WeaponDef.shieldDeployWhileFiring")) return false;
        if (!r.asset_field(&asset->shieldRetractWhileFiring, "WeaponDef.shieldRetractWhileFiring")) return false;
        if (!r.asset_field(&asset->shieldBashGesture, "WeaponDef.shieldBashGesture")) return false;
        if (!r.fx(asset->shieldMeleeFx, "WeaponDef.shieldMeleeFx")) return false;
        if (!r.scalar(&asset->shieldMeleeFxDelay, "WeaponDef.shieldMeleeFxDelay")) return false;
        if (!r.scalar(&asset->HitEarthquakeScale, "WeaponDef.HitEarthquakeScale")) return false;
        if (!r.scalar(&asset->HitEarthquakeDuration, "WeaponDef.HitEarthquakeDuration")) return false;
        if (!r.scalar(&asset->HitEarthquakeRadius, "WeaponDef.HitEarthquakeRadius")) return false;
        if (!r.asset_field(&asset->shieldHitRumble, "WeaponDef.shieldHitRumble")) return false;
        if (!r.scalar(&asset->MissEarthquakeScale, "WeaponDef.MissEarthquakeScale")) return false;
        if (!r.scalar(&asset->MissEarthquakeDuration, "WeaponDef.MissEarthquakeDuration")) return false;
        if (!r.scalar(&asset->MissEarthquakeRadius, "WeaponDef.MissEarthquakeRadius")) return false;
        if (!r.asset_field(&asset->shieldMissRumble, "WeaponDef.shieldMissRumble")) return false;
        if (!r.scalar(&asset->shieldDeployButton, "WeaponDef.shieldDeployButton")) return false;
        if (!r.scalar(&asset->shieldUsesEnergy, "WeaponDef.shieldUsesEnergy")) return false;
        if (!r.scalar(&asset->shieldMaxEnergy, "WeaponDef.shieldMaxEnergy")) return false;
        if (!r.scalar(&asset->shieldConsumptionRate, "WeaponDef.shieldConsumptionRate")) return false;
        if (!r.scalar(&asset->shieldMeleeEnergyCost, "WeaponDef.shieldMeleeEnergyCost")) return false;
        if (!r.scalar(&asset->shieldMeleeHitEnergyCost, "WeaponDef.shieldMeleeHitEnergyCost")) return false;
        if (!r.scalar(&asset->reactiveMotionRadiusScale, "WeaponDef.reactiveMotionRadiusScale")) return false;
        if (!r.scalar(&asset->reactiveMotionFrequencyScale, "WeaponDef.reactiveMotionFrequencyScale")) return false;
        if (!r.scalar(&asset->reactiveMotionAmplitudeScale, "WeaponDef.reactiveMotionAmplitudeScale")) return false;
        if (!r.scalar(&asset->reactiveMotionFalloff, "WeaponDef.reactiveMotionFalloff")) return false;
        if (!r.scalar(&asset->reactiveMotionLifetime, "WeaponDef.reactiveMotionLifetime")) return false;
        if (!r.scalar(&asset->hasAnyTransientModels, "WeaponDef.hasAnyTransientModels")) return false;
        if (!r.scalar(&asset->sharedAmmo, "WeaponDef.sharedAmmo")) return false;
        if (!r.scalar(&asset->lockonSupported, "WeaponDef.lockonSupported")) return false;
        if (!r.scalar(&asset->requireLockonToFire, "WeaponDef.requireLockonToFire")) return false;
        if (!r.scalar(&asset->isAirburstWeapon, "WeaponDef.isAirburstWeapon")) return false;
        if (!r.scalar(&asset->bigExplosion, "WeaponDef.bigExplosion")) return false;
        if (!r.scalar(&asset->noAdsWhenMagEmpty, "WeaponDef.noAdsWhenMagEmpty")) return false;
        if (!r.scalar(&asset->avoidDropCleanup, "WeaponDef.avoidDropCleanup")) return false;
        if (!r.scalar(&asset->allowGrenadeSwitching, "WeaponDef.allowGrenadeSwitching")) return false;
        if (!r.scalar(&asset->inheritsPerks, "WeaponDef.inheritsPerks")) return false;
        if (!r.scalar(&asset->crosshairColorChange, "WeaponDef.crosshairColorChange")) return false;
        if (!r.scalar(&asset->bRifleBullet, "WeaponDef.bRifleBullet")) return false;
        if (!r.scalar(&asset->bEnergyBullet, "WeaponDef.bEnergyBullet")) return false;
        if (!r.scalar(&asset->armorPiercing, "WeaponDef.armorPiercing")) return false;
        if (!r.scalar(&asset->impaling, "WeaponDef.impaling")) return false;
        if (!r.scalar(&asset->bBoltAction, "WeaponDef.bBoltAction")) return false;
        if (!r.scalar(&asset->aimDownSight, "WeaponDef.aimDownSight")) return false;
        if (!r.scalar(&asset->canHoldBreath, "WeaponDef.canHoldBreath")) return false;
        if (!r.scalar(&asset->meleeOnly, "WeaponDef.meleeOnly")) return false;
        if (!r.scalar(&asset->supportsAlternateMelee, "WeaponDef.supportsAlternateMelee")) return false;
        if (!r.scalar(&asset->canVariableZoom, "WeaponDef.canVariableZoom")) return false;
        if (!r.scalar(&asset->bRechamberWhileAds, "WeaponDef.bRechamberWhileAds")) return false;
        if (!r.scalar(&asset->bBulletExplosiveDamage, "WeaponDef.bBulletExplosiveDamage")) return false;
        if (!r.scalar(&asset->bCookOffHold, "WeaponDef.bCookOffHold")) return false;
        if (!r.scalar(&asset->reticleSpin45, "WeaponDef.reticleSpin45")) return false;
        if (!r.scalar(&asset->bClipOnly, "WeaponDef.bClipOnly")) return false;
        if (!r.scalar(&asset->bDoesNotConsumeAmmo, "WeaponDef.bDoesNotConsumeAmmo")) return false;
        if (!r.scalar(&asset->bRemoveWeaponOnEmpty, "WeaponDef.bRemoveWeaponOnEmpty")) return false;
        if (!r.scalar(&asset->noAmmoPickup, "WeaponDef.noAmmoPickup")) return false;
        if (!r.scalar(&asset->adsFireOnly, "WeaponDef.adsFireOnly")) return false;
        if (!r.scalar(&asset->cancelAutoHolsterWhenEmpty, "WeaponDef.cancelAutoHolsterWhenEmpty")) return false;
        if (!r.scalar(&asset->disableSwitchToWhenEmpty, "WeaponDef.disableSwitchToWhenEmpty")) return false;
        if (!r.scalar(&asset->suppressAmmoPrimaryDisplay, "WeaponDef.suppressAmmoPrimaryDisplay")) return false;
        if (!r.scalar(&asset->suppressAmmoReserveDisplay, "WeaponDef.suppressAmmoReserveDisplay")) return false;
        if (!r.scalar(&asset->laserSightDuringNightvision, "WeaponDef.laserSightDuringNightvision")) return false;
        if (!r.scalar(&asset->markableViewmodel, "WeaponDef.markableViewmodel")) return false;
        if (!r.scalar(&asset->flipKillIcon, "WeaponDef.flipKillIcon")) return false;
        if (!r.scalar(&asset->bNoPartialReload, "WeaponDef.bNoPartialReload")) return false;
        if (!r.scalar(&asset->reloadDisabled, "WeaponDef.reloadDisabled")) return false;
        if (!r.scalar(&asset->blocksProne, "WeaponDef.blocksProne")) return false;
        if (!r.scalar(&asset->silenced, "WeaponDef.silenced")) return false;
        if (!r.scalar(&asset->isRollingGrenade, "WeaponDef.isRollingGrenade")) return false;
        if (!r.scalar(&asset->dropGrenadeHeldOnDeath, "WeaponDef.dropGrenadeHeldOnDeath")) return false;
        if (!r.scalar(&asset->projExplosionEffectForceNormalUp, "WeaponDef.projExplosionEffectForceNormalUp")) return false;
        if (!r.scalar(&asset->projExplosionEffectInheritParentDirection, "WeaponDef.projExplosionEffectInheritParentDirection")) return false;
        if (!r.scalar(&asset->bProjImpactExplode, "WeaponDef.bProjImpactExplode")) return false;
        if (!r.scalar(&asset->disableProjectileCrumpleCheck, "WeaponDef.disableProjectileCrumpleCheck")) return false;
        if (!r.scalar(&asset->bProjTrajectoryEvents, "WeaponDef.bProjTrajectoryEvents")) return false;
        if (!r.scalar(&asset->bProjWhizByEnabled, "WeaponDef.bProjWhizByEnabled")) return false;
        if (!r.scalar(&asset->stickToPlayers, "WeaponDef.stickToPlayers")) return false;
        if (!r.scalar(&asset->stickToVehicles, "WeaponDef.stickToVehicles")) return false;
        if (!r.scalar(&asset->stickToTurrets, "WeaponDef.stickToTurrets")) return false;
        if (!r.scalar(&asset->stickToNonStick, "WeaponDef.stickToNonStick")) return false;
        if (!r.scalar(&asset->projEnableMissileStickiness, "WeaponDef.projEnableMissileStickiness")) return false;
        if (!r.scalar(&asset->thrownSideways, "WeaponDef.thrownSideways")) return false;
        if (!r.scalar(&asset->hasDetonator, "WeaponDef.hasDetonator")) return false;
        if (!r.scalar(&asset->disableFiring, "WeaponDef.disableFiring")) return false;
        if (!r.scalar(&asset->firesOnWeaponSwitch, "WeaponDef.firesOnWeaponSwitch")) return false;
        if (!r.scalar(&asset->disableHolding, "WeaponDef.disableHolding")) return false;
        if (!r.scalar(&asset->timedDetonation, "WeaponDef.timedDetonation")) return false;
        if (!r.scalar(&asset->explosiveDamageDelay, "WeaponDef.explosiveDamageDelay")) return false;
        if (!r.scalar(&asset->fuseTime, "WeaponDef.fuseTime")) return false;
        if (!r.scalar(&asset->aiFuseTime, "WeaponDef.aiFuseTime")) return false;
        if (!r.scalar(&asset->maxHoldTime, "WeaponDef.maxHoldTime")) return false;
        if (!r.scalar(&asset->holdButtonToThrow, "WeaponDef.holdButtonToThrow")) return false;
        if (!r.scalar(&asset->infiniteHold, "WeaponDef.infiniteHold")) return false;
        if (!r.scalar(&asset->freezeMovementWhenFiring, "WeaponDef.freezeMovementWhenFiring")) return false;
        if (!r.scalar(&asset->offhandAllowsSprint, "WeaponDef.offhandAllowsSprint")) return false;
        if (!r.scalar(&asset->thermalScope, "WeaponDef.thermalScope")) return false;
        if (!r.scalar(&asset->thermalToggle, "WeaponDef.thermalToggle")) return false;
        if (!r.scalar(&asset->outlineEnemies, "WeaponDef.outlineEnemies")) return false;
        if (!r.scalar(&asset->outlineDepthTest, "WeaponDef.outlineDepthTest")) return false;
        if (!r.scalar(&asset->outlineFill, "WeaponDef.outlineFill")) return false;
        if (!r.scalar(&asset->enemyOutlineR, "WeaponDef.enemyOutlineR")) return false;
        if (!r.scalar(&asset->enemyOutlineG, "WeaponDef.enemyOutlineG")) return false;
        if (!r.scalar(&asset->enemyOutlineB, "WeaponDef.enemyOutlineB")) return false;
        if (!r.scalar(&asset->enemyOutlineA, "WeaponDef.enemyOutlineA")) return false;
        if (!r.scalar(&asset->allyOutlineR, "WeaponDef.allyOutlineR")) return false;
        if (!r.scalar(&asset->allyOutlineG, "WeaponDef.allyOutlineG")) return false;
        if (!r.scalar(&asset->allyOutlineB, "WeaponDef.allyOutlineB")) return false;
        if (!r.scalar(&asset->allyOutlineA, "WeaponDef.allyOutlineA")) return false;
        if (!r.scalar(&asset->depthScan, "WeaponDef.depthScan")) return false;
        if (!r.scalar(&asset->depthScanThickness, "WeaponDef.depthScanThickness")) return false;
        if (!r.scalar(&asset->depthScanR, "WeaponDef.depthScanR")) return false;
        if (!r.scalar(&asset->depthScanG, "WeaponDef.depthScanG")) return false;
        if (!r.scalar(&asset->depthScanB, "WeaponDef.depthScanB")) return false;
        if (!r.scalar(&asset->depthScanA, "WeaponDef.depthScanA")) return false;
        if (!r.scalar(&asset->depthScanOutlineThickness, "WeaponDef.depthScanOutlineThickness")) return false;
        if (!r.scalar(&asset->depthScanOutlineR, "WeaponDef.depthScanOutlineR")) return false;
        if (!r.scalar(&asset->depthScanOutlineG, "WeaponDef.depthScanOutlineG")) return false;
        if (!r.scalar(&asset->depthScanOutlineB, "WeaponDef.depthScanOutlineB")) return false;
        if (!r.scalar(&asset->depthScanOutlineA, "WeaponDef.depthScanOutlineA")) return false;
        if (!r.scalar(&asset->depthScanOverlay, "WeaponDef.depthScanOverlay")) return false;
        if (!r.scalar(&asset->depthScanOverlayStrength, "WeaponDef.depthScanOverlayStrength")) return false;
        if (!r.scalar(&asset->depthScanOverlayXTiles, "WeaponDef.depthScanOverlayXTiles")) return false;
        if (!r.scalar(&asset->depthScanOverlayYTiles, "WeaponDef.depthScanOverlayYTiles")) return false;
        if (!r.scalar(&asset->depthScanOverlayXScroll, "WeaponDef.depthScanOverlayXScroll")) return false;
        if (!r.scalar(&asset->depthScanOverlayYScroll, "WeaponDef.depthScanOverlayYScroll")) return false;
        if (!r.scalar(&asset->blurSceneAdsInFraction, "WeaponDef.blurSceneAdsInFraction")) return false;
        if (!r.scalar(&asset->blurSceneAdsOutFraction, "WeaponDef.blurSceneAdsOutFraction")) return false;
        if (!r.scalar(&asset->altModeSameWeapon, "WeaponDef.altModeSameWeapon")) return false;
        if (!r.scalar(&asset->turretBarrelSpinEnabled, "WeaponDef.turretBarrelSpinEnabled")) return false;
        if (!r.scalar(&asset->missileConeSoundEnabled, "WeaponDef.missileConeSoundEnabled")) return false;
        if (!r.scalar(&asset->missileConeSoundPitchshiftEnabled, "WeaponDef.missileConeSoundPitchshiftEnabled")) return false;
        if (!r.scalar(&asset->missileConeSoundCrossfadeEnabled, "WeaponDef.missileConeSoundCrossfadeEnabled")) return false;
        if (!r.scalar(&asset->offhandHoldIsCancelable, "WeaponDef.offhandHoldIsCancelable")) return false;
        if (!r.scalar(&asset->doNotAllowAttachmentsToOverrideSpread, "WeaponDef.doNotAllowAttachmentsToOverrideSpread")) return false;
        if (!r.scalar(&asset->useScopeDrift, "WeaponDef.useScopeDrift")) return false;
        if (!r.scalar(&asset->alwaysShatterGlassOnImpact, "WeaponDef.alwaysShatterGlassOnImpact")) return false;
        if (!r.scalar(&asset->oldWeapon, "WeaponDef.oldWeapon")) return false;
        if (!r.scalar(&asset->jumpSpread, "WeaponDef.jumpSpread")) return false;
        if (!r.scalar(&asset->noFullViewmodelAnimations, "WeaponDef.noFullViewmodelAnimations")) return false;
        if (!r.scalar(&asset->killcamOffset, "WeaponDef.killcamOffset")) return false;
        if (!r.scalar(&asset->useDualFOV, "WeaponDef.useDualFOV")) return false;
        if (!r.scalar(&asset->disableDrop, "WeaponDef.disableDrop")) return false;
        if (!r.scalar(&asset->preferredDrop, "WeaponDef.preferredDrop")) return false;
        if (!r.asset_field(&asset->gestureAnimation, "WeaponDef.gestureAnimation")) return false;
        if (!r.scalar(&asset->gestureFireStateTime, "WeaponDef.gestureFireStateTime")) return false;
        if (!r.asset_field(&asset->gesturePullback, "WeaponDef.gesturePullback")) return false;
        if (!r.scalar(&asset->minPullbackTime, "WeaponDef.minPullbackTime")) return false;
        if (!r.asset_field(&asset->gestureThrow, "WeaponDef.gestureThrow")) return false;
        if (!r.scalar(&asset->gestureFireTime, "WeaponDef.gestureFireTime")) return false;
        if (!r.asset_field(&asset->gestureDetonate, "WeaponDef.gestureDetonate")) return false;
        if (!r.scalar(&asset->gestureDetonationTime, "WeaponDef.gestureDetonationTime")) return false;
        if (!r.scalar(&asset->unk_433, "WeaponDef.unk_433")) return false;
        if (!r.string_field(&asset->unknownString1, "WeaponDef.unknownString1")) return false;
        if (!r.scalar(&asset->unk_434, "WeaponDef.unk_434")) return false;
        if (!r.string_field(&asset->unknownString2, "WeaponDef.unknownString2")) return false;
        if (!r.scalar(&asset->gesturesDisablePrimary, "WeaponDef.gesturesDisablePrimary")) return false;
        if (!r.fx(asset->cameraFireEffect, "WeaponDef.cameraFireEffect")) return false;
        if (!r.scalar(&asset->cameraFireEffectDurationSec, "WeaponDef.cameraFireEffectDurationSec")) return false;
        if (!r.scalar(&asset->changedFireTime, "WeaponDef.changedFireTime")) return false;
        if (!r.scalar(&asset->changedFireTimeAkimbo, "WeaponDef.changedFireTimeAkimbo")) return false;
        if (!r.scalar(&asset->changedFireTimeNumBullets, "WeaponDef.changedFireTimeNumBullets")) return false;
        if (!r.scalar(&asset->chargeType, "WeaponDef.chargeType")) return false;
        if (!r.scalar(&asset->chargeGain, "WeaponDef.chargeGain")) return false;
        if (!r.scalar(&asset->chargeCostPerShot, "WeaponDef.chargeCostPerShot")) return false;
        if (!r.scalar(&asset->chargeLossWhenIdle, "WeaponDef.chargeLossWhenIdle")) return false;
        if (!r.scalar(&asset->chargeEmptyCooldown, "WeaponDef.chargeEmptyCooldown")) return false;
        if (!r.scalar(&asset->chargeFireAtMaxDamageMultiplier, "WeaponDef.chargeFireAtMaxDamageMultiplier")) return false;
        if (!r.scalar(&asset->chargeMeterEffectBoneCount, "WeaponDef.chargeMeterEffectBoneCount")) return false;
        if (!r.fx(asset->chargeMeterEffect, "WeaponDef.chargeMeterEffect")) return false;
        if (!r.string_field(&asset->chargeUpSound, "WeaponDef.chargeUpSound")) return false;
        if (!r.string_field(&asset->chargeDownSound, "WeaponDef.chargeDownSound")) return false;
        if (!r.string_field(&asset->chargeUpSoundPlayer, "WeaponDef.chargeUpSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeDownSoundPlayer, "WeaponDef.chargeDownSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeDownToUpSound, "WeaponDef.chargeDownToUpSound")) return false;
        if (!r.string_field(&asset->chargeDownToUpSoundPlayer, "WeaponDef.chargeDownToUpSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeUpToDownSound, "WeaponDef.chargeUpToDownSound")) return false;
        if (!r.string_field(&asset->chargeUpToDownSoundPlayer, "WeaponDef.chargeUpToDownSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeMaxSound, "WeaponDef.chargeMaxSound")) return false;
        if (!r.string_field(&asset->chargeMaxSoundPlayer, "WeaponDef.chargeMaxSoundPlayer")) return false;
        if (!r.scalar(&asset->chargeHudReveal, "WeaponDef.chargeHudReveal")) return false;
        if (!r.asset_field(&asset->chargeRumble, "WeaponDef.chargeRumble")) return false;
        if (!r.script_field(&asset->stowTag, "WeaponDef.stowTag")) return false;
        if (!r.asset_field(&asset->stowOffsetModel, "WeaponDef.stowOffsetModel")) return false;
        if (!r.scalar(&asset->maxTargetAngle, "WeaponDef.maxTargetAngle")) return false;
        if (!r.scalar(&asset->spaceshipSecondaryWeapon, "WeaponDef.spaceshipSecondaryWeapon")) return false;
        if (!r.scalar(&asset->impulseFieldRadius, "WeaponDef.impulseFieldRadius")) return false;
        if (!r.scalar(&asset->impulseFieldInitialSpeed, "WeaponDef.impulseFieldInitialSpeed")) return false;
        if (!r.scalar(&asset->impulseFieldMaxSpeed, "WeaponDef.impulseFieldMaxSpeed")) return false;
        if (!r.scalar(&asset->impulseFieldAcceleration, "WeaponDef.impulseFieldAcceleration")) return false;
        if (!r.scalar(&asset->impulseFieldInAirImpulseMultiplier, "WeaponDef.impulseFieldInAirImpulseMultiplier")) return false;
        if (!r.scalar(&asset->impulseFieldInAirImpulseMultiplierInterpTime, "WeaponDef.impulseFieldInAirImpulseMultiplierInterpTime")) return false;
        if (!r.scalar(&asset->impulseFieldSlideMultiplier, "WeaponDef.impulseFieldSlideMultiplier")) return false;
        if (!r.scalar(&asset->impulseFieldSlideMultiplierInterpTime, "WeaponDef.impulseFieldSlideMultiplierInterpTime")) return false;
        if (!r.scalar(&asset->impulseFieldIsPush, "WeaponDef.impulseFieldIsPush")) return false;
        if (!r.scalar(&asset->impulseFieldAffectsFriendlies, "WeaponDef.impulseFieldAffectsFriendlies")) return false;
        if (!r.scalar(&asset->impulseFieldAffectsSelf, "WeaponDef.impulseFieldAffectsSelf")) return false;
        if (!r.scalar(&asset->impulseFieldAffectsProne, "WeaponDef.impulseFieldAffectsProne")) return false;
        if (!r.scalar(&asset->regenerationEnabled, "WeaponDef.regenerationEnabled")) return false;
        if (!r.scalar(&asset->regenerationTimeMs, "WeaponDef.regenerationTimeMs")) return false;
        if (!r.scalar(&asset->regenerationAddTimeMs, "WeaponDef.regenerationAddTimeMs")) return false;
        if (!r.scalar(&asset->regenerationAmount, "WeaponDef.regenerationAmount")) return false;
        if (!r.scalar(&asset->regenerationConsumeStock, "WeaponDef.regenerationConsumeStock")) return false;
        if (!r.scalar(&asset->regenerationDisableWhileFiring, "WeaponDef.regenerationDisableWhileFiring")) return false;
        if (!r.scalar(&asset->deployRequireOnWalkableSurface, "WeaponDef.deployRequireOnWalkableSurface")) return false;
        if (!r.scalar(&asset->deployRequireOnNavmesh, "WeaponDef.deployRequireOnNavmesh")) return false;
        if (!r.scalar(&asset->deployRequireSkyAbove, "WeaponDef.deployRequireSkyAbove")) return false;
        if (!r.scalar(&asset->deployRequireNoOverhang, "WeaponDef.deployRequireNoOverhang")) return false;
        if (!r.scalar(&asset->deployAlwaysUpright, "WeaponDef.deployAlwaysUpright")) return false;
        if (!r.scalar(&asset->deployEdgeSnap, "WeaponDef.deployEdgeSnap")) return false;
        if (!r.scalar(&asset->deployCylinderRadius, "WeaponDef.deployCylinderRadius")) return false;
        if (!r.scalar(&asset->deployCylinderHeight, "WeaponDef.deployCylinderHeight")) return false;
        if (!r.scalar(&asset->deployMaxDistance, "WeaponDef.deployMaxDistance")) return false;
        if (!r.fx(asset->deployEffect, "WeaponDef.deployEffect")) return false;
        if (!r.scalar(&asset->deployValidGroupId, "WeaponDef.deployValidGroupId")) return false;
        if (!r.scalar(&asset->deployIndoorGroupId, "WeaponDef.deployIndoorGroupId")) return false;
        if (!r.scalar(&asset->deployInvalidGroupId, "WeaponDef.deployInvalidGroupId")) return false;
        if (!r.scalar(&asset->deployOutOfRangeGroupId, "WeaponDef.deployOutOfRangeGroupId")) return false;
        if (!r.scalar(&asset->reactiveEmitterDelay, "WeaponDef.reactiveEmitterDelay")) return false;
        if (!r.scalar(&asset->grenadeDangerIconDistance, "WeaponDef.grenadeDangerIconDistance")) return false;
        if (!r.scalar(&asset->unk_466_0, "WeaponDef.unk_466_0")) return false;
        if (!r.scalar(&asset->unk_0, "WeaponDef.unk_0")) return false;
        if (!r.scalar(&asset->unk_1, "WeaponDef.unk_1")) return false;
        if (!r.scalar(&asset->unk_2, "WeaponDef.unk_2")) return false;
        if (!r.scalar(&asset->unk_3, "WeaponDef.unk_3")) return false;
        if (!r.scalar(&asset->unk_4_0, "WeaponDef.unk_4_0")) return false;
        if (!r.scalar(&asset->unk_4_1, "WeaponDef.unk_4_1")) return false;
        if (!r.scalar(&asset->unk_18, "WeaponDef.unk_18")) return false;
        if (!r.scalar(&asset->unk_19, "WeaponDef.unk_19")) return false;
        if (!r.scalar(&asset->unk_20, "WeaponDef.unk_20")) return false;
        if (!r.scalar(&asset->unk_21, "WeaponDef.unk_21")) return false;
        if (!r.scalar(&asset->unk_22, "WeaponDef.unk_22")) return false;
        if (!r.scalar(&asset->unk_23, "WeaponDef.unk_23")) return false;
        if (!r.scalar(&asset->unk_24, "WeaponDef.unk_24")) return false;
        if (!r.scalar(&asset->unk_25, "WeaponDef.unk_25")) return false;
        if (!r.scalar(&asset->unk_26, "WeaponDef.unk_26")) return false;
        if (!r.scalar(&asset->unk_27, "WeaponDef.unk_27")) return false;
        if (!r.scalar(&asset->unk_28, "WeaponDef.unk_28")) return false;
        if (!r.scalar(&asset->unk_29, "WeaponDef.unk_29")) return false;
        if (!r.scalar(&asset->unk_30, "WeaponDef.unk_30")) return false;
        if (!r.scalar(&asset->unk_31, "WeaponDef.unk_31")) return false;
        if (!r.scalar(&asset->unk_32, "WeaponDef.unk_32")) return false;
        if (!r.scalar(&asset->unk_33, "WeaponDef.unk_33")) return false;
        if (!r.scalar(&asset->unk_34, "WeaponDef.unk_34")) return false;
        if (!r.scalar(&asset->unk_35, "WeaponDef.unk_35")) return false;
        if (!r.scalar(&asset->unk_36, "WeaponDef.unk_36")) return false;
        if (!r.scalar(&asset->unk_37, "WeaponDef.unk_37")) return false;
        if (!r.scalar(&asset->unk_38, "WeaponDef.unk_38")) return false;
        if (!r.scalar(&asset->unk_39, "WeaponDef.unk_39")) return false;
        if (!r.scalar(&asset->unk_40, "WeaponDef.unk_40")) return false;
        if (!r.scalar(&asset->unk_41, "WeaponDef.unk_41")) return false;
        if (!r.scalar(&asset->unk_42, "WeaponDef.unk_42")) return false;
        if (!r.scalar(&asset->unk_43, "WeaponDef.unk_43")) return false;
        if (!r.scalar(&asset->unk_44, "WeaponDef.unk_44")) return false;
        if (!r.scalar(&asset->unk_45, "WeaponDef.unk_45")) return false;
        if (!r.scalar(&asset->unk_46, "WeaponDef.unk_46")) return false;
        if (!r.scalar(&asset->unk_47, "WeaponDef.unk_47")) return false;
        if (!r.scalar(&asset->unk_48, "WeaponDef.unk_48")) return false;
        if (!r.scalar(&asset->unk_49, "WeaponDef.unk_49")) return false;
        if (!r.scalar(&asset->unk_50, "WeaponDef.unk_50")) return false;
        if (!r.scalar(&asset->unk_51, "WeaponDef.unk_51")) return false;
        if (!r.scalar(&asset->unk_52, "WeaponDef.unk_52")) return false;
        if (!r.scalar(&asset->unk_53, "WeaponDef.unk_53")) return false;
        if (!r.scalar(&asset->unk_54, "WeaponDef.unk_54")) return false;
        if (!r.scalar(&asset->unk_55, "WeaponDef.unk_55")) return false;
        if (!r.scalar(&asset->unk_56, "WeaponDef.unk_56")) return false;
        if (!r.scalar(&asset->unk_57, "WeaponDef.unk_57")) return false;
        if (!r.scalar(&asset->unk_58, "WeaponDef.unk_58")) return false;
        if (!r.scalar(&asset->unk_59, "WeaponDef.unk_59")) return false;
        if (!r.scalar(&asset->unk_60, "WeaponDef.unk_60")) return false;
        if (!r.scalar(&asset->unk_61, "WeaponDef.unk_61")) return false;
        if (!r.scalar(&asset->unk_62, "WeaponDef.unk_62")) return false;
        if (!r.scalar(&asset->unk_63, "WeaponDef.unk_63")) return false;
        if (!r.scalar(&asset->unk_64, "WeaponDef.unk_64")) return false;
        if (!r.scalar(&asset->unk_65_0, "WeaponDef.unk_65_0")) return false;
        if (!r.scalar(&asset->unk_65_1, "WeaponDef.unk_65_1")) return false;
        if (!r.scalar(&asset->unk_65_2, "WeaponDef.unk_65_2")) return false;
        if (!r.scalar(&asset->unk_65_3, "WeaponDef.unk_65_3")) return false;
        if (!validate(r, &asset->overlay) || !validate(r, &asset->rotationParams) ||
            !r.asset_field(&asset->unkMaterial, "WeaponDef.unkMaterial")) return false;
        if (!r.object(parent, "WeaponDef.parent")) return false;
        for (size_t i = 0; i < 2; ++i)
        {
            if (!r.string_field(&asset->accuracyGraphName[i], "WeaponDef.accuracyGraphName")) return false;
            std::remove_cv_t<std::remove_reference_t<decltype(parent->accuracyGraphKnotCount[0])>> parent_raw{};
            std::remove_cv_t<std::remove_reference_t<decltype(asset->originalAccuracyGraphKnotCount[0])>> original_raw{};
            size_t count, original_count;
            if (!r.load(&parent->accuracyGraphKnotCount[i], parent_raw, "WeaponDef.parentKnotCount") ||
                !r.load(&asset->originalAccuracyGraphKnotCount[i], original_raw, "WeaponDef.originalKnotCount") ||
                !r.count(parent_raw, count, "WeaponDef.parentKnotCount") ||
                !r.count(original_raw, original_count, "WeaponDef.originalKnotCount") || original_count < count)
                return r.fail("WeaponDef.originalKnotCountMismatch");
            if (!r.pointer_array(&asset->originalAccuracyGraphKnots[i], count, "WeaponDef.originalAccuracyGraphKnots",
                [&](const auto* value) { return r.scalar(value, "WeaponDef.originalAccuracyGraphKnots"); }, true)) return false;
        }
        return true;
    }
    // assets/weapondef.cpp: dump_NoteTrackToSoundEntry(NoteTrackToSoundEntry*), 3 exact macro fields.
    inline bool validate(Reader& r, const NoteTrackToSoundEntry* asset)
    {
        if (!r.object(asset, "NoteTrackToSoundEntry")) return false;
        if (!r.script_field(&asset->attachment, "NoteTrackToSoundEntry.attachment")) return false;
        if (!r.counted_array(&asset->notetrackSoundMapKeys, &asset->numSoundMappings, "NoteTrackToSoundEntry.notetrackSoundMapKeys", [&](const auto* value) { return r.script_field(value, "NoteTrackToSoundEntry.notetrackSoundMapKeys"); })) return false;
        if (!r.counted_array(&asset->notetrackSoundMapValues, &asset->numSoundMappings, "NoteTrackToSoundEntry.notetrackSoundMapValues", [&](const auto* value) { return r.script_field(value, "NoteTrackToSoundEntry.notetrackSoundMapValues"); })) return false;
        return true;
    }
    // assets/weapondef.cpp: dump_NoteTrackToSuitSoundEntry(NoteTrackToSuitSoundEntry*), 3 exact macro fields.
    inline bool validate(Reader& r, const NoteTrackToSuitSoundEntry* asset)
    {
        if (!r.object(asset, "NoteTrackToSuitSoundEntry")) return false;
        if (!r.scalar(&asset->suitAnimState, "NoteTrackToSuitSoundEntry.suitAnimState")) return false;
        if (!r.counted_array(&asset->notetrackSoundMapKeys, &asset->numSoundMappings, "NoteTrackToSuitSoundEntry.notetrackSoundMapKeys", [&](const auto* value) { return r.script_field(value, "NoteTrackToSuitSoundEntry.notetrackSoundMapKeys"); })) return false;
        if (!r.counted_array(&asset->notetrackSoundMapValues, &asset->numSoundMappings, "NoteTrackToSuitSoundEntry.notetrackSoundMapValues", [&](const auto* value) { return r.script_field(value, "NoteTrackToSuitSoundEntry.notetrackSoundMapValues"); })) return false;
        return true;
    }
    // assets/weapondef.cpp: dump_complete(WeaponCompleteDef*), 36 exact macro fields.
    inline bool validate(Reader& r, const WeaponCompleteDef* asset)
    {
        if (!r.object(asset, "WeaponCompleteDef")) return false;
        if (!r.string_field(&asset->szInternalName, "WeaponCompleteDef.szInternalName")) return false;
        if (!r.string_field(&asset->szDisplayName, "WeaponCompleteDef.szDisplayName")) return false;
        if (!r.string_field(&asset->szLootTable, "WeaponCompleteDef.szLootTable")) return false;
        if (!r.pointer_array(&asset->hideTags, 32, "WeaponCompleteDef.hideTags", [&](const auto* value) { return r.script_field(value, "WeaponCompleteDef.hideTags"); })) return false;
        if (!r.counted_array(&asset->attachments, &asset->numAttachments, "WeaponCompleteDef.attachments", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments"); })) return false;
        if (!r.counted_array(&asset->attachments2, &asset->numAttachments2, "WeaponCompleteDef.attachments2", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments2"); })) return false;
        if (!r.counted_array(&asset->attachments3, &asset->numAttachments3, "WeaponCompleteDef.attachments3", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments3"); })) return false;
        if (!r.counted_array(&asset->attachments4, &asset->numAttachments4, "WeaponCompleteDef.attachments4", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments4"); })) return false;
        if (!r.counted_array(&asset->attachments5, &asset->numAttachments5, "WeaponCompleteDef.attachments5", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments5"); })) return false;
        if (!r.counted_array(&asset->attachments6, &asset->numAttachments6, "WeaponCompleteDef.attachments6", [&](const auto* value) { return r.asset_field(value, "WeaponCompleteDef.attachments6"); })) return false;
        if (!r.counted_array(&asset->notetrackSoundMapKeys, &asset->numNotetrackSoundMappings, "WeaponCompleteDef.notetrackSoundMapKeys", [&](const auto* value) { return r.script_field(value, "WeaponCompleteDef.notetrackSoundMapKeys"); })) return false;
        if (!r.counted_array(&asset->notetrackSoundMapValues, &asset->numNotetrackSoundMappings, "WeaponCompleteDef.notetrackSoundMapValues", [&](const auto* value) { return r.script_field(value, "WeaponCompleteDef.notetrackSoundMapValues"); })) return false;
        if (!r.scalar(&asset->fAdsZoomFov, "WeaponCompleteDef.fAdsZoomFov")) return false;
        if (!r.scalar(&asset->iAdsTransInTime, "WeaponCompleteDef.iAdsTransInTime")) return false;
        if (!r.scalar(&asset->iAdsTransOutTime, "WeaponCompleteDef.iAdsTransOutTime")) return false;
        if (!r.scalar(&asset->iClipSize, "WeaponCompleteDef.iClipSize")) return false;
        if (!r.scalar(&asset->vfxImpactType, "WeaponCompleteDef.vfxImpactType")) return false;
        if (!r.scalar(&asset->sfxImpactType, "WeaponCompleteDef.sfxImpactType")) return false;
        if (!r.scalar(&asset->meleeImpactType, "WeaponCompleteDef.meleeImpactType")) return false;
        if (!r.scalar(&asset->penetrateMultiplier, "WeaponCompleteDef.penetrateMultiplier")) return false;
        if (!r.scalar(&asset->fAdsViewKickCenterSpeed, "WeaponCompleteDef.fAdsViewKickCenterSpeed")) return false;
        if (!r.scalar(&asset->fHipViewKickCenterSpeed, "WeaponCompleteDef.fHipViewKickCenterSpeed")) return false;
        if (!r.string_field(&asset->szAltWeaponName, "WeaponCompleteDef.szAltWeaponName")) return false;
        if (!r.asset_field(&asset->killIcon, "WeaponCompleteDef.killIcon")) return false;
        if (!r.asset_field(&asset->dpadIcon, "WeaponCompleteDef.dpadIcon")) return false;
        if (!r.scalar(&asset->ammoDropStockMax, "WeaponCompleteDef.ammoDropStockMax")) return false;
        if (!r.scalar(&asset->adsDofStart, "WeaponCompleteDef.adsDofStart")) return false;
        if (!r.scalar(&asset->adsDofEnd, "WeaponCompleteDef.adsDofEnd")) return false;
        if (!r.scalar(&asset->motionTracker, "WeaponCompleteDef.motionTracker")) return false;
        if (!r.scalar(&asset->enhanced, "WeaponCompleteDef.enhanced")) return false;
        if (!r.scalar(&asset->dpadIconShowsAmmo, "WeaponCompleteDef.dpadIconShowsAmmo")) return false;
        if (!r.scalar(&asset->luiWeaponInfoWidgetUsesScopeStencil, "WeaponCompleteDef.luiWeaponInfoWidgetUsesScopeStencil")) return false;
        if (!r.string_field(&asset->szAdsrBaseSetting, "WeaponCompleteDef.szAdsrBaseSetting")) return false;
        if (!r.string_field(&asset->szLUIWeaponInfoWidgetName, "WeaponCompleteDef.szLUIWeaponInfoWidgetName")) return false;
        if (!r.string_field(&asset->szLUIWeaponInfoWidgetTag, "WeaponCompleteDef.szLUIWeaponInfoWidgetTag")) return false;
        if (!r.string_field(&asset->szLUICrosshairWidget, "WeaponCompleteDef.szLUICrosshairWidget")) return false;
        WeaponDef* definition;
        if (!r.load(&asset->weapDef, definition, "WeaponCompleteDef.weapDef") || !validate(r, definition, asset)) return false;
        if (!r.counted_array(&asset->notetrackOverrides, &asset->numNotetrackOverrides, "WeaponCompleteDef.notetrackOverrides",
            [&](const auto* value) { return validate(r, value); }) ||
            !r.counted_array(&asset->notetrackSuitEntries, &asset->numNotetrackSuitEntries, "WeaponCompleteDef.notetrackSuitEntries",
            [&](const auto* value) { return validate(r, value); })) return false;
        for (size_t i = 0; i < 2; ++i)
        {
            std::remove_cv_t<std::remove_reference_t<decltype(asset->accuracyGraphKnotCount[0])>> raw{};
            size_t count;
            if (!r.load(&asset->accuracyGraphKnotCount[i], raw, "WeaponCompleteDef.accuracyGraphKnotCount") ||
                !r.count(raw, count, "WeaponCompleteDef.accuracyGraphKnotCount") ||
                !r.pointer_array(&asset->accuracyGraphKnots[i], count, "WeaponCompleteDef.accuracyGraphKnots",
                    [&](const auto* value) { return r.scalar(value, "WeaponCompleteDef.accuracyGraphKnots"); })) return false;
        }
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttAmmoGeneral*), 5 exact macro fields.
    inline bool validate(Reader& r, const AttAmmoGeneral* asset)
    {
        if (!r.object(asset, "AttAmmoGeneral")) return false;
        if (!r.scalar(&asset->vfxImpactType, "AttAmmoGeneral.vfxImpactType")) return false;
        if (!r.scalar(&asset->sfxImpactType, "AttAmmoGeneral.sfxImpactType")) return false;
        if (!r.scalar(&asset->meleeImpactType, "AttAmmoGeneral.meleeImpactType")) return false;
        if (!r.scalar(&asset->fireType, "AttAmmoGeneral.fireType")) return false;
        if (!r.scalar(&asset->burstCount, "AttAmmoGeneral.burstCount")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttAmmoTracer*), 2 exact macro fields.
    inline bool validate(Reader& r, const AttAmmoTracer* asset)
    {
        if (!r.object(asset, "AttAmmoTracer")) return false;
        if (!r.asset_field(&asset->tracerType, "AttAmmoTracer.tracerType")) return false;
        if (!r.scalar(&asset->tracerStyle, "AttAmmoTracer.tracerStyle")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttPenetration*), 5 exact macro fields.
    inline bool validate(Reader& r, const AttPenetration* asset)
    {
        if (!r.object(asset, "AttPenetration")) return false;
        if (!r.scalar(&asset->penetrateType, "AttPenetration.penetrateType")) return false;
        if (!r.scalar(&asset->penetrateMultiplier, "AttPenetration.penetrateMultiplier")) return false;
        if (!r.scalar(&asset->rifleBullet, "AttPenetration.rifleBullet")) return false;
        if (!r.scalar(&asset->armorPiercing, "AttPenetration.armorPiercing")) return false;
        if (!r.scalar(&asset->impaling, "AttPenetration.impaling")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttSight*), 11 exact macro fields.
    inline bool validate(Reader& r, const AttSight* asset)
    {
        if (!r.object(asset, "AttSight")) return false;
        if (!r.scalar(&asset->blurSceneAdsInFraction, "AttSight.blurSceneAdsInFraction")) return false;
        if (!r.scalar(&asset->blurSceneAdsOutFraction, "AttSight.blurSceneAdsOutFraction")) return false;
        if (!r.scalar(&asset->aimDownSight, "AttSight.aimDownSight")) return false;
        if (!r.scalar(&asset->adsFire, "AttSight.adsFire")) return false;
        if (!r.scalar(&asset->rechamberWhileAds, "AttSight.rechamberWhileAds")) return false;
        if (!r.scalar(&asset->noAdsWhenMagEmpty, "AttSight.noAdsWhenMagEmpty")) return false;
        if (!r.scalar(&asset->canVariableZoom, "AttSight.canVariableZoom")) return false;
        if (!r.scalar(&asset->hideRailWithThisScope, "AttSight.hideRailWithThisScope")) return false;
        if (!r.scalar(&asset->forceIronSightDown, "AttSight.forceIronSightDown")) return false;
        if (!r.scalar(&asset->useScopeDrift, "AttSight.useScopeDrift")) return false;
        if (!r.scalar(&asset->useDualFOV, "AttSight.useDualFOV")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttHoldBreath*), 1 exact macro fields.
    inline bool validate(Reader& r, const AttHoldBreath* asset)
    {
        if (!r.object(asset, "AttHoldBreath")) return false;
        if (!r.scalar(&asset->canHoldBreath, "AttHoldBreath.canHoldBreath")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttReload*), 3 exact macro fields.
    inline bool validate(Reader& r, const AttReload* asset)
    {
        if (!r.object(asset, "AttReload")) return false;
        if (!r.scalar(&asset->noPartialReload, "AttReload.noPartialReload")) return false;
        if (!r.scalar(&asset->segmentedReload, "AttReload.segmentedReload")) return false;
        if (!r.scalar(&asset->reloadDisabled, "AttReload.reloadDisabled")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttAddOns*), 3 exact macro fields.
    inline bool validate(Reader& r, const AttAddOns* asset)
    {
        if (!r.object(asset, "AttAddOns")) return false;
        if (!r.scalar(&asset->motionTracker, "AttAddOns.motionTracker")) return false;
        if (!r.scalar(&asset->silenced, "AttAddOns.silenced")) return false;
        if (!r.scalar(&asset->riotShield, "AttAddOns.riotShield")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttGeneral*), 12 exact macro fields.
    inline bool validate(Reader& r, const AttGeneral* asset)
    {
        if (!r.object(asset, "AttGeneral")) return false;
        if (!r.scalar(&asset->boltAction, "AttGeneral.boltAction")) return false;
        if (!r.scalar(&asset->inheritsPerks, "AttGeneral.inheritsPerks")) return false;
        if (!r.scalar(&asset->reticleSpin45, "AttGeneral.reticleSpin45")) return false;
        if (!r.scalar(&asset->adsShouldShowCrosshair, "AttGeneral.adsShouldShowCrosshair")) return false;
        if (!r.scalar(&asset->enemyCrosshairRange, "AttGeneral.enemyCrosshairRange")) return false;
        if (!r.scalar(&asset->reticleType, "AttGeneral.reticleType")) return false;
        if (!r.asset_field(&asset->reticleCenter, "AttGeneral.reticleCenter")) return false;
        if (!r.asset_field(&asset->reticleSide, "AttGeneral.reticleSide")) return false;
        if (!r.asset_field(&asset->reticleOnePiece, "AttGeneral.reticleOnePiece")) return false;
        if (!r.scalar(&asset->reticleCenterSize, "AttGeneral.reticleCenterSize")) return false;
        if (!r.scalar(&asset->reticleSideSize, "AttGeneral.reticleSideSize")) return false;
        if (!r.string_field(&asset->szLUICrosshairWidget, "AttGeneral.szLUICrosshairWidget")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttLaser*), 3 exact macro fields.
    inline bool validate(Reader& r, const AttLaser* asset)
    {
        if (!r.object(asset, "AttLaser")) return false;
        if (!r.asset_field(&asset->laserTypeFriendly, "AttLaser.laserTypeFriendly")) return false;
        if (!r.asset_field(&asset->laserTypeEnemy, "AttLaser.laserTypeEnemy")) return false;
        if (!r.scalar(&asset->forceLaserOn, "AttLaser.forceLaserOn")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttAimAssist*), 8 exact macro fields.
    inline bool validate(Reader& r, const AttAimAssist* asset)
    {
        if (!r.object(asset, "AttAimAssist")) return false;
        if (!r.scalar(&asset->autoAimRange, "AttAimAssist.autoAimRange")) return false;
        if (!r.scalar(&asset->aimAssistRange, "AttAimAssist.aimAssistRange")) return false;
        if (!r.scalar(&asset->aimAssistRangeAds, "AttAimAssist.aimAssistRangeAds")) return false;
        if (!r.scalar(&asset->aimAssistPitchSlowdown, "AttAimAssist.aimAssistPitchSlowdown")) return false;
        if (!r.scalar(&asset->aimAssistPitchSlowdownAds, "AttAimAssist.aimAssistPitchSlowdownAds")) return false;
        if (!r.scalar(&asset->aimAssistYawSlowdown, "AttAimAssist.aimAssistYawSlowdown")) return false;
        if (!r.scalar(&asset->aimAssistYawSlowdownAds, "AttAimAssist.aimAssistYawSlowdownAds")) return false;
        if (!r.scalar(&asset->aimAssistLockonStrength, "AttAimAssist.aimAssistLockonStrength")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttTargetAssist*), 8 exact macro fields.
    inline bool validate(Reader& r, const AttTargetAssist* asset)
    {
        if (!r.object(asset, "AttTargetAssist")) return false;
        if (!r.scalar(&asset->targetAssistType, "AttTargetAssist.targetAssistType")) return false;
        if (!r.scalar(&asset->targetAssistBehavior, "AttTargetAssist.targetAssistBehavior")) return false;
        if (!r.scalar(&asset->targetAssistRange, "AttTargetAssist.targetAssistRange")) return false;
        if (!r.scalar(&asset->targetAssistAngle, "AttTargetAssist.targetAssistAngle")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetForward, "AttTargetAssist.targetAssistLosOffsetForward")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetRight, "AttTargetAssist.targetAssistLosOffsetRight")) return false;
        if (!r.scalar(&asset->targetAssistLosOffsetUp, "AttTargetAssist.targetAssistLosOffsetUp")) return false;
        if (!r.scalar(&asset->targetAssistOnlyAvailableInAds, "AttTargetAssist.targetAssistOnlyAvailableInAds")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttUnknown01*), 50 exact macro fields.
    inline bool validate(Reader& r, const AttUnknown01* asset)
    {
        if (!r.object(asset, "AttUnknown01")) return false;
        if (!r.asset_field(&asset->material, "AttUnknown01.material")) return false;
        if (!r.scalar(&asset->unk_0, "AttUnknown01.unk_0")) return false;
        if (!r.scalar(&asset->unk_1, "AttUnknown01.unk_1")) return false;
        if (!r.scalar(&asset->unk_2, "AttUnknown01.unk_2")) return false;
        if (!r.scalar(&asset->unk_3, "AttUnknown01.unk_3")) return false;
        if (!r.scalar(&asset->unk_4, "AttUnknown01.unk_4")) return false;
        if (!r.scalar(&asset->unk_5, "AttUnknown01.unk_5")) return false;
        if (!r.scalar(&asset->unk_6, "AttUnknown01.unk_6")) return false;
        if (!r.scalar(&asset->unk_7, "AttUnknown01.unk_7")) return false;
        if (!r.scalar(&asset->unk_8, "AttUnknown01.unk_8")) return false;
        if (!r.scalar(&asset->unk_9, "AttUnknown01.unk_9")) return false;
        if (!r.scalar(&asset->unk_10, "AttUnknown01.unk_10")) return false;
        if (!r.scalar(&asset->unk_11, "AttUnknown01.unk_11")) return false;
        if (!r.scalar(&asset->unk_12, "AttUnknown01.unk_12")) return false;
        if (!r.scalar(&asset->unk_13, "AttUnknown01.unk_13")) return false;
        if (!r.scalar(&asset->unk_14, "AttUnknown01.unk_14")) return false;
        if (!r.scalar(&asset->unk_15, "AttUnknown01.unk_15")) return false;
        if (!r.scalar(&asset->unk_16, "AttUnknown01.unk_16")) return false;
        if (!r.scalar(&asset->unk_17, "AttUnknown01.unk_17")) return false;
        if (!r.scalar(&asset->unk_18, "AttUnknown01.unk_18")) return false;
        if (!r.scalar(&asset->unk_19, "AttUnknown01.unk_19")) return false;
        if (!r.scalar(&asset->unk_20, "AttUnknown01.unk_20")) return false;
        if (!r.scalar(&asset->unk_21, "AttUnknown01.unk_21")) return false;
        if (!r.scalar(&asset->unk_22, "AttUnknown01.unk_22")) return false;
        if (!r.scalar(&asset->unk_23, "AttUnknown01.unk_23")) return false;
        if (!r.scalar(&asset->unk_24, "AttUnknown01.unk_24")) return false;
        if (!r.scalar(&asset->unk_25, "AttUnknown01.unk_25")) return false;
        if (!r.scalar(&asset->unk_26, "AttUnknown01.unk_26")) return false;
        if (!r.scalar(&asset->unk_27, "AttUnknown01.unk_27")) return false;
        if (!r.scalar(&asset->unk_28, "AttUnknown01.unk_28")) return false;
        if (!r.scalar(&asset->unk_29, "AttUnknown01.unk_29")) return false;
        if (!r.scalar(&asset->unk_30, "AttUnknown01.unk_30")) return false;
        if (!r.scalar(&asset->unk_31, "AttUnknown01.unk_31")) return false;
        if (!r.scalar(&asset->unk_32, "AttUnknown01.unk_32")) return false;
        if (!r.scalar(&asset->unk_33, "AttUnknown01.unk_33")) return false;
        if (!r.scalar(&asset->unk_34, "AttUnknown01.unk_34")) return false;
        if (!r.scalar(&asset->unk_35, "AttUnknown01.unk_35")) return false;
        if (!r.scalar(&asset->unk_36, "AttUnknown01.unk_36")) return false;
        if (!r.scalar(&asset->unk_37, "AttUnknown01.unk_37")) return false;
        if (!r.scalar(&asset->unk_38, "AttUnknown01.unk_38")) return false;
        if (!r.scalar(&asset->unk_39, "AttUnknown01.unk_39")) return false;
        if (!r.scalar(&asset->unk_40, "AttUnknown01.unk_40")) return false;
        if (!r.scalar(&asset->unk_41, "AttUnknown01.unk_41")) return false;
        if (!r.scalar(&asset->unk_42, "AttUnknown01.unk_42")) return false;
        if (!r.scalar(&asset->unk_43, "AttUnknown01.unk_43")) return false;
        if (!r.scalar(&asset->unk_44, "AttUnknown01.unk_44")) return false;
        if (!r.scalar(&asset->unk_45, "AttUnknown01.unk_45")) return false;
        if (!r.scalar(&asset->unk_46, "AttUnknown01.unk_46")) return false;
        if (!r.scalar(&asset->unk_47, "AttUnknown01.unk_47")) return false;
        if (!r.scalar(&asset->unk_48, "AttUnknown01.unk_48")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttAmmunition*), 7 exact macro fields.
    inline bool validate(Reader& r, const AttAmmunition* asset)
    {
        if (!r.object(asset, "AttAmmunition")) return false;
        if (!r.scalar(&asset->maxAmmo, "AttAmmunition.maxAmmo")) return false;
        if (!r.scalar(&asset->startAmmo, "AttAmmunition.startAmmo")) return false;
        if (!r.scalar(&asset->clipSize, "AttAmmunition.clipSize")) return false;
        if (!r.scalar(&asset->shotCount, "AttAmmunition.shotCount")) return false;
        if (!r.scalar(&asset->reloadAmmoAdd, "AttAmmunition.reloadAmmoAdd")) return false;
        if (!r.scalar(&asset->reloadStartAdd, "AttAmmunition.reloadStartAdd")) return false;
        if (!r.scalar(&asset->requireAmmoUsedPerShot, "AttAmmunition.requireAmmoUsedPerShot")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttDamage*), 16 exact macro fields.
    inline bool validate(Reader& r, const AttDamage* asset)
    {
        if (!r.object(asset, "AttDamage")) return false;
        if (!r.scalar(&asset->damage, "AttDamage.damage")) return false;
        if (!r.scalar(&asset->mid1Damage, "AttDamage.mid1Damage")) return false;
        if (!r.scalar(&asset->mid2Damage, "AttDamage.mid2Damage")) return false;
        if (!r.scalar(&asset->mid3Damage, "AttDamage.mid3Damage")) return false;
        if (!r.scalar(&asset->minDamage, "AttDamage.minDamage")) return false;
        if (!r.scalar(&asset->meleeDamage, "AttDamage.meleeDamage")) return false;
        if (!r.scalar(&asset->maxDamageRange, "AttDamage.maxDamageRange")) return false;
        if (!r.scalar(&asset->mid1DamageRange, "AttDamage.mid1DamageRange")) return false;
        if (!r.scalar(&asset->mid2DamageRange, "AttDamage.mid2DamageRange")) return false;
        if (!r.scalar(&asset->mid3DamageRange, "AttDamage.mid3DamageRange")) return false;
        if (!r.scalar(&asset->minDamageRange, "AttDamage.minDamageRange")) return false;
        if (!r.scalar(&asset->playerDamage, "AttDamage.playerDamage")) return false;
        if (!r.scalar(&asset->mid1PlayerDamage, "AttDamage.mid1PlayerDamage")) return false;
        if (!r.scalar(&asset->mid2PlayerDamage, "AttDamage.mid2PlayerDamage")) return false;
        if (!r.scalar(&asset->mid3PlayerDamage, "AttDamage.mid3PlayerDamage")) return false;
        if (!r.scalar(&asset->minPlayerDamage, "AttDamage.minPlayerDamage")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttIdleSettings*), 6 exact macro fields.
    inline bool validate(Reader& r, const AttIdleSettings* asset)
    {
        if (!r.object(asset, "AttIdleSettings")) return false;
        if (!r.scalar(&asset->hipIdleAmount, "AttIdleSettings.hipIdleAmount")) return false;
        if (!r.scalar(&asset->hipIdleSpeed, "AttIdleSettings.hipIdleSpeed")) return false;
        if (!r.scalar(&asset->idleCrouchFactor, "AttIdleSettings.idleCrouchFactor")) return false;
        if (!r.scalar(&asset->idleProneFactor, "AttIdleSettings.idleProneFactor")) return false;
        if (!r.scalar(&asset->adsIdleLerpStartTime, "AttIdleSettings.adsIdleLerpStartTime")) return false;
        if (!r.scalar(&asset->adsIdleLerpTime, "AttIdleSettings.adsIdleLerpTime")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttADSSettings*), 24 exact macro fields.
    inline bool validate(Reader& r, const AttADSSettings* asset)
    {
        if (!r.object(asset, "AttADSSettings")) return false;
        if (!r.scalar(&asset->adsSpread, "AttADSSettings.adsSpread")) return false;
        if (!r.scalar(&asset->adsAimPitch, "AttADSSettings.adsAimPitch")) return false;
        if (!r.scalar(&asset->adsTransInTime, "AttADSSettings.adsTransInTime")) return false;
        if (!r.scalar(&asset->adsTransOutTime, "AttADSSettings.adsTransOutTime")) return false;
        if (!r.scalar(&asset->adsReloadTransTime, "AttADSSettings.adsReloadTransTime")) return false;
        if (!r.scalar(&asset->adsCrosshairInFrac, "AttADSSettings.adsCrosshairInFrac")) return false;
        if (!r.scalar(&asset->adsCrosshairOutFrac, "AttADSSettings.adsCrosshairOutFrac")) return false;
        if (!r.scalar(&asset->adsInCrosshairAlphaStart, "AttADSSettings.adsInCrosshairAlphaStart")) return false;
        if (!r.scalar(&asset->adsInCrosshairAlphaEnd, "AttADSSettings.adsInCrosshairAlphaEnd")) return false;
        if (!r.scalar(&asset->adsOutCrosshairAlphaStart, "AttADSSettings.adsOutCrosshairAlphaStart")) return false;
        if (!r.scalar(&asset->adsOutCrosshairAlphaEnd, "AttADSSettings.adsOutCrosshairAlphaEnd")) return false;
        if (!r.scalar(&asset->adsZoomFov, "AttADSSettings.adsZoomFov")) return false;
        if (!r.scalar(&asset->adsZoomInFrac, "AttADSSettings.adsZoomInFrac")) return false;
        if (!r.scalar(&asset->adsZoomOutFrac, "AttADSSettings.adsZoomOutFrac")) return false;
        if (!r.scalar(&asset->adsFovLerpTime, "AttADSSettings.adsFovLerpTime")) return false;
        if (!r.scalar(&asset->adsBobFactor, "AttADSSettings.adsBobFactor")) return false;
        if (!r.scalar(&asset->adsViewBobMult, "AttADSSettings.adsViewBobMult")) return false;
        if (!r.scalar(&asset->adsFireRateScale, "AttADSSettings.adsFireRateScale")) return false;
        if (!r.scalar(&asset->adsDamageRangeScale, "AttADSSettings.adsDamageRangeScale")) return false;
        if (!r.scalar(&asset->adsFireAnimFrac, "AttADSSettings.adsFireAnimFrac")) return false;
        if (!r.scalar(&asset->fireTimerLerpToAdsScale, "AttADSSettings.fireTimerLerpToAdsScale")) return false;
        if (!r.scalar(&asset->alwaysFireAtMaxRangeInAds, "AttADSSettings.alwaysFireAtMaxRangeInAds")) return false;
        if (!r.scalar(&asset->adsAlignEnabled, "AttADSSettings.adsAlignEnabled")) return false;
        if (!r.scalar(&asset->disableTagAlignX, "AttADSSettings.disableTagAlignX")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttScopeDriftSettings*), 6 exact macro fields.
    inline bool validate(Reader& r, const AttScopeDriftSettings* asset)
    {
        if (!r.object(asset, "AttScopeDriftSettings")) return false;
        if (!r.scalar(&asset->fScopeDriftDelay, "AttScopeDriftSettings.fScopeDriftDelay")) return false;
        if (!r.scalar(&asset->fScopeDriftLerpInTime, "AttScopeDriftSettings.fScopeDriftLerpInTime")) return false;
        if (!r.scalar(&asset->fScopeDriftSteadyTime, "AttScopeDriftSettings.fScopeDriftSteadyTime")) return false;
        if (!r.scalar(&asset->fScopeDriftLerpOutTime, "AttScopeDriftSettings.fScopeDriftLerpOutTime")) return false;
        if (!r.scalar(&asset->fScopeDriftSteadyFactor, "AttScopeDriftSettings.fScopeDriftSteadyFactor")) return false;
        if (!r.scalar(&asset->fScopeDriftUnsteadyFactor, "AttScopeDriftSettings.fScopeDriftUnsteadyFactor")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttHipSpread*), 18 exact macro fields.
    inline bool validate(Reader& r, const AttHipSpread* asset)
    {
        if (!r.object(asset, "AttHipSpread")) return false;
        if (!r.scalar(&asset->hipSpreadStandMin, "AttHipSpread.hipSpreadStandMin")) return false;
        if (!r.scalar(&asset->hipSpreadDuckedMin, "AttHipSpread.hipSpreadDuckedMin")) return false;
        if (!r.scalar(&asset->hipSpreadProneMin, "AttHipSpread.hipSpreadProneMin")) return false;
        if (!r.scalar(&asset->hipSpreadSprintMin, "AttHipSpread.hipSpreadSprintMin")) return false;
        if (!r.scalar(&asset->hipSpreadInAirMin, "AttHipSpread.hipSpreadInAirMin")) return false;
        if (!r.scalar(&asset->hipSpreadMax, "AttHipSpread.hipSpreadMax")) return false;
        if (!r.scalar(&asset->hipSpreadDuckedMax, "AttHipSpread.hipSpreadDuckedMax")) return false;
        if (!r.scalar(&asset->hipSpreadProneMax, "AttHipSpread.hipSpreadProneMax")) return false;
        if (!r.scalar(&asset->hipSpreadSprintMax, "AttHipSpread.hipSpreadSprintMax")) return false;
        if (!r.scalar(&asset->hipSpreadInAirMax, "AttHipSpread.hipSpreadInAirMax")) return false;
        if (!r.scalar(&asset->hipSpreadFireAdd, "AttHipSpread.hipSpreadFireAdd")) return false;
        if (!r.scalar(&asset->hipSpreadTurnAdd, "AttHipSpread.hipSpreadTurnAdd")) return false;
        if (!r.scalar(&asset->hipSpreadMoveAdd, "AttHipSpread.hipSpreadMoveAdd")) return false;
        if (!r.scalar(&asset->hipSpreadDecayRate, "AttHipSpread.hipSpreadDecayRate")) return false;
        if (!r.scalar(&asset->hipSpreadDuckedDecay, "AttHipSpread.hipSpreadDuckedDecay")) return false;
        if (!r.scalar(&asset->hipSpreadProneDecay, "AttHipSpread.hipSpreadProneDecay")) return false;
        if (!r.scalar(&asset->hipSpreadSprintDecay, "AttHipSpread.hipSpreadSprintDecay")) return false;
        if (!r.scalar(&asset->hipSpreadInAirDecay, "AttHipSpread.hipSpreadInAirDecay")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttSlideSpread*), 5 exact macro fields.
    inline bool validate(Reader& r, const AttSlideSpread* asset)
    {
        if (!r.object(asset, "AttSlideSpread")) return false;
        if (!r.scalar(&asset->slideSpreadMin, "AttSlideSpread.slideSpreadMin")) return false;
        if (!r.scalar(&asset->slideSpreadMax, "AttSlideSpread.slideSpreadMax")) return false;
        if (!r.scalar(&asset->slideSpreadDecayRate, "AttSlideSpread.slideSpreadDecayRate")) return false;
        if (!r.scalar(&asset->slideSpreadFireAdd, "AttSlideSpread.slideSpreadFireAdd")) return false;
        if (!r.scalar(&asset->slideSpreadTurnAdd, "AttSlideSpread.slideSpreadTurnAdd")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttGunKick*), 22 exact macro fields.
    inline bool validate(Reader& r, const AttGunKick* asset)
    {
        if (!r.object(asset, "AttGunKick")) return false;
        if (!r.scalar(&asset->hipGunKickReducedKickBullets, "AttGunKick.hipGunKickReducedKickBullets")) return false;
        if (!r.scalar(&asset->hipGunKickReducedKickPercent, "AttGunKick.hipGunKickReducedKickPercent")) return false;
        if (!r.scalar(&asset->hipGunKickPitchMin, "AttGunKick.hipGunKickPitchMin")) return false;
        if (!r.scalar(&asset->hipGunKickPitchMax, "AttGunKick.hipGunKickPitchMax")) return false;
        if (!r.scalar(&asset->hipGunKickYawMin, "AttGunKick.hipGunKickYawMin")) return false;
        if (!r.scalar(&asset->hipGunKickYawMax, "AttGunKick.hipGunKickYawMax")) return false;
        if (!r.scalar(&asset->hipGunKickMagMin, "AttGunKick.hipGunKickMagMin")) return false;
        if (!r.scalar(&asset->hipGunKickAccel, "AttGunKick.hipGunKickAccel")) return false;
        if (!r.scalar(&asset->hipGunKickSpeedMax, "AttGunKick.hipGunKickSpeedMax")) return false;
        if (!r.scalar(&asset->hipGunKickSpeedDecay, "AttGunKick.hipGunKickSpeedDecay")) return false;
        if (!r.scalar(&asset->hipGunKickStaticDecay, "AttGunKick.hipGunKickStaticDecay")) return false;
        if (!r.scalar(&asset->adsGunKickReducedKickBullets, "AttGunKick.adsGunKickReducedKickBullets")) return false;
        if (!r.scalar(&asset->adsGunKickReducedKickPercent, "AttGunKick.adsGunKickReducedKickPercent")) return false;
        if (!r.scalar(&asset->adsGunKickPitchMin, "AttGunKick.adsGunKickPitchMin")) return false;
        if (!r.scalar(&asset->adsGunKickPitchMax, "AttGunKick.adsGunKickPitchMax")) return false;
        if (!r.scalar(&asset->adsGunKickYawMin, "AttGunKick.adsGunKickYawMin")) return false;
        if (!r.scalar(&asset->adsGunKickYawMax, "AttGunKick.adsGunKickYawMax")) return false;
        if (!r.scalar(&asset->adsGunKickMagMin, "AttGunKick.adsGunKickMagMin")) return false;
        if (!r.scalar(&asset->adsGunKickAccel, "AttGunKick.adsGunKickAccel")) return false;
        if (!r.scalar(&asset->adsGunKickSpeedMax, "AttGunKick.adsGunKickSpeedMax")) return false;
        if (!r.scalar(&asset->adsGunKickSpeedDecay, "AttGunKick.adsGunKickSpeedDecay")) return false;
        if (!r.scalar(&asset->adsGunKickStaticDecay, "AttGunKick.adsGunKickStaticDecay")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttViewKick*), 14 exact macro fields.
    inline bool validate(Reader& r, const AttViewKick* asset)
    {
        if (!r.object(asset, "AttViewKick")) return false;
        if (!r.scalar(&asset->hipViewKickPitchMin, "AttViewKick.hipViewKickPitchMin")) return false;
        if (!r.scalar(&asset->hipViewKickPitchMax, "AttViewKick.hipViewKickPitchMax")) return false;
        if (!r.scalar(&asset->hipViewKickYawMin, "AttViewKick.hipViewKickYawMin")) return false;
        if (!r.scalar(&asset->hipViewKickYawMax, "AttViewKick.hipViewKickYawMax")) return false;
        if (!r.scalar(&asset->hipViewKickMagMin, "AttViewKick.hipViewKickMagMin")) return false;
        if (!r.scalar(&asset->hipViewKickCenterSpeed, "AttViewKick.hipViewKickCenterSpeed")) return false;
        if (!r.scalar(&asset->adsViewKickPitchMin, "AttViewKick.adsViewKickPitchMin")) return false;
        if (!r.scalar(&asset->adsViewKickPitchMax, "AttViewKick.adsViewKickPitchMax")) return false;
        if (!r.scalar(&asset->adsViewKickYawMin, "AttViewKick.adsViewKickYawMin")) return false;
        if (!r.scalar(&asset->adsViewKickYawMax, "AttViewKick.adsViewKickYawMax")) return false;
        if (!r.scalar(&asset->adsViewKickMagMin, "AttViewKick.adsViewKickMagMin")) return false;
        if (!r.scalar(&asset->adsViewKickCenterSpeed, "AttViewKick.adsViewKickCenterSpeed")) return false;
        if (!r.scalar(&asset->kickAlignedInputScalar, "AttViewKick.kickAlignedInputScalar")) return false;
        if (!r.scalar(&asset->kickOpposedInputScalar, "AttViewKick.kickOpposedInputScalar")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttADSOverlay*), 13 exact macro fields.
    inline bool validate(Reader& r, const AttADSOverlay* asset)
    {
        if (!r.object(asset, "AttADSOverlay")) return false;
        if (!r.asset_field(&asset->overlay.shader, "AttADSOverlay.overlay.shader")) return false;
        if (!r.asset_field(&asset->overlay.shaderLowRes, "AttADSOverlay.overlay.shaderLowRes")) return false;
        if (!r.asset_field(&asset->overlay.shaderEMP, "AttADSOverlay.overlay.shaderEMP")) return false;
        if (!r.asset_field(&asset->overlay.shaderEMPLowRes, "AttADSOverlay.overlay.shaderEMPLowRes")) return false;
        if (!r.scalar(&asset->overlay.reticle, "AttADSOverlay.overlay.reticle")) return false;
        if (!r.scalar(&asset->overlay.width, "AttADSOverlay.overlay.width")) return false;
        if (!r.scalar(&asset->overlay.height, "AttADSOverlay.overlay.height")) return false;
        if (!r.scalar(&asset->overlay.widthSplitscreen, "AttADSOverlay.overlay.widthSplitscreen")) return false;
        if (!r.scalar(&asset->overlay.heightSplitscreen, "AttADSOverlay.overlay.heightSplitscreen")) return false;
        if (!r.scalar(&asset->hybridToggle, "AttADSOverlay.hybridToggle")) return false;
        if (!r.scalar(&asset->thermalScope, "AttADSOverlay.thermalScope")) return false;
        if (!r.scalar(&asset->thermalToggle, "AttADSOverlay.thermalToggle")) return false;
        if (!r.scalar(&asset->outlineEnemies, "AttADSOverlay.outlineEnemies")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttOutline*), 18 exact macro fields.
    inline bool validate(Reader& r, const AttOutline* asset)
    {
        if (!r.object(asset, "AttOutline")) return false;
        if (!r.fixed_scalars(&asset->outlineColor, 4, "AttOutline.outlineColor")) return false;
        if (!r.fixed_scalars(&asset->outlineAltColor, 4, "AttOutline.outlineAltColor")) return false;
        if (!r.fixed_scalars(&asset->outlineFillColor0, 4, "AttOutline.outlineFillColor0")) return false;
        if (!r.fixed_scalars(&asset->outlineFillColor1, 4, "AttOutline.outlineFillColor1")) return false;
        if (!r.fixed_scalars(&asset->outlineOccludedOutlineColor, 4, "AttOutline.outlineOccludedOutlineColor")) return false;
        if (!r.fixed_scalars(&asset->outlineOccludedInlineColor, 4, "AttOutline.outlineOccludedInlineColor")) return false;
        if (!r.fixed_scalars(&asset->outlineOccludedInteriorColor, 4, "AttOutline.outlineOccludedInteriorColor")) return false;
        if (!r.scalar(&asset->outlineWidth, "AttOutline.outlineWidth")) return false;
        if (!r.scalar(&asset->outlineEnemies, "AttOutline.outlineEnemies")) return false;
        if (!r.scalar(&asset->outlineDepthTest, "AttOutline.outlineDepthTest")) return false;
        if (!r.scalar(&asset->outlineFill, "AttOutline.outlineFill")) return false;
        if (!r.scalar(&asset->outlineScriptControlled, "AttOutline.outlineScriptControlled")) return false;
        if (!r.scalar(&asset->outlineVehicles, "AttOutline.outlineVehicles")) return false;
        if (!r.scalar(&asset->outlineTurrets, "AttOutline.outlineTurrets")) return false;
        if (!r.scalar(&asset->outlineCharacters, "AttOutline.outlineCharacters")) return false;
        if (!r.scalar(&asset->outlineAgents, "AttOutline.outlineAgents")) return false;
        if (!r.scalar(&asset->outlineScriptMovers, "AttOutline.outlineScriptMovers")) return false;
        if (!r.scalar(&asset->outlineLockOn, "AttOutline.outlineLockOn")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttUI*), 10 exact macro fields.
    inline bool validate(Reader& r, const AttUI* asset)
    {
        if (!r.object(asset, "AttUI")) return false;
        if (!r.asset_field(&asset->hudIcon, "AttUI.hudIcon")) return false;
        if (!r.asset_field(&asset->pickupIcon, "AttUI.pickupIcon")) return false;
        if (!r.asset_field(&asset->dangerIcon, "AttUI.dangerIcon")) return false;
        if (!r.asset_field(&asset->throwBackIcon, "AttUI.throwBackIcon")) return false;
        if (!r.scalar(&asset->hideWarningIcons, "AttUI.hideWarningIcons")) return false;
        if (!r.scalar(&asset->warningIconsDelay, "AttUI.warningIconsDelay")) return false;
        if (!r.asset_field(&asset->dpadIcon, "AttUI.dpadIcon")) return false;
        if (!r.asset_field(&asset->ammoCounterIcon, "AttUI.ammoCounterIcon")) return false;
        if (!r.scalar(&asset->ammoCounterClip, "AttUI.ammoCounterClip")) return false;
        if (!r.scalar(&asset->grenadeDangerIconDistance, "AttUI.grenadeDangerIconDistance")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttRumbles*), 2 exact macro fields.
    inline bool validate(Reader& r, const AttRumbles* asset)
    {
        if (!r.object(asset, "AttRumbles")) return false;
        if (!r.asset_field(&asset->fireRumble, "AttRumbles.fireRumble")) return false;
        if (!r.asset_field(&asset->meleeImpactRumble, "AttRumbles.meleeImpactRumble")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttProjectile*), 49 exact macro fields.
    inline bool validate(Reader& r, const AttProjectile* asset)
    {
        if (!r.object(asset, "AttProjectile")) return false;
        if (!r.scalar(&asset->explosionRadius, "AttProjectile.explosionRadius")) return false;
        if (!r.scalar(&asset->explosionForceRadius, "AttProjectile.explosionForceRadius")) return false;
        if (!r.scalar(&asset->explosionInnerDamage, "AttProjectile.explosionInnerDamage")) return false;
        if (!r.scalar(&asset->explosionOuterDamage, "AttProjectile.explosionOuterDamage")) return false;
        if (!r.scalar(&asset->damageConeAngle, "AttProjectile.damageConeAngle")) return false;
        if (!r.scalar(&asset->projectileSpeed, "AttProjectile.projectileSpeed")) return false;
        if (!r.scalar(&asset->projectileSpeedUp, "AttProjectile.projectileSpeedUp")) return false;
        if (!r.scalar(&asset->projectileActivateDist, "AttProjectile.projectileActivateDist")) return false;
        if (!r.scalar(&asset->projectileLifetime, "AttProjectile.projectileLifetime")) return false;
        if (!r.scalar(&asset->projectileLifetimeStdDeviation, "AttProjectile.projectileLifetimeStdDeviation")) return false;
        if (!r.asset_field(&asset->projectileModel, "AttProjectile.projectileModel")) return false;
        if (!r.scalar(&asset->projExplosionType, "AttProjectile.projExplosionType")) return false;
        if (!r.scalar(&asset->projExplosionEffect.type, "AttProjectile.projExplosionEffect.type")) return false;
        if (!r.asset_field(&asset->projExplosionEffect.u.fx, "AttProjectile.projExplosionEffect.u.fx")) return false;
        if (!r.scalar(&asset->projExplosionEffectForceNormalUp, "AttProjectile.projExplosionEffectForceNormalUp")) return false;
        if (!r.string_field(&asset->projExplosionSound, "AttProjectile.projExplosionSound")) return false;
        if (!r.scalar(&asset->projDudEffect.type, "AttProjectile.projDudEffect.type")) return false;
        if (!r.asset_field(&asset->projDudEffect.u.fx, "AttProjectile.projDudEffect.u.fx")) return false;
        if (!r.string_field(&asset->projDudSound, "AttProjectile.projDudSound")) return false;
        if (!r.scalar(&asset->projImpactExplode, "AttProjectile.projImpactExplode")) return false;
        if (!r.scalar(&asset->disableProjectileCrumpleCheck, "AttProjectile.disableProjectileCrumpleCheck")) return false;
        if (!r.scalar(&asset->destabilizationRateTime, "AttProjectile.destabilizationRateTime")) return false;
        if (!r.scalar(&asset->destabilizationCurvatureMax, "AttProjectile.destabilizationCurvatureMax")) return false;
        if (!r.scalar(&asset->destabilizeDistance, "AttProjectile.destabilizeDistance")) return false;
        if (!r.scalar(&asset->projBodyEffect.type, "AttProjectile.projBodyEffect.type")) return false;
        if (!r.asset_field(&asset->projBodyEffect.u.fx, "AttProjectile.projBodyEffect.u.fx")) return false;
        if (!r.scalar(&asset->projTrailEffect.type, "AttProjectile.projTrailEffect.type")) return false;
        if (!r.asset_field(&asset->projTrailEffect.u.fx, "AttProjectile.projTrailEffect.u.fx")) return false;
        if (!r.scalar(&asset->projBeaconEffect.type, "AttProjectile.projBeaconEffect.type")) return false;
        if (!r.asset_field(&asset->projBeaconEffect.u.fx, "AttProjectile.projBeaconEffect.u.fx")) return false;
        if (!r.scalar(&asset->projIgnitionDelay, "AttProjectile.projIgnitionDelay")) return false;
        if (!r.scalar(&asset->projIgnitionEffect.type, "AttProjectile.projIgnitionEffect.type")) return false;
        if (!r.asset_field(&asset->projIgnitionEffect.u.fx, "AttProjectile.projIgnitionEffect.u.fx")) return false;
        if (!r.string_field(&asset->projIgnitionSound, "AttProjectile.projIgnitionSound")) return false;
        if (!r.scalar(&asset->stickiness, "AttProjectile.stickiness")) return false;
        if (!r.scalar(&asset->fuseTime, "AttProjectile.fuseTime")) return false;
        if (!r.scalar(&asset->aiFuseTime, "AttProjectile.aiFuseTime")) return false;
        if (!r.scalar(&asset->stickToPlayers, "AttProjectile.stickToPlayers")) return false;
        if (!r.scalar(&asset->stickToVehicles, "AttProjectile.stickToVehicles")) return false;
        if (!r.scalar(&asset->stickToTurrets, "AttProjectile.stickToTurrets")) return false;
        if (!r.scalar(&asset->stickToNonStick, "AttProjectile.stickToNonStick")) return false;
        if (!r.scalar(&asset->timedDetonation, "AttProjectile.timedDetonation")) return false;
        if (!r.scalar(&asset->isPredictedProjectile, "AttProjectile.isPredictedProjectile")) return false;
        if (!r.scalar(&asset->useSteppedExplosionDamage, "AttProjectile.useSteppedExplosionDamage")) return false;
        if (!r.scalar(&asset->reactiveMotionRadiusScale, "AttProjectile.reactiveMotionRadiusScale")) return false;
        if (!r.scalar(&asset->reactiveMotionFrequencyScale, "AttProjectile.reactiveMotionFrequencyScale")) return false;
        if (!r.scalar(&asset->reactiveMotionAmplitudeScale, "AttProjectile.reactiveMotionAmplitudeScale")) return false;
        if (!r.scalar(&asset->reactiveMotionFalloff, "AttProjectile.reactiveMotionFalloff")) return false;
        if (!r.scalar(&asset->reactiveMotionLifetime, "AttProjectile.reactiveMotionLifetime")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttCharged*), 21 exact macro fields.
    inline bool validate(Reader& r, const AttCharged* asset)
    {
        if (!r.object(asset, "AttCharged")) return false;
        if (!r.scalar(&asset->chargeType, "AttCharged.chargeType")) return false;
        if (!r.scalar(&asset->chargeGain, "AttCharged.chargeGain")) return false;
        if (!r.scalar(&asset->chargeCostPerShot, "AttCharged.chargeCostPerShot")) return false;
        if (!r.scalar(&asset->chargeLossWhenIdle, "AttCharged.chargeLossWhenIdle")) return false;
        if (!r.scalar(&asset->chargeEmptyCooldown, "AttCharged.chargeEmptyCooldown")) return false;
        if (!r.scalar(&asset->chargeFireAtMaxDamageMultiplier, "AttCharged.chargeFireAtMaxDamageMultiplier")) return false;
        if (!r.scalar(&asset->chargeMeterEffectBoneCount, "AttCharged.chargeMeterEffectBoneCount")) return false;
        if (!r.scalar(&asset->chargeMeterEffect.type, "AttCharged.chargeMeterEffect.type")) return false;
        if (!r.asset_field(&asset->chargeMeterEffect.u.fx, "AttCharged.chargeMeterEffect.u.fx")) return false;
        if (!r.string_field(&asset->chargeUpSound, "AttCharged.chargeUpSound")) return false;
        if (!r.string_field(&asset->chargeDownSound, "AttCharged.chargeDownSound")) return false;
        if (!r.string_field(&asset->chargeDownToUpSound, "AttCharged.chargeDownToUpSound")) return false;
        if (!r.string_field(&asset->chargeUpToDownSound, "AttCharged.chargeUpToDownSound")) return false;
        if (!r.string_field(&asset->chargeMaxSound, "AttCharged.chargeMaxSound")) return false;
        if (!r.string_field(&asset->chargeUpSoundPlayer, "AttCharged.chargeUpSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeDownSoundPlayer, "AttCharged.chargeDownSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeDownToUpSoundPlayer, "AttCharged.chargeDownToUpSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeUpToDownSoundPlayer, "AttCharged.chargeUpToDownSoundPlayer")) return false;
        if (!r.string_field(&asset->chargeMaxSoundPlayer, "AttCharged.chargeMaxSoundPlayer")) return false;
        if (!r.scalar(&asset->chargeHudReveal, "AttCharged.chargeHudReveal")) return false;
        if (!r.asset_field(&asset->chargeRumble, "AttCharged.chargeRumble")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AdsAltSwitch*), 8 exact macro fields.
    inline bool validate(Reader& r, const AdsAltSwitch* asset)
    {
        if (!r.object(asset, "AdsAltSwitch")) return false;
        if (!r.scalar(&asset->fovInterpTimeSecMainToAlt, "AdsAltSwitch.fovInterpTimeSecMainToAlt")) return false;
        if (!r.scalar(&asset->fovInterpDelaySecMainToAlt, "AdsAltSwitch.fovInterpDelaySecMainToAlt")) return false;
        if (!r.scalar(&asset->dualFovSwitchRateMainToAlt, "AdsAltSwitch.dualFovSwitchRateMainToAlt")) return false;
        if (!r.scalar(&asset->fovInterpTypeMainToAlt, "AdsAltSwitch.fovInterpTypeMainToAlt")) return false;
        if (!r.scalar(&asset->fovInterpTimeSecAltToMain, "AdsAltSwitch.fovInterpTimeSecAltToMain")) return false;
        if (!r.scalar(&asset->fovInterpDelaySecAltToMain, "AdsAltSwitch.fovInterpDelaySecAltToMain")) return false;
        if (!r.scalar(&asset->dualFovSwitchRateAltToMain, "AdsAltSwitch.dualFovSwitchRateAltToMain")) return false;
        if (!r.scalar(&asset->fovInterpTypeAltToMain, "AdsAltSwitch.fovInterpTypeAltToMain")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttRegeneration*), 6 exact macro fields.
    inline bool validate(Reader& r, const AttRegeneration* asset)
    {
        if (!r.object(asset, "AttRegeneration")) return false;
        if (!r.scalar(&asset->regenerationEnabled, "AttRegeneration.regenerationEnabled")) return false;
        if (!r.scalar(&asset->regenerationTimeMs, "AttRegeneration.regenerationTimeMs")) return false;
        if (!r.scalar(&asset->regenerationAddTimeMs, "AttRegeneration.regenerationAddTimeMs")) return false;
        if (!r.scalar(&asset->regenerationAmount, "AttRegeneration.regenerationAmount")) return false;
        if (!r.scalar(&asset->regenerationConsumeStock, "AttRegeneration.regenerationConsumeStock")) return false;
        if (!r.scalar(&asset->regenerationDisableWhileFiring, "AttRegeneration.regenerationDisableWhileFiring")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttMovement*), 3 exact macro fields.
    inline bool validate(Reader& r, const AttMovement* asset)
    {
        if (!r.object(asset, "AttMovement")) return false;
        if (!r.scalar(&asset->moveSpeedScale, "AttMovement.moveSpeedScale")) return false;
        if (!r.scalar(&asset->adsMoveSpeedScale, "AttMovement.adsMoveSpeedScale")) return false;
        if (!r.scalar(&asset->fastADS3PAnims, "AttMovement.fastADS3PAnims")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump_att(AttBurst*), 2 exact macro fields.
    inline bool validate(Reader& r, const AttBurst* asset)
    {
        if (!r.object(asset, "AttBurst")) return false;
        if (!r.scalar(&asset->burstFireCooldown, "AttBurst.burstFireCooldown")) return false;
        if (!r.scalar(&asset->burstFireAuto, "AttBurst.burstFireAuto")) return false;
        return true;
    }
    // assets/weaponattachment.cpp: dump(WeaponAttachment*), 84 exact macro fields.
    inline bool validate(Reader& r, const WeaponAttachment* asset)
    {
        if (!r.object(asset, "WeaponAttachment")) return false;
        if (!r.string_field(&asset->szInternalName, "WeaponAttachment.szInternalName")) return false;
        if (!r.string_field(&asset->szDisplayName, "WeaponAttachment.szDisplayName")) return false;
        if (!r.scalar(&asset->papAttachment, "WeaponAttachment.papAttachment")) return false;
        if (!r.scalar(&asset->type, "WeaponAttachment.type")) return false;
        if (!r.scalar(&asset->weaponType, "WeaponAttachment.weaponType")) return false;
        if (!r.scalar(&asset->weapClass, "WeaponAttachment.weapClass")) return false;
        if (!r.asset_field(&asset->worldModelCamo, "WeaponAttachment.worldModelCamo")) return false;
        if (!r.asset_field(&asset->viewModelCamo, "WeaponAttachment.viewModelCamo")) return false;
        if (!r.counted_array(&asset->worldModelVariations, &asset->numModelVariations, "WeaponAttachment.worldModelVariations", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.worldModelVariations"); })) return false;
        if (!r.counted_array(&asset->viewModelVariations, &asset->numModelVariations, "WeaponAttachment.viewModelVariations", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.viewModelVariations"); })) return false;
        if (!r.counted_array(&asset->worldModelCamoMaterials, &asset->numWorldModelCamoMaterials, "WeaponAttachment.worldModelCamoMaterials", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.worldModelCamoMaterials"); })) return false;
        if (!r.counted_array(&asset->viewModelCamoMaterials, &asset->numViewModelCamoMaterials, "WeaponAttachment.viewModelCamoMaterials", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.viewModelCamoMaterials"); })) return false;
        if (!r.script_field(&asset->attachPoint, "WeaponAttachment.attachPoint")) return false;
        if (!r.counted_array(&asset->reticles, &asset->numReticles, "WeaponAttachment.reticles", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.reticles"); })) return false;
        if (!r.counted_array(&asset->altReticles, &asset->numAltReticles, "WeaponAttachment.altReticles", [&](const auto* value) { return r.asset_field(value, "WeaponAttachment.altReticles"); })) return false;
        if (!optional(r, &asset->ammogeneral, "WeaponAttachment.ammogeneral")) return false;
        if (!optional(r, &asset->tracer, "WeaponAttachment.tracer")) return false;
        if (!optional(r, &asset->penetration, "WeaponAttachment.penetration")) return false;
        if (!optional(r, &asset->sight, "WeaponAttachment.sight")) return false;
        if (!optional(r, &asset->holdBreath, "WeaponAttachment.holdBreath")) return false;
        if (!optional(r, &asset->reload, "WeaponAttachment.reload")) return false;
        if (!optional(r, &asset->addOns, "WeaponAttachment.addOns")) return false;
        if (!optional(r, &asset->laser, "WeaponAttachment.laser")) return false;
        if (!optional(r, &asset->general, "WeaponAttachment.general")) return false;
        if (!optional(r, &asset->aimAssist, "WeaponAttachment.aimAssist")) return false;
        if (!optional(r, &asset->targetAssist, "WeaponAttachment.targetAssist")) return false;
        if (!optional(r, &asset->unkAtt01, "WeaponAttachment.unkAtt01")) return false;
        if (!optional(r, &asset->ammunition, "WeaponAttachment.ammunition")) return false;
        if (!optional(r, &asset->damage, "WeaponAttachment.damage")) return false;
        if (!optional(r, &asset->idleSettings, "WeaponAttachment.idleSettings")) return false;
        if (!optional(r, &asset->adsSettings, "WeaponAttachment.adsSettings")) return false;
        if (!optional(r, &asset->adsSettingsMain, "WeaponAttachment.adsSettingsMain")) return false;
        if (!optional(r, &asset->scopeDriftSettings, "WeaponAttachment.scopeDriftSettings")) return false;
        if (!optional(r, &asset->scopeDriftSettingsMain, "WeaponAttachment.scopeDriftSettingsMain")) return false;
        if (!optional(r, &asset->hipSpread, "WeaponAttachment.hipSpread")) return false;
        if (!optional(r, &asset->slideSpread, "WeaponAttachment.slideSpread")) return false;
        if (!optional(r, &asset->gunKick, "WeaponAttachment.gunKick")) return false;
        if (!optional(r, &asset->viewKick, "WeaponAttachment.viewKick")) return false;
        if (!optional(r, &asset->adsOverlay, "WeaponAttachment.adsOverlay")) return false;
        if (!optional(r, &asset->outline, "WeaponAttachment.outline")) return false;
        if (!optional(r, &asset->ui, "WeaponAttachment.ui")) return false;
        if (!optional(r, &asset->rumbles, "WeaponAttachment.rumbles")) return false;
        if (!optional(r, &asset->projectile, "WeaponAttachment.projectile")) return false;
        if (!optional(r, &asset->charged, "WeaponAttachment.charged")) return false;
        if (!optional(r, &asset->adsAltSwitch, "WeaponAttachment.adsAltSwitch")) return false;
        if (!optional(r, &asset->regeneration, "WeaponAttachment.regeneration")) return false;
        if (!optional(r, &asset->movement, "WeaponAttachment.movement")) return false;
        if (!optional(r, &asset->burst, "WeaponAttachment.burst")) return false;
        if (!r.pointer_array(&asset->locationDamage, 22, "WeaponAttachment.locationDamage", [&](const auto* value) { return r.scalar(value, "WeaponAttachment.locationDamage"); })) return false;
        if (!r.scalar(&asset->ammunitionScale, "WeaponAttachment.ammunitionScale")) return false;
        if (!r.scalar(&asset->damageScale, "WeaponAttachment.damageScale")) return false;
        if (!r.scalar(&asset->stateTimersScale, "WeaponAttachment.stateTimersScale")) return false;
        if (!r.scalar(&asset->reloadTimersScale, "WeaponAttachment.reloadTimersScale")) return false;
        if (!r.scalar(&asset->fireTimeOverride, "WeaponAttachment.fireTimeOverride")) return false;
        if (!r.scalar(&asset->fireTimeAkimboOverride, "WeaponAttachment.fireTimeAkimboOverride")) return false;
        if (!r.scalar(&asset->fireTimersScale, "WeaponAttachment.fireTimersScale")) return false;
        if (!r.scalar(&asset->burstFireCooldownScale, "WeaponAttachment.burstFireCooldownScale")) return false;
        if (!r.scalar(&asset->idleHipMotionScale, "WeaponAttachment.idleHipMotionScale")) return false;
        if (!r.scalar(&asset->idleADSMotionScale, "WeaponAttachment.idleADSMotionScale")) return false;
        if (!r.scalar(&asset->idleADSMotionTimeScale, "WeaponAttachment.idleADSMotionTimeScale")) return false;
        if (!r.scalar(&asset->adsSettingsScale, "WeaponAttachment.adsSettingsScale")) return false;
        if (!r.scalar(&asset->adsSettingsScaleMain, "WeaponAttachment.adsSettingsScaleMain")) return false;
        if (!r.scalar(&asset->hipSpreadScale, "WeaponAttachment.hipSpreadScale")) return false;
        if (!r.scalar(&asset->slideSpreadScale, "WeaponAttachment.slideSpreadScale")) return false;
        if (!r.scalar(&asset->gunKickScale, "WeaponAttachment.gunKickScale")) return false;
        if (!r.scalar(&asset->viewKickScale, "WeaponAttachment.viewKickScale")) return false;
        if (!r.scalar(&asset->viewCenterScale, "WeaponAttachment.viewCenterScale")) return false;
        if (!r.scalar(&asset->adsSwayScale, "WeaponAttachment.adsSwayScale")) return false;
        if (!r.scalar(&asset->adsSwayScale2, "WeaponAttachment.adsSwayScale2")) return false;
        if (!r.scalar(&asset->adsSwayScale3, "WeaponAttachment.adsSwayScale3")) return false;
        if (!r.scalar(&asset->iAmmoIndex, "WeaponAttachment.iAmmoIndex")) return false;
        if (!r.scalar(&asset->loadIndex, "WeaponAttachment.loadIndex")) return false;
        if (!r.scalar(&asset->useAlternateViewModelLaser, "WeaponAttachment.useAlternateViewModelLaser")) return false;
        if (!r.scalar(&asset->hideIronSightsWithThisAttachment, "WeaponAttachment.hideIronSightsWithThisAttachment")) return false;
        if (!r.scalar(&asset->shareAmmoWithAlt, "WeaponAttachment.shareAmmoWithAlt")) return false;
        if (!r.scalar(&asset->useLeftTriggerAltFire, "WeaponAttachment.useLeftTriggerAltFire")) return false;
        if (!r.scalar(&asset->containsIKTag, "WeaponAttachment.containsIKTag")) return false;
        if (!r.scalar(&asset->isAkimboAttachment, "WeaponAttachment.isAkimboAttachment")) return false;
        if (!r.scalar(&asset->attachLeftWeaponAkimbo, "WeaponAttachment.attachLeftWeaponAkimbo")) return false;
        if (!r.scalar(&asset->attachRightWeaponAkimbo, "WeaponAttachment.attachRightWeaponAkimbo")) return false;
        if (!r.scalar(&asset->luiWeaponInfoWidgetUsesScopeStencil, "WeaponAttachment.luiWeaponInfoWidgetUsesScopeStencil")) return false;
        if (!r.string_field(&asset->szAltModeName, "WeaponAttachment.szAltModeName")) return false;
        if (!r.string_field(&asset->szLUIWeaponInfoWidgetName, "WeaponAttachment.szLUIWeaponInfoWidgetName")) return false;
        if (!r.string_field(&asset->szLUIWeaponInfoWidgetTag, "WeaponAttachment.szLUIWeaponInfoWidgetTag")) return false;
        return true;
    }
}
