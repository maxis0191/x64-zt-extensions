// The new collector was armed before hook creation/ComInit, never reset here.
static void observe_incoming_image_metadata_iw7(const std::string& zone_arg,
    const std::string& model_arg,const std::string& lod_arg)
{
    if (zone_arg != "mp_freerun_04" || model_arg != "p7_fre_platform_cap_02" || lod_arg != "0")
        throw std::runtime_error("Exact incoming-image zone/model/LOD required");
    selected_image_provenance_context.begin_incoming_map();
    std::exception_ptr load_failure;
    try { resident_export_load_zone(zone_arg); }
    catch (...) { load_failure=std::current_exception(); }
    const auto report=selected_image_provenance_context.finish_incoming(!load_failure);
    const auto text=report.dump();
    if (text.empty() || text.size()>32u*1024u) throw std::runtime_error("Bounded incoming report required");
    ZONETOOL_INFO("T7_INCOMING_IMAGE_METADATA %s",text.c_str());
    if (load_failure) std::rethrow_exception(load_failure);
    if (report.at("refused").get<bool>()) throw std::runtime_error("Incoming image observation refused; diagnostic retained");
}
