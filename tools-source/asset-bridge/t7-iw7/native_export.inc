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

static void resident_export_load_zone(const std::string& zone)
{
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
}

static void resident_export_dump_multisurface_mesh(XModelMesh* selected_mesh)
{
    utils::memory::allocator allocator;
    const auto converted = converter::iw7::xmodel_mesh::convert(selected_mesh, allocator);
    if (!converted || converted->numsurfs != selected_mesh->numSurfs || !converted->surfs)
        throw std::runtime_error("Converted surface inventory differs");
    for (unsigned int i = 0; i < converted->numsurfs; ++i)
    {
        auto& surface = converted->surfs[i];
        if (surface.triCount != selected_mesh->surfs[i].triCount || !surface.triIndices)
            throw std::runtime_error("Converted triangle inventory differs at surface[" + std::to_string(i) + "]");
        // fab9358 borrows source index ranges. Its untyped dump ledger rounds
        // a contained byte offset down to sizeof(Face), so overlaps beginning
        // one/two uint16 indices later cannot safely remain pointer aliases.
        // Every occurrence gets its own live allocation, including exact and
        // whole-face aliases. The v2 work bound already includes these 6*T bytes.
        auto* owned_faces = allocator.allocate_array<zonetool::iw7::Face>(surface.triCount);
        if (!owned_faces) throw std::runtime_error("Triangle ownership allocation failed at surface[" + std::to_string(i) + "]");
        std::memcpy(owned_faces, surface.triIndices, sizeof(zonetool::iw7::Face) * surface.triCount);
        surface.triIndices = owned_faces;
    }
    zonetool::iw7::xsurface::dump(converted);
}

// Observe only the selected mesh headers before a resident-profile refusal.
// In particular, a streamed data pointer is never treated as a CPU buffer here.
static void resident_export_observe_mesh(const XModel* source, const std::string& zone,
    const std::string& name, const unsigned int lod)
{
    try
    {
        using namespace resident_iw7::detail;
        const auto model = object(source);
        require(model.numLods > 0 && model.numLods <= 8 && lod < model.numLods,
            "mesh observation requires a valid selected LOD");
        const auto mesh = object(model.meshes[lod]);
        const auto shared = object(mesh.shared);
        require(mesh.numSurfs > 0, "mesh observation requires a nonempty surface header array");
        readable(mesh.surfs, static_cast<std::size_t>(mesh.numSurfs) * sizeof(XSurface));
        auto surfaces = nlohmann::ordered_json::array();
        for (unsigned int i = 0; i < mesh.numSurfs; ++i)
        {
            const auto surface = object(mesh.surfs + i);
            surfaces.push_back({{"index", i}, {"flags", static_cast<unsigned int>(surface.flags)},
                {"vertices", surface.vertCount}, {"triangles", surface.triCount},
                {"rigid_lists", static_cast<unsigned int>(surface.vertListCount)},
                {"base_vertex", surface.baseVertOffset}, {"base_index", surface.baseIndexOffset},
                {"same_shared_header", surface.shared == mesh.shared}});
        }
        const auto& entry = mesh.xpakEntry;
        std::array<std::uint64_t, 3> descriptor_words{};
        static_assert(sizeof(entry) == sizeof(entry.key) + sizeof(descriptor_words));
        std::memcpy(descriptor_words.data(), reinterpret_cast<const std::uint8_t*>(&entry) +
            sizeof(entry.key), sizeof(descriptor_words));
        const nlohmann::ordered_json report = {
            {"schema", "iw7.t7-iw7-selected-mesh-observation/1"},
            {"requested_zone", zone}, {"source_model", name}, {"selected_source_lod", lod},
            {"observed_model_name", resident_iw7::asset_name(model.name)},
            {"mesh_name", resident_iw7::asset_name(mesh.name)}, {"shared_flags", shared.flags},
            {"data_size", shared.dataSize}, {"data_pointer_nonzero", shared.data != nullptr},
            {"shared_vertices", shared.vertCount}, {"shared_skin_vertices", shared.skinVertCount},
            {"shared_indices", shared.indexCount}, {"position_offset", shared.posOffset},
            {"attribute_offset", shared.vertsOffset}, {"index_offset", shared.indicesOffset},
            {"skin_weight_offset", shared.skinWeightsOffset},
            {"xpak_entry", {{"key", entry.key}, {"opaque_descriptor_words_u64", descriptor_words},
                {"descriptor_field_semantics_verified", false}}},
            {"surface_headers", std::move(surfaces)},
            {"headers_rechecked", false}, {"atomic_snapshot_proven", false},
            {"allocation_retained", false},
            {"payload_bytes_read", 0}, {"zonetool_xpak_helper_reads_allowed", false},
            {"geometry_verified", false}, {"runtime_verified", false}, {"ready", false}};
        const auto bytes = report.dump();
        require(bytes.size() <= 64u * 1024u, "selected mesh observation exceeds 64 KiB");
        ZONETOOL_INFO("T7_SELECTED_MESH_METADATA %s", bytes.c_str());
    }
    catch (const std::exception& error)
    {
        // Keep the original selector's outcome and refusal available afterwards.
        ZONETOOL_INFO("T7_SELECTED_MESH_METADATA_REFUSED %s", error.what());
    }
}

static void selected_export_observe_material(const XModel* source, const std::string& name, const unsigned lod)
{
    try
    {
        const auto observation = selected_material_observation::observe(source, name, lod, 0,
            resident_iw7::detail::readable);
        ZONETOOL_INFO("T7_SELECTED_MATERIAL_METADATA %s", observation.c_str());
    }
    catch (const std::exception& error)
    {
        ZONETOOL_INFO("T7_SELECTED_MATERIAL_METADATA_REFUSED %s", error.what());
    }
}

static void write_selected_model_iw7(XModel* selected, const std::string& zone,
    const std::string& name, const std::string& lod_arg, const bool multisurface,
    const nlohmann::ordered_json* streamed_payload = nullptr, const std::string& streamed_root_key = {})
{
    const auto lod = static_cast<unsigned>(lod_arg[0] - '0');
    if (streamed_payload && (!multisurface || streamed_root_key.size() != 80 ||
        !streamed_root_key.starts_with("t7_iw7_streamed_")))
        throw std::runtime_error("Explicit selected-streamed output root required");
    if (!selected || resident_export_name(selected->name) != name || selected->numLods != 1 || !selected->meshes[0])
        throw std::runtime_error("Selected model contract differs");
    const auto mesh_name = resident_export_name(selected->meshes[0]->name);
    const auto selected_mesh = selected->meshes[0];
    const auto surface_count = static_cast<unsigned int>(selected_mesh->numSurfs);
    if (!surface_count || (!multisurface && surface_count != 1) || !selected->meshMaterials ||
        selected->meshMaterials[0].numMaterials != surface_count || !selected->meshMaterials[0].materials)
        throw std::runtime_error("Explicit surface/material slot counts differ");
    auto material_names = nlohmann::ordered_json::array();
    auto surface_records = nlohmann::ordered_json::array();
    std::uint64_t vertices = 0, triangles = 0;
    for (unsigned int i = 0; i < surface_count; ++i)
    {
        // select already validated every slot and payload under the logical
        // geometry bound. Preserve pointer aliases and repeated material names.
        const auto material = selected->meshMaterials[0].materials[i];
        if (!material) throw std::runtime_error("Missing material at surface[" + std::to_string(i) + "]");
        try
        {
            material_names.push_back(resident_export_name(material->name));
        }
        catch (const std::runtime_error& error)
        {
            throw std::runtime_error("surface[" + std::to_string(i) + "] material_slot=" +
                std::to_string(i) + "; " + error.what());
        }
        const auto& surface = selected_mesh->surfs[i];
        vertices += surface.vertCount;
        triangles += surface.triCount;
        if (multisurface)
            surface_records.push_back({{"index", i}, {"material_slot", i},
                {"vertices", surface.vertCount}, {"triangles", surface.triCount}});
    }
    const auto geometry_work = multisurface ?
        resident_iw7::geometry_work_bytes_upper_bound(surface_count, vertices, triangles) : 0;
    // Capture observed selection metadata in the same stable DB scope. Bone
    // strings are observations, not paths: preserve their actual T7 spelling.
    const auto root_bone_name = resident_iw7::detail::name(SL_ConvertToString(selected->boneNames[0]));
    const nlohmann::ordered_json selected_counts = {
        {"bones", static_cast<unsigned int>(selected->numBones)},
        {"roots", static_cast<unsigned int>(selected->numRootBones)},
        {"surfaces", surface_count}, {"vertices", vertices}, {"triangles", triangles}};
    const auto key_input = zone + "\n" + name + "\n" + lod_arg;
    const auto resident_key = "t7_iw7_" + utils::string::to_lower(utils::cryptography::sha256::compute(
        reinterpret_cast<const uint8_t*>(key_input.data()), key_input.size(), true));
    const auto key = streamed_payload ? streamed_root_key : resident_key;
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
    // Bypass automatic dependency expansion. Both explicit adapters give
    // the converter validated CPU geometry with legacy XPAK reads locked.
    converter::iw7::xmodel::dump(selected);
    if (multisurface) resident_export_dump_multisurface_mesh(selected->meshes[0]);
    else converter::iw7::xmodel_mesh::dump(selected->meshes[0]);
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
    nlohmann::ordered_json report = {{"schema", streamed_payload ? "iw7.t7-iw7-selected-streamed-export/1" :
        (multisurface ? "iw7.t7-iw7-resident-export/2" : "iw7.t7-iw7-resident-export/1")},
        {"requested_zone", zone}, {"source_model", name}, {"selected_source_lod", lod},
        {"output_model_name", name}, {"output_mesh_name", mesh_name}, {"output_root_key", key},
        {"target", "iw7"}, {"profile", streamed_payload ? "selected-streamed-rigid-one-lod" : "resident-rigid-one-lod"},
        {"geometry_profile", streamed_payload ? streamed_iw7::profile :
            (multisurface ? resident_iw7::multisurface_profile : resident_iw7::profile)},
        {"root_bone_name", root_bone_name}, {"selected_counts", selected_counts},
        {"material_dependencies", material_names},
        {"model", resident_export_file(root / model_path, 1024u * 1024u)},
        {"mesh", resident_export_file(root / mesh_path, 16u * 1024u * 1024u)},
        {"zonetool_xpak_helper_reads_allowed", false}, {"engine_io_verified", false},
        {"dependency_payloads_verified", false},
        {"asset_zone_ownership_verified", false},
        {"serialized_parse_verified", false}, {"runtime_verified", false}, {"ready", false}};
    if (multisurface)
    {
        report["surface_records"] = surface_records;
        report["geometry_work_bytes_upper_bound"] = geometry_work;
    }
    if (streamed_payload) report["selected_mesh_payload"] = *streamed_payload;
    report["model"]["relative_path"] = model_path.generic_string();
    report["mesh"]["relative_path"] = mesh_path.generic_string();
    const auto bytes = report.dump() + "\n";
    const size_t manifest_limit = multisurface ? 256u * 1024u : 4096u;
    if (bytes.size() > manifest_limit) throw std::runtime_error("Export receipt exceeds explicit version's byte limit");
    // Reuse the retained exclusive-create + exact readback writer. Its function
    // name is historical; it writes the supplied bytes without CSV conversion.
    zonetool::iw7::write_enemy_reference_output(root / "manifest.json", bytes);
    ZONETOOL_INFO("%s name=%s lod=%u root=%s ready=false",
        streamed_payload ? "T7_IW7_SELECTED_STREAMED_EXPORT" : "T7_IW7_RESIDENT_EXPORT",
        name.c_str(), lod, key.c_str());
}

static void export_resident_model_iw7(const std::string& zone_arg, const std::string& model_arg,
    const std::string& lod_arg, const bool multisurface = false)
{
    const auto zone = resident_export_name(zone_arg.c_str(), true);
    const auto name = resident_export_name(model_arg.c_str());
    if (lod_arg.size() != 1 || lod_arg[0] < '0' || lod_arg[0] > '5')
        throw std::runtime_error("Explicit canonical LOD 0..5 required");
    const auto lod = static_cast<unsigned int>(lod_arg[0] - '0');
    resident_export_load_zone(zone);
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str()))
        throw std::runtime_error("Exact nondefault source model required");
    if (multisurface)
    {
        resident_export_observe_mesh(reinterpret_cast<const XModel*>(header.data), zone, name, lod);
        selected_export_observe_material(reinterpret_cast<const XModel*>(header.data), name, lod);
    }
    utils::memory::allocator allocator;
    const auto selected = resident_iw7::select(reinterpret_cast<XModel*>(header.data), name.c_str(), lod, allocator, multisurface);
    write_selected_model_iw7(selected, zone, name, lod_arg, multisurface);
}
