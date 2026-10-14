// Explicit metadata-only entry. Reuses the resident loader and its global
// helper-XPAK denial; never selects geometry, follows a part key or copies pixels.
static void observe_selected_material_parts_iw7(const std::string& zone_arg,
    const std::string& model_arg, const std::string& lod_arg)
{
    const auto zone = resident_export_name(zone_arg.c_str(), true);
    const auto name = resident_export_name(model_arg.c_str());
    if (lod_arg.size() != 1 || lod_arg[0] < '0' || lod_arg[0] > '5')
        throw std::runtime_error("Canonical material-parts LOD 0..5 required");
    const auto lod = static_cast<unsigned>(lod_arg[0] - '0');
    resident_export_load_zone(zone);
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str()))
        throw std::runtime_error("Exact nondefault material-parts model required");
    const auto observed = selected_material_parts_observation::observe_binding_parts(
        reinterpret_cast<const XModel*>(header.data), name, lod, 0,
        resident_iw7::detail::readable,
        selected_material_observation::image_binding_selection{4u, 0xA0AB1041u});
    if (observed.empty() || observed.size() > 64u * 1024u)
        throw std::runtime_error("Bounded material-parts diagnostic required");
    const auto parsed = nlohmann::ordered_json::parse(observed);
    if (!parsed.is_object() || parsed.value("schema", std::string{}) !=
        "iw7.t7-selected-material-observation/3" ||
        !parsed.contains("pixels_copied") || !parsed["pixels_copied"].is_boolean() ||
        parsed["pixels_copied"].get<bool>() || !parsed.contains("ready") ||
        !parsed["ready"].is_boolean() || parsed["ready"].get<bool>() ||
        !parsed.contains("refused") || !parsed["refused"].is_boolean())
        throw std::runtime_error("Exact metadata-only material-parts schema required");
    ZONETOOL_INFO("T7_SELECTED_MATERIAL_PARTS_METADATA %s", observed.c_str());
    if (parsed["refused"].get<bool>())
        throw std::runtime_error("Selected material-parts observation refused; diagnostic retained");
    if (!parsed.contains("headers_rechecked") || !parsed["headers_rechecked"].is_boolean() ||
        !parsed["headers_rechecked"].get<bool>() || !parsed.contains("stream_parts_headers_rechecked") ||
        !parsed["stream_parts_headers_rechecked"].is_boolean() ||
        !parsed["stream_parts_headers_rechecked"].get<bool>())
        throw std::runtime_error("Selected material-parts headers not rechecked");
}
