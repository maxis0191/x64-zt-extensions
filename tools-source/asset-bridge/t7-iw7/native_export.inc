// Source-only adapter. Requires the separately reviewed resident_iw7::select
// header and an external pinned original-job/stock/deadline/output Plan.
static std::string resident_export_name(const char* text, bool zone = false)
{
    if (!zone)
    {
        auto value = resident_iw7::asset_name(text);
        if (value.front() == ',') throw std::runtime_error("Referenced-asset alias is not an export identity");
        return value;
    }
    if (!text) throw std::runtime_error("Null export name");
    const size_t limit = 64;
    std::string value;
    for (size_t i = 0; i <= limit; ++i)
    {
        const auto c = text[i];
        if (!c) break;
        if (i == limit || !((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
            (c >= '0' && c <= '9') || c == '_' || c == '-'))
            throw std::runtime_error("Export name outside reviewed portable subset");
        value += c;
    }
    if (value.empty() || value.front() == '-' || value.front() == '/')
        throw std::runtime_error("Empty/relative export name refused");
    (void)resident_iw7::checked_asset_name(value);
    return value;
}

static void resident_export_ancestry(const std::filesystem::path& path)
{
    auto current = std::filesystem::absolute(path).lexically_normal();
    for (;;)
    {
        const auto attr = GetFileAttributesW(current.c_str());
        if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_REPARSE_POINT))
            throw std::runtime_error("Missing/redirected private output ancestor");
        if (current == current.root_path()) break;
        current = current.parent_path();
    }
}

static nlohmann::ordered_json resident_export_file(const std::filesystem::path& path, const size_t limit)
{
    resident_export_ancestry(path);
    const auto handle = CreateFileW(path.c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot guard export output");
    const auto close = gsl::finally([&] { CloseHandle(handle); });
    BY_HANDLE_FILE_INFORMATION before{}, after{};
    if (!GetFileInformationByHandle(handle, &before) || before.nFileSizeHigh ||
        !before.nFileSizeLow || before.nFileSizeLow > limit ||
        (before.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)))
        throw std::runtime_error("Export output type/size refused");
    std::string bytes(before.nFileSizeLow, '\0');
    DWORD read{};
    if (!ReadFile(handle, bytes.data(), before.nFileSizeLow, &read, nullptr) || read != before.nFileSizeLow ||
        !GetFileInformationByHandle(handle, &after) || after.nFileSizeHigh != before.nFileSizeHigh ||
        after.nFileSizeLow != before.nFileSizeLow ||
        CompareFileTime(&before.ftLastWriteTime, &after.ftLastWriteTime) != 0)
        throw std::runtime_error("Export output changed/short read");
    return {{"bytes", bytes.size()}, {"sha256", utils::cryptography::sha256::compute(
        reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size(), true)}};
}

static void export_resident_model_iw7(const std::string& zone_arg, const std::string& model_arg,
    const std::string& lod_arg)
{
    const auto zone = resident_export_name(zone_arg.c_str(), true);
    const auto name = resident_export_name(model_arg.c_str());
    if (lod_arg.size() != 1 || lod_arg[0] < '0' || lod_arg[0] > '5')
        throw std::runtime_error("Explicit canonical LOD 0..5 required");
    const auto lod = static_cast<unsigned int>(lod_arg[0] - '0');
    if (game::get_mode() != game::t7) throw std::runtime_error("T7 engine mode required");
    // Irreversible for this short-lived process; protects against any later
    // accidental fall-through into the existing global package enumeration.
    xpak::deny_reads_for_resident_export();
    globals.dump = globals.dump_csv = globals.verify = false;
    asset_type_filter.clear();
    referenced_assets.clear();
    if (std::filesystem::exists("zonetool_paths"))
        throw std::runtime_error("External ZoneTool search-path input refused");
    if (is_zone_loaded(zone) || !load_zone(zone, true, false))
        throw std::runtime_error("A fresh exact donor zone load is required");
    wait_for_database();
    if (!is_zone_loaded(zone)) throw std::runtime_error("Exact donor zone did not finish loading");
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str()))
        throw std::runtime_error("Exact nondefault source model required");
    utils::memory::allocator allocator;
    const auto selected = resident_iw7::select(reinterpret_cast<XModel*>(header.data), name.c_str(), lod, allocator);
    if (!selected || resident_export_name(selected->name) != name || selected->numLods != 1 || !selected->meshes[0])
        throw std::runtime_error("Selected model contract differs");
    const auto mesh_name = resident_export_name(selected->meshes[0]->name);
    if (!selected->meshMaterials || selected->meshMaterials[0].numMaterials != 1 ||
        !selected->meshMaterials[0].materials || !selected->meshMaterials[0].materials[0])
        throw std::runtime_error("Exactly one explicit material dependency required");
    const auto material_name = resident_export_name(selected->meshMaterials[0].materials[0]->name);
    const auto key_input = zone + "\n" + name + "\n" + lod_arg;
    const auto key = "t7_iw7_" + utils::string::to_lower(utils::cryptography::sha256::compute(
        reinterpret_cast<const uint8_t*>(key_input.data()), key_input.size(), true));
    const auto cwd = std::filesystem::current_path();
    resident_export_ancestry(cwd);
    const auto dump = cwd / "dump";
    if (!std::filesystem::exists(dump) && !CreateDirectoryW(dump.c_str(), nullptr))
        throw std::runtime_error("Could not create private dump parent");
    resident_export_ancestry(dump);
    const auto root = dump / key;
    if (!CreateDirectoryW(root.c_str(), nullptr)) throw std::runtime_error("Export root must be absent");
    resident_export_ancestry(root);
    filesystem::set_fastfile(key);
    // Bypass auto dump/ref expansion. The geometry adapter already rejected
    // streamed data, optional physics and all but the selected resident LOD.
    converter::iw7::xmodel::dump(selected);
    converter::iw7::xmodel_mesh::dump(selected->meshes[0]);
    const auto model_path = std::filesystem::path("xmodel") / (name + ".xmb");
    const auto mesh_path = std::filesystem::path("xsurface") / (mesh_name + ".xsb");
    const std::set<std::filesystem::path> expected{model_path, mesh_path};
    size_t files = 0;
    uintmax_t total = 0;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(root))
    {
        resident_export_ancestry(entry.path());
        if (entry.is_directory()) continue;
        if (!entry.is_regular_file() || !expected.contains(entry.path().lexically_relative(root)))
            throw std::runtime_error("Unexpected generated export file");
        total += entry.file_size();
        if (++files > 2 || total > 32u * 1024u * 1024u) throw std::runtime_error("Export file budget exceeded");
    }
    if (files != 2) throw std::runtime_error("Both model and mesh outputs required");
    nlohmann::ordered_json report = {{"schema", "iw7.t7-iw7-resident-export/1"},
        {"requested_zone", zone}, {"source_model", name}, {"selected_source_lod", lod},
        {"output_model_name", name}, {"output_mesh_name", mesh_name}, {"output_root_key", key},
        {"target", "iw7"}, {"profile", "resident-rigid-one-lod"},
        {"geometry_profile", resident_iw7::profile},
        {"material_dependencies", nlohmann::ordered_json::array({material_name})},
        {"model", resident_export_file(root / model_path, 1024u * 1024u)},
        {"mesh", resident_export_file(root / mesh_path, 16u * 1024u * 1024u)},
        {"zonetool_xpak_helper_reads_allowed", false}, {"engine_io_verified", false},
        {"dependency_payloads_verified", false},
        {"asset_zone_ownership_verified", false},
        {"serialized_parse_verified", false}, {"runtime_verified", false}, {"ready", false}};
    report["model"]["relative_path"] = model_path.generic_string();
    report["mesh"]["relative_path"] = mesh_path.generic_string();
    const auto bytes = report.dump() + "\n";
    if (bytes.size() > 4096) throw std::runtime_error("Export receipt exceeds 4096 bytes");
    // Reuse the retained exclusive-create + exact readback writer. Its function
    // name is historical; it writes the supplied bytes without CSV conversion.
    zonetool::iw7::write_enemy_reference_output(root / "manifest.json", bytes);
    ZONETOOL_INFO("T7_IW7_RESIDENT_EXPORT name=%s lod=%u root=%s ready=false", name.c_str(), lod, key.c_str());
}
