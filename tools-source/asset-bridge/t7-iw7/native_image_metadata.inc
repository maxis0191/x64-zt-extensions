// Distinct opt-in body-metadata route; never runs from the F2 provenance option.
static void observe_selected_image_metadata_iw7(const std::string& zone_arg,
    const std::string& model_arg, const std::string& lod_arg)
{
    if (zone_arg != "mp_freerun_04" || model_arg != "p7_fre_platform_cap_02" || lod_arg != "0")
        throw std::runtime_error("Exact image-metadata zone/model/LOD required");
    selected_image_provenance_context.begin();
    resident_export_load_zone(zone_arg);
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, model_arg.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, model_arg.c_str()))
        throw std::runtime_error("Exact nondefault image-metadata model required");
    const auto model = reinterpret_cast<const XModel*>(header.data);
    const auto provenance = selected_image_provenance_context.finish(model);
    const auto report = selected_image_metadata::observe(model, provenance,
        &resident_iw7::detail::readable, true);
    const auto text = report.dump();
    if (text.empty() || text.size() > 32u * 1024u)
        throw std::runtime_error("Bounded image-metadata report required");
    ZONETOOL_INFO("T7_SELECTED_IMAGE_METADATA %s", text.c_str());
    if (report.at("refused").get<bool>())
        throw std::runtime_error("Selected image metadata refused; diagnostic retained");
}
