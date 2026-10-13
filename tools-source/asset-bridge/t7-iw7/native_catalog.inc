static void catalog_resident_models_iw7(const std::string& zone_arg)
{
    const auto zone = resident_export_name(zone_arg.c_str(), true);
    {
        std::lock_guard<std::mutex> lock(resident_catalog_mutex);
        if (resident_catalog_active.load() || !resident_catalog_names.empty())
            throw std::runtime_error("Fresh catalogue process required");
        resident_catalog_failed.store(false);
        resident_catalog_name_bytes = 0;
        resident_catalog_active.store(true);
    }
    const auto reset = gsl::finally([] { resident_catalog_active.store(false); });
    resident_export_load_zone(zone);
    std::vector<std::string> names;
    size_t name_bytes = 0;
    {
        std::lock_guard<std::mutex> lock(resident_catalog_mutex);
        resident_catalog_active.store(false);
        if (resident_catalog_failed.load())
            throw std::runtime_error("Catalogue capture failed or exceeded its bound; no result published");
        name_bytes = resident_catalog_name_bytes;
        names = std::move(resident_catalog_names);
    }
    std::sort(names.begin(), names.end());
    auto models = nlohmann::ordered_json::array();
    for (const auto& name : names)
    {
        const bool reference = name.front() == ',';
        nlohmann::ordered_json row = {{"name", name}, {"reference", reference},
            {"resolved_nondefault", false}, {"counts", nullptr}};
        if (!reference)
        {
            const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str());
            if (header.data && !DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str()))
            {
                const auto& model = resident_iw7::detail::object(reinterpret_cast<const XModel*>(header.data));
                if (resident_iw7::detail::name(model.name) != name)
                    throw std::runtime_error("Catalogue stable DB name differs");
                row["resolved_nondefault"] = true;
                // Header counts only: no mesh, surface, bone array or payload read.
                row["counts"] = {{"bones", static_cast<unsigned int>(model.numBones)},
                    {"roots", static_cast<unsigned int>(model.numRootBones)},
                    {"cosmetic_bones", static_cast<unsigned int>(model.numCosmeticBones)},
                    {"lods", static_cast<unsigned int>(model.numLods)}};
            }
        }
        models.push_back(std::move(row));
    }
    const nlohmann::ordered_json report = {{"schema", "iw7.t7-iw7-model-catalog/1"},
        {"requested_zone", zone}, {"provenance", "observed_during_requested_zone_load"},
        {"model_count", names.size()}, {"name_bytes", name_bytes}, {"models", std::move(models)},
        {"truncated", false}, {"asset_zone_ownership_verified", false},
        {"zonetool_xpak_helper_reads_allowed", false}, {"engine_io_verified", false},
        {"geometry_verified", false}, {"runtime_verified", false}, {"ready", false}};
    const auto bytes = report.dump() + "\n";
    if (bytes.size() > 512u * 1024u) throw std::runtime_error("Catalogue publication exceeds 512 KiB");
    const auto key = "t7_iw7_catalog_" + utils::string::to_lower(utils::cryptography::sha256::compute(
        reinterpret_cast<const uint8_t*>(zone.data()), zone.size(), true));
    const auto root = std::filesystem::current_path() / key;
    resident_export_ancestry(root.parent_path());
    if (!CreateDirectoryW(root.c_str(), nullptr)) throw std::runtime_error("Catalogue root must be absent");
    resident_export_ancestry(root);
    zonetool::iw7::write_enemy_reference_output(root / "catalog.json", bytes);
    ZONETOOL_INFO("T7_IW7_MODEL_CATALOG models=%zu root=%s ready=false", names.size(), key.c_str());
}
