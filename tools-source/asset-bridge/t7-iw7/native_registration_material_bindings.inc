// Distinct mode: copies occur at the existing MODEL registration callback only.
static void observe_registration_material_bindings_iw7(const std::string& zone_arg,
    const std::string& model_arg, const std::string& lod_arg)
{
    if (zone_arg != "mp_freerun_04" || model_arg != "p7_fre_platform_cap_02" || lod_arg != "0")
        throw std::runtime_error("Exact material-bindings zone/model/LOD required");
    selected_image_provenance_context.begin_material_bindings();
    resident_export_load_zone(zone_arg);
    const auto report = selected_image_provenance_context.finish_material_bindings(true);
    const auto text = report.dump();
    if (text.empty() || text.size() > 32u*1024u)
        throw std::runtime_error("Bounded material-bindings report required");
    ZONETOOL_INFO("T7_REGISTRATION_MATERIAL_BINDINGS %s", text.c_str());
    if (report.at("refused").get<bool>())
        throw std::runtime_error("Registration material bindings refused; diagnostic retained");
}
