// Derived from maxis0191/x64-zt fab935826c898806855376662a8a03317b3ad8f1.
// Preserve original author/license notices in the native source.
template<class Sink> bool visit_weapon_fields(WeaponDef* asset, Sink& sink)
{
    if (!sink.required(asset != nullptr)) return false;
    if (asset->gunXModel && !sink.asset(ASSET_TYPE_XMODEL, asset->gunXModel->name, {"weapDef.gunXModel", 0})) return false;
    if (asset->gunXModelLeftHand && !sink.asset(ASSET_TYPE_XMODEL, asset->gunXModelLeftHand->name, {"weapDef.gunXModelLeftHand", 0})) return false;
    if (asset->gunXModelRightHand && !sink.asset(ASSET_TYPE_XMODEL, asset->gunXModelRightHand->name, {"weapDef.gunXModelRightHand", 0})) return false;
    if (asset->defaultViewModel && !sink.asset(ASSET_TYPE_XMODEL, asset->defaultViewModel->name, {"weapDef.defaultViewModel", 0})) return false;
    if (asset->defaultWorldModelLeftHand && !sink.asset(ASSET_TYPE_XMODEL, asset->defaultWorldModelLeftHand->name, {"weapDef.defaultWorldModelLeftHand", 0})) return false;
    if (asset->defaultWorldModelRightHand && !sink.asset(ASSET_TYPE_XMODEL, asset->defaultWorldModelRightHand->name, {"weapDef.defaultWorldModelRightHand", 0})) return false;
    if (asset->worldModel && !sink.asset(ASSET_TYPE_XMODEL, asset->worldModel->name, {"weapDef.worldModel", 0})) return false;
    if (asset->worldXModelLeftHand && !sink.asset(ASSET_TYPE_XMODEL, asset->worldXModelLeftHand->name, {"weapDef.worldXModelLeftHand", 0})) return false;
    if (asset->worldXModelRightHand && !sink.asset(ASSET_TYPE_XMODEL, asset->worldXModelRightHand->name, {"weapDef.worldXModelRightHand", 0})) return false;
    if (asset->defaultWorldModel && !sink.asset(ASSET_TYPE_XMODEL, asset->defaultWorldModel->name, {"weapDef.defaultWorldModel", 0})) return false;
    if (asset->playerShadowModel && !sink.asset(ASSET_TYPE_XMODEL, asset->playerShadowModel->name, {"weapDef.playerShadowModel", 0})) return false;
    if (asset->playerShadowModelLeftHand && !sink.asset(ASSET_TYPE_XMODEL, asset->playerShadowModelLeftHand->name, {"weapDef.playerShadowModelLeftHand", 0})) return false;
    if (asset->playerShadowModelRightHand && !sink.asset(ASSET_TYPE_XMODEL, asset->playerShadowModelRightHand->name, {"weapDef.playerShadowModelRightHand", 0})) return false;
    if (asset->handXModel && !sink.asset(ASSET_TYPE_XMODEL, asset->handXModel->name, {"weapDef.handXModel", 0})) return false;
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexWorldModel != nullptr)) return false;
    if (asset->complexWorldModel)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexWorldModel[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexWorldModel[idx]->name, {"weapDef.complexWorldModel[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexWorldModelLeftHand != nullptr)) return false;
    if (asset->complexWorldModelLeftHand)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexWorldModelLeftHand[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexWorldModelLeftHand[idx]->name, {"weapDef.complexWorldModelLeftHand[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexWorldModelRightHand != nullptr)) return false;
    if (asset->complexWorldModelRightHand)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexWorldModelRightHand[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexWorldModelRightHand[idx]->name, {"weapDef.complexWorldModelRightHand[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexGunXModel != nullptr)) return false;
    if (asset->complexGunXModel)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexGunXModel[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexGunXModel[idx]->name, {"weapDef.complexGunXModel[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexGunXModelLeftHand != nullptr)) return false;
    if (asset->complexGunXModelLeftHand)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexGunXModelLeftHand[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexGunXModelLeftHand[idx]->name, {"weapDef.complexGunXModelLeftHand[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numComplexModels), true)) return false;
    if (!sink.required(!(asset->numComplexModels) || asset->complexGunXModelRightHand != nullptr)) return false;
    if (asset->complexGunXModelRightHand)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numComplexModels; ++idx)
        {
            if (asset->complexGunXModelRightHand[idx] && !sink.asset(ASSET_TYPE_XMODEL, asset->complexGunXModelRightHand[idx]->name, {"weapDef.complexGunXModelRightHand[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(16), false)) return false;
    {
        for (auto idx = 0u; idx < (unsigned int)16; ++idx)
        {
            if (asset->camoWorldModelMaterialOverride[idx] && !sink.asset(ASSET_TYPE_MATERIAL, asset->camoWorldModelMaterialOverride[idx]->name, {"weapDef.camoWorldModelMaterialOverride[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(16), false)) return false;
    {
        for (auto idx = 0u; idx < (unsigned int)16; ++idx)
        {
            if (asset->camoViewModelMaterialOverride[idx] && !sink.asset(ASSET_TYPE_MATERIAL, asset->camoViewModelMaterialOverride[idx]->name, {"weapDef.camoViewModelMaterialOverride[]", idx})) return false;
        }
    }
    if (asset->szXAnims && !sink.asset(ASSET_TYPE_ANIM_PACKAGE, asset->szXAnims->name, {"weapDef.szXAnims", 0})) return false;
    if (asset->szXAnimsRightHanded && !sink.asset(ASSET_TYPE_ANIM_PACKAGE, asset->szXAnimsRightHanded->name, {"weapDef.szXAnimsRightHanded", 0})) return false;
    if (asset->szXAnimsLeftHanded && !sink.asset(ASSET_TYPE_ANIM_PACKAGE, asset->szXAnimsLeftHanded->name, {"weapDef.szXAnimsLeftHanded", 0})) return false;
    if (asset->notetrackFXMapValues)
    {
        if (!sink.count(static_cast<size_t>(16), false)) return false;
        for (auto idx = 0u; idx < (unsigned int)16; ++idx)
        {
            if (!emit_fx(asset->notetrackFXMapValues[idx], {"weapDef.notetrackFXMapValues[]", idx}, sink)) return false;
        }
    }
    if (asset->unkMaterial && !sink.asset(ASSET_TYPE_MATERIAL, asset->unkMaterial->name, {"weapDef.unkMaterial", 0})) return false;
    if (asset->vfxPackage && !sink.asset(ASSET_TYPE_VFX_PACKAGE, asset->vfxPackage->name, {"weapDef.vfxPackage", 0})) return false;
    if (asset->sfxPackage && !sink.asset(ASSET_TYPE_SFX_PACKAGE, asset->sfxPackage->name, {"weapDef.sfxPackage", 0})) return false;
    if (asset->reticleCenter && !sink.asset(ASSET_TYPE_MATERIAL, asset->reticleCenter->name, {"weapDef.reticleCenter", 0})) return false;
    if (asset->reticleSide && !sink.asset(ASSET_TYPE_MATERIAL, asset->reticleSide->name, {"weapDef.reticleSide", 0})) return false;
    if (asset->reticleOnePiece && !sink.asset(ASSET_TYPE_MATERIAL, asset->reticleOnePiece->name, {"weapDef.reticleOnePiece", 0})) return false;
    if (asset->worldClipModel && !sink.asset(ASSET_TYPE_XMODEL, asset->worldClipModel->name, {"weapDef.worldClipModel", 0})) return false;
    if (asset->rocketModel && !sink.asset(ASSET_TYPE_XMODEL, asset->rocketModel->name, {"weapDef.rocketModel", 0})) return false;
    if (asset->knifeModel && !sink.asset(ASSET_TYPE_XMODEL, asset->knifeModel->name, {"weapDef.knifeModel", 0})) return false;
    if (asset->worldKnifeModel && !sink.asset(ASSET_TYPE_XMODEL, asset->worldKnifeModel->name, {"weapDef.worldKnifeModel", 0})) return false;
    if (asset->hudIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->hudIcon->name, {"weapDef.hudIcon", 0})) return false;
    if (asset->pickupIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->pickupIcon->name, {"weapDef.pickupIcon", 0})) return false;
    if (asset->dangerIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->dangerIcon->name, {"weapDef.dangerIcon", 0})) return false;
    if (asset->throwBackIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->throwBackIcon->name, {"weapDef.throwBackIcon", 0})) return false;
    if (asset->ammoCounterIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ammoCounterIcon->name, {"weapDef.ammoCounterIcon", 0})) return false;
    if (asset->projectileModel && !sink.asset(ASSET_TYPE_XMODEL, asset->projectileModel->name, {"weapDef.projectileModel", 0})) return false;
    if (!emit_fx(asset->projExplosionEffect, {"weapDef.projExplosionEffect", 0}, sink)) return false;
    if (!emit_fx(asset->projDudEffect, {"weapDef.projDudEffect", 0}, sink)) return false;
    if (!emit_fx(asset->projBodyEffect, {"weapDef.projBodyEffect", 0}, sink)) return false;
    if (!emit_fx(asset->projTrailEffect, {"weapDef.projTrailEffect", 0}, sink)) return false;
    if (!emit_fx(asset->projBeaconEffect, {"weapDef.projBeaconEffect", 0}, sink)) return false;
    if (!emit_fx(asset->projIgnitionEffect, {"weapDef.projIgnitionEffect", 0}, sink)) return false;
    if (asset->fireRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->fireRumble->name, {"weapDef.fireRumble", 0})) return false;
    if (asset->meleeImpactRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->meleeImpactRumble->name, {"weapDef.meleeImpactRumble", 0})) return false;
    if (asset->tracerType && !sink.asset(ASSET_TYPE_TRACER, asset->tracerType->name, {"weapDef.tracerType", 0})) return false;
    if (asset->overchargeTracerType && !sink.asset(ASSET_TYPE_TRACER, asset->overchargeTracerType->name, {"weapDef.overchargeTracerType", 0})) return false;
    if (asset->laserTypeFriendly && !sink.asset(ASSET_TYPE_LASER, asset->laserTypeFriendly->name, {"weapDef.laserTypeFriendly", 0})) return false;
    if (asset->laserTypeEnemy && !sink.asset(ASSET_TYPE_LASER, asset->laserTypeEnemy->name, {"weapDef.laserTypeEnemy", 0})) return false;
    if (!emit_fx(asset->turretOverheatEffect, {"weapDef.turretOverheatEffect", 0}, sink)) return false;
    if (asset->turretBarrelSpinRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->turretBarrelSpinRumble->name, {"weapDef.turretBarrelSpinRumble", 0})) return false;
    if (asset->shieldDeployGesture && !sink.asset(ASSET_TYPE_GESTURE, asset->shieldDeployGesture->name, {"weapDef.shieldDeployGesture", 0})) return false;
    if (asset->shieldFireWeapGesture && !sink.asset(ASSET_TYPE_GESTURE, asset->shieldFireWeapGesture->name, {"weapDef.shieldFireWeapGesture", 0})) return false;
    if (asset->shieldDeployWhileFiring && !sink.asset(ASSET_TYPE_GESTURE, asset->shieldDeployWhileFiring->name, {"weapDef.shieldDeployWhileFiring", 0})) return false;
    if (asset->shieldRetractWhileFiring && !sink.asset(ASSET_TYPE_GESTURE, asset->shieldRetractWhileFiring->name, {"weapDef.shieldRetractWhileFiring", 0})) return false;
    if (asset->shieldBashGesture && !sink.asset(ASSET_TYPE_GESTURE, asset->shieldBashGesture->name, {"weapDef.shieldBashGesture", 0})) return false;
    if (!emit_fx(asset->shieldMeleeFx, {"weapDef.shieldMeleeFx", 0}, sink)) return false;
    if (asset->shieldHitRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->shieldHitRumble->name, {"weapDef.shieldHitRumble", 0})) return false;
    if (asset->shieldMissRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->shieldMissRumble->name, {"weapDef.shieldMissRumble", 0})) return false;
    if (asset->gestureAnimation && !sink.asset(ASSET_TYPE_GESTURE, asset->gestureAnimation->name, {"weapDef.gestureAnimation", 0})) return false;
    if (asset->gesturePullback && !sink.asset(ASSET_TYPE_GESTURE, asset->gesturePullback->name, {"weapDef.gesturePullback", 0})) return false;
    if (asset->gestureThrow && !sink.asset(ASSET_TYPE_GESTURE, asset->gestureThrow->name, {"weapDef.gestureThrow", 0})) return false;
    if (asset->gestureDetonate && !sink.asset(ASSET_TYPE_GESTURE, asset->gestureDetonate->name, {"weapDef.gestureDetonate", 0})) return false;
    if (!emit_fx(asset->cameraFireEffect, {"weapDef.cameraFireEffect", 0}, sink)) return false;
    if (!emit_fx(asset->chargeMeterEffect, {"weapDef.chargeMeterEffect", 0}, sink)) return false;
    if (asset->chargeRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->chargeRumble->name, {"weapDef.chargeRumble", 0})) return false;
    if (asset->stowOffsetModel && !sink.asset(ASSET_TYPE_XMODEL, asset->stowOffsetModel->name, {"weapDef.stowOffsetModel", 0})) return false;
    if (!emit_fx(asset->deployEffect, {"weapDef.deployEffect", 0}, sink)) return false;
    if (!sink.count(static_cast<size_t>(21), false)) return false;
    for (auto i = 0; i < 21; i++)
    {
    if (asset->animOverrides[i].overrides && !sink.asset(ASSET_TYPE_ANIM_PACKAGE, asset->animOverrides[i].overrides->name, {"weapDef.animOverrides[].overrides", static_cast<unsigned>(i)})) return false;
    if (asset->animOverrides[i].overridesAlt && !sink.asset(ASSET_TYPE_ANIM_PACKAGE, asset->animOverrides[i].overridesAlt->name, {"weapDef.animOverrides[].overridesAlt", static_cast<unsigned>(i)})) return false;
    if (asset->sfxOverrides[i].overrides && !sink.asset(ASSET_TYPE_SFX_PACKAGE, asset->sfxOverrides[i].overrides->name, {"weapDef.sfxOverrides[].overrides", static_cast<unsigned>(i)})) return false;
    if (asset->sfxOverrides[i].overridesAlt && !sink.asset(ASSET_TYPE_SFX_PACKAGE, asset->sfxOverrides[i].overridesAlt->name, {"weapDef.sfxOverrides[].overridesAlt", static_cast<unsigned>(i)})) return false;
    if (asset->vfxOverrides[i].overrides && !sink.asset(ASSET_TYPE_VFX_PACKAGE, asset->vfxOverrides[i].overrides->name, {"weapDef.vfxOverrides[].overrides", static_cast<unsigned>(i)})) return false;
    if (asset->vfxOverrides[i].overridesAlt && !sink.asset(ASSET_TYPE_VFX_PACKAGE, asset->vfxOverrides[i].overridesAlt->name, {"weapDef.vfxOverrides[].overridesAlt", static_cast<unsigned>(i)})) return false;
    }
    return true;
}
template<class Sink> bool visit_weapon(WeaponCompleteDef* asset, Sink& sink)
{
    if (!sink.required(asset != nullptr)) return false;
    if (!sink.count(static_cast<size_t>(asset->numAttachments), true)) return false;
    if (!sink.required(!(asset->numAttachments) || asset->attachments != nullptr)) return false;
    if (asset->attachments)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments; ++idx)
        {
            if (asset->attachments[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments[idx]->name, {"attachments[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numAttachments2), true)) return false;
    if (!sink.required(!(asset->numAttachments2) || asset->attachments2 != nullptr)) return false;
    if (asset->attachments2)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments2; ++idx)
        {
            if (asset->attachments2[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments2[idx]->name, {"attachments2[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numAttachments3), true)) return false;
    if (!sink.required(!(asset->numAttachments3) || asset->attachments3 != nullptr)) return false;
    if (asset->attachments3)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments3; ++idx)
        {
            if (asset->attachments3[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments3[idx]->name, {"attachments3[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numAttachments4), true)) return false;
    if (!sink.required(!(asset->numAttachments4) || asset->attachments4 != nullptr)) return false;
    if (asset->attachments4)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments4; ++idx)
        {
            if (asset->attachments4[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments4[idx]->name, {"attachments4[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numAttachments5), true)) return false;
    if (!sink.required(!(asset->numAttachments5) || asset->attachments5 != nullptr)) return false;
    if (asset->attachments5)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments5; ++idx)
        {
            if (asset->attachments5[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments5[idx]->name, {"attachments5[]", idx})) return false;
        }
    }
    if (!sink.count(static_cast<size_t>(asset->numAttachments6), true)) return false;
    if (!sink.required(!(asset->numAttachments6) || asset->attachments6 != nullptr)) return false;
    if (asset->attachments6)
    {
        for (auto idx = 0u; idx < (unsigned int)asset->numAttachments6; ++idx)
        {
            if (asset->attachments6[idx] && !sink.asset(ASSET_TYPE_ATTACHMENT, asset->attachments6[idx]->name, {"attachments6[]", idx})) return false;
        }
    }
    if (asset->killIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->killIcon->name, {"killIcon", 0})) return false;
    if (asset->dpadIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->dpadIcon->name, {"dpadIcon", 0})) return false;
    if (!visit_weapon_fields(asset->weapDef, sink)) return false;
    return true;
}
