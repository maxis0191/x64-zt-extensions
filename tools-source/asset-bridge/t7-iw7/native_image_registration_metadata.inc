// New opt-in route. Copy header/name only inside the original registration callback.
static void observe_registration_image_metadata_iw7(const std::string& zone_arg,
    const std::string& model_arg, const std::string& lod_arg)
{
    if (zone_arg != "mp_freerun_04" || model_arg != "p7_fre_platform_cap_02" || lod_arg != "0")
        throw std::runtime_error("Exact registration-metadata zone/model/LOD required");
    selected_image_provenance_context.begin_registration_metadata();
    resident_export_load_zone(zone_arg);
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, model_arg.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, model_arg.c_str()))
        throw std::runtime_error("Exact nondefault registration-metadata model required");
    const auto report = selected_image_provenance_context.finish_registration_metadata(
        reinterpret_cast<const XModel*>(header.data), true);
    const auto text = report.dump();
    if (text.empty() || text.size() > 32u * 1024u)
        throw std::runtime_error("Bounded registration-metadata report required");
    ZONETOOL_INFO("T7_REGISTRATION_IMAGE_METADATA %s", text.c_str());
    if (report.at("refused").get<bool>())
        throw std::runtime_error("Registration image metadata refused; diagnostic retained");
}
