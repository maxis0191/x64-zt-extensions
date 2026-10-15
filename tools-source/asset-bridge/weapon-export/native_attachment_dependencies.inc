// Derived from maxis0191/x64-zt fab935826c898806855376662a8a03317b3ad8f1.
// Preserve original author/license notices in the native source.
template<class Sink> bool visit_attachment(WeaponAttachment* asset, Sink& sink)
{
    if (!sink.required(asset != nullptr)) return false;
    if (asset->worldModelCamo && !sink.asset(ASSET_TYPE_XMODEL, asset->worldModelCamo->name, {"worldModelCamo", 0})) return false;
    if (asset->viewModelCamo && !sink.asset(ASSET_TYPE_XMODEL, asset->viewModelCamo->name, {"viewModelCamo", 0})) return false;
    if (!sink.count(static_cast<size_t>(asset->numModelVariations), true)) return false;
    if (!sink.required(!(asset->numModelVariations) || asset->worldModelVariations != nullptr)) return false;
    if (!sink.required(!(asset->numModelVariations) || asset->viewModelVariations != nullptr)) return false;
    for (auto i = 0u; i < asset->numModelVariations; i++)
    {
    if (asset->worldModelVariations[i] && !sink.asset(ASSET_TYPE_XMODEL, asset->worldModelVariations[i]->name, {"worldModelVariations[]", static_cast<unsigned>(i)})) return false;
    if (asset->viewModelVariations[i] && !sink.asset(ASSET_TYPE_XMODEL, asset->viewModelVariations[i]->name, {"viewModelVariations[]", static_cast<unsigned>(i)})) return false;
    }
    if (!sink.count(static_cast<size_t>(asset->numWorldModelCamoMaterials), true)) return false;
    if (!sink.required(!(asset->numWorldModelCamoMaterials) || asset->worldModelCamoMaterials != nullptr)) return false;
    for (auto i = 0u; i < asset->numWorldModelCamoMaterials; i++)
    {
    if (asset->worldModelCamoMaterials[i] && !sink.asset(ASSET_TYPE_MATERIAL, asset->worldModelCamoMaterials[i]->name, {"worldModelCamoMaterials[]", static_cast<unsigned>(i)})) return false;
    }
    if (!sink.count(static_cast<size_t>(asset->numViewModelCamoMaterials), true)) return false;
    if (!sink.required(!(asset->numViewModelCamoMaterials) || asset->viewModelCamoMaterials != nullptr)) return false;
    for (auto i = 0u; i < asset->numViewModelCamoMaterials; i++)
    {
    if (asset->viewModelCamoMaterials[i] && !sink.asset(ASSET_TYPE_MATERIAL, asset->viewModelCamoMaterials[i]->name, {"viewModelCamoMaterials[]", static_cast<unsigned>(i)})) return false;
    }
    if (!sink.count(static_cast<size_t>(asset->numReticles), true)) return false;
    if (!sink.required(!(asset->numReticles) || asset->reticles != nullptr)) return false;
    for (auto i = 0; i < asset->numReticles; i++)
    {
    if (asset->reticles[i] && !sink.asset(ASSET_TYPE_RETICLE, asset->reticles[i]->name, {"reticles[]", static_cast<unsigned>(i)})) return false;
    }
    if (!sink.count(static_cast<size_t>(asset->numAltReticles), true)) return false;
    if (!sink.required(!(asset->numAltReticles) || asset->altReticles != nullptr)) return false;
    for (auto i = 0; i < asset->numAltReticles; i++)
    {
    if (asset->altReticles[i] && !sink.asset(ASSET_TYPE_RETICLE, asset->altReticles[i]->name, {"altReticles[]", static_cast<unsigned>(i)})) return false;
    }
    if (asset->tracer && asset->tracer->tracerType && !sink.asset(ASSET_TYPE_TRACER, asset->tracer->tracerType->name, {"tracer.tracerType", 0})) return false;
    if (asset->general && asset->general->reticleCenter && !sink.asset(ASSET_TYPE_MATERIAL, asset->general->reticleCenter->name, {"general.reticleCenter", 0})) return false;
    if (asset->general && asset->general->reticleSide && !sink.asset(ASSET_TYPE_MATERIAL, asset->general->reticleSide->name, {"general.reticleSide", 0})) return false;
    if (asset->general && asset->general->reticleOnePiece && !sink.asset(ASSET_TYPE_MATERIAL, asset->general->reticleOnePiece->name, {"general.reticleOnePiece", 0})) return false;
    if (asset->laser && asset->laser->laserTypeFriendly && !sink.asset(ASSET_TYPE_LASER, asset->laser->laserTypeFriendly->name, {"laser.laserTypeFriendly", 0})) return false;
    if (asset->laser && asset->laser->laserTypeEnemy && !sink.asset(ASSET_TYPE_LASER, asset->laser->laserTypeEnemy->name, {"laser.laserTypeEnemy", 0})) return false;
    if (asset->unkAtt01 && asset->unkAtt01->material && !sink.asset(ASSET_TYPE_MATERIAL, asset->unkAtt01->material->name, {"unkAtt01.material", 0})) return false;
    if (asset->adsOverlay && asset->adsOverlay->overlay.shader && !sink.asset(ASSET_TYPE_MATERIAL, asset->adsOverlay->overlay.shader->name, {"adsOverlay.overlay.shader", 0})) return false;
    if (asset->adsOverlay && asset->adsOverlay->overlay.shaderLowRes && !sink.asset(ASSET_TYPE_MATERIAL, asset->adsOverlay->overlay.shaderLowRes->name, {"adsOverlay.overlay.shaderLowRes", 0})) return false;
    if (asset->adsOverlay && asset->adsOverlay->overlay.shaderEMP && !sink.asset(ASSET_TYPE_MATERIAL, asset->adsOverlay->overlay.shaderEMP->name, {"adsOverlay.overlay.shaderEMP", 0})) return false;
    if (asset->adsOverlay && asset->adsOverlay->overlay.shaderEMPLowRes && !sink.asset(ASSET_TYPE_MATERIAL, asset->adsOverlay->overlay.shaderEMPLowRes->name, {"adsOverlay.overlay.shaderEMPLowRes", 0})) return false;
    if (asset->ui && asset->ui->hudIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->hudIcon->name, {"ui.hudIcon", 0})) return false;
    if (asset->ui && asset->ui->pickupIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->pickupIcon->name, {"ui.pickupIcon", 0})) return false;
    if (asset->ui && asset->ui->dangerIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->dangerIcon->name, {"ui.dangerIcon", 0})) return false;
    if (asset->ui && asset->ui->throwBackIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->throwBackIcon->name, {"ui.throwBackIcon", 0})) return false;
    if (asset->ui && asset->ui->dpadIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->dpadIcon->name, {"ui.dpadIcon", 0})) return false;
    if (asset->ui && asset->ui->ammoCounterIcon && !sink.asset(ASSET_TYPE_MATERIAL, asset->ui->ammoCounterIcon->name, {"ui.ammoCounterIcon", 0})) return false;
    if (asset->rumbles && asset->rumbles->fireRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->rumbles->fireRumble->name, {"rumbles.fireRumble", 0})) return false;
    if (asset->rumbles && asset->rumbles->meleeImpactRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->rumbles->meleeImpactRumble->name, {"rumbles.meleeImpactRumble", 0})) return false;
    if (asset->projectile && asset->projectile->projectileModel && !sink.asset(ASSET_TYPE_XMODEL, asset->projectile->projectileModel->name, {"projectile.projectileModel", 0})) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projExplosionEffect, {"projectile.projExplosionEffect", 0}, sink)) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projDudEffect, {"projectile.projDudEffect", 0}, sink)) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projBodyEffect, {"projectile.projBodyEffect", 0}, sink)) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projTrailEffect, {"projectile.projTrailEffect", 0}, sink)) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projBeaconEffect, {"projectile.projBeaconEffect", 0}, sink)) return false;
    if (asset->projectile && !emit_fx(asset->projectile->projIgnitionEffect, {"projectile.projIgnitionEffect", 0}, sink)) return false;
    if (asset->charged && !emit_fx(asset->charged->chargeMeterEffect, {"charged.chargeMeterEffect", 0}, sink)) return false;
    if (asset->charged && asset->charged->chargeRumble && !sink.asset(ASSET_TYPE_RUMBLE, asset->charged->chargeRumble->name, {"charged.chargeRumble", 0})) return false;
    return true;
}
