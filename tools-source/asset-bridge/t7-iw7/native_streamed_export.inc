// Selected-XPAK native entry point. The existing external Run plan must admit
// the request text and each exact package identity before launching this CLI.
static std::uint64_t selected_streamed_hex64(const std::string& value)
{
    if (value.size() != 16) throw std::runtime_error("Canonical hexadecimal key required");
    std::uint64_t result = 0;
    for (const auto c : value)
    {
        const auto digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
        if (digit < 0) throw std::runtime_error("Lower-case hexadecimal key required");
        result = (result << 4) | static_cast<unsigned>(digit);
    }
    return result;
}

static std::string selected_streamed_hex(const std::uint64_t value)
{
    std::ostringstream out;
    out << std::hex << std::setfill('0') << std::setw(16) << value;
    return out.str();
}

static void selected_streamed_fields(const nlohmann::ordered_json& value,
    const std::set<std::string>& expected)
{
    if (!value.is_object() || value.size() != expected.size())
        throw std::runtime_error("Exact selected-streamed object fields required");
    for (const auto& item : value.items())
        if (!expected.contains(item.key())) throw std::runtime_error("Unknown selected-streamed field");
}

static nlohmann::ordered_json selected_streamed_request(const std::string& argument)
{
    if (!argument.ends_with(".json")) throw std::runtime_error("Pinned flat request JSON required");
    (void)resident_export_name(argument.substr(0, argument.size() - 5).c_str(), true);
    const auto path = std::filesystem::current_path() / argument;
    resident_export_ancestry(path);
    const auto handle = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot retain selected-streamed request");
    const auto close = gsl::finally([&] { CloseHandle(handle); });
    BY_HANDLE_FILE_INFORMATION before{}, after{};
    if (GetFileType(handle) != FILE_TYPE_DISK || !GetFileInformationByHandle(handle, &before) ||
        before.nFileSizeHigh || !before.nFileSizeLow || before.nFileSizeLow > 4096 ||
        (before.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)))
        throw std::runtime_error("Bounded ordinary selected-streamed request required");
    std::string bytes(before.nFileSizeLow, '\0'); DWORD read = 0;
    if (!ReadFile(handle, bytes.data(), before.nFileSizeLow, &read, nullptr) || read != before.nFileSizeLow ||
        !GetFileInformationByHandle(handle, &after) || after.nFileSizeHigh != before.nFileSizeHigh ||
        after.nFileSizeLow != before.nFileSizeLow || CompareFileTime(&before.ftLastWriteTime, &after.ftLastWriteTime))
        throw std::runtime_error("Selected-streamed request changed or was truncated");
    std::vector<std::set<std::string>> object_keys;
    const auto callback = [&](const int, const nlohmann::ordered_json::parse_event_t event,
        nlohmann::ordered_json& parsed)
    {
        if (event == nlohmann::ordered_json::parse_event_t::object_start) object_keys.emplace_back();
        else if (event == nlohmann::ordered_json::parse_event_t::key)
        {
            if (object_keys.empty() || !object_keys.back().insert(parsed.get<std::string>()).second)
                throw std::runtime_error("Duplicate selected-streamed request key");
        }
        else if (event == nlohmann::ordered_json::parse_event_t::object_end) object_keys.pop_back();
        return true;
    };
    return nlohmann::ordered_json::parse(bytes, callback);
}

static void export_selected_streamed_model_iw7(const std::string& zone_arg, const std::string& model_arg,
    const std::string& lod_arg, const std::string& request_arg, const bool render_only = false)
{
    const auto zone = resident_export_name(zone_arg.c_str(), true);
    const auto name = resident_export_name(model_arg.c_str());
    if (lod_arg.size() != 1 || lod_arg[0] < '0' || lod_arg[0] > '5')
        throw std::runtime_error("Canonical selected-streamed LOD 0..5 required");
    const auto lod = static_cast<unsigned>(lod_arg[0] - '0');
    const auto request = selected_streamed_request(request_arg);
    std::set<std::string> request_fields{"schema", "target", "profile", "zone", "model", "lod", "xpak_key", "packages"};
    if (render_only) request_fields.insert("collision_policy");
    selected_streamed_fields(request, request_fields);
    if (request["schema"] != (render_only ? "iw7.t7-iw7-selected-streamed-request/2" : "iw7.t7-iw7-selected-streamed-request/1") ||
        request["target"] != "iw7" ||
        request["profile"] != (render_only ? "selected-streamed-render-only-rigid-one-lod" : "selected-streamed-rigid-one-lod") ||
        (render_only && request["collision_policy"] != "omit-source-rigid-collision-trees") || request["zone"] != zone ||
        request["model"] != name || !request["lod"].is_number_unsigned() || request["lod"].get<std::uint64_t>() != lod ||
        !request["xpak_key"].is_string() || !request["packages"].is_array() ||
        request["packages"].empty() || request["packages"].size() > selected_xpak::max_packages)
        throw std::runtime_error("Request differs from exact selected-streamed command");
    const auto key_text = request["xpak_key"].get<std::string>();
    const auto expected_key = selected_streamed_hex64(key_text);
    std::vector<selected_xpak::package> packages;
    std::set<std::string> paths, identities;
    std::string root_input = std::string(render_only ? streamed_iw7::render_profile : streamed_iw7::profile) +
        "\n" + zone + "\n" + name + "\n" + lod_arg + "\n" + key_text;
    const auto cwd = std::filesystem::current_path();
    for (const auto& package : request["packages"])
    {
        selected_streamed_fields(package, {"path", "identity", "bytes"});
        if (!package["path"].is_string() || !package["identity"].is_string() || !package["bytes"].is_number_unsigned())
            throw std::runtime_error("Typed selected package path/identity/bytes required");
        const auto path = package["path"].get<std::string>();
        const auto identity = package["identity"].get<std::string>();
        const auto size = package["bytes"].get<std::uint64_t>();
        if (!path.starts_with("zone/") || !path.ends_with(".xpak") || path.size() <= 10 ||
            identity.size() != 25 || identity[8] != ':' || size < 120 || size > 16ull * 1024 * 1024 * 1024 ||
            !paths.insert(path).second || !identities.insert(identity).second)
            throw std::runtime_error("Explicit unique bounded selected package required");
        (void)resident_export_name(path.substr(5, path.size() - 10).c_str(), true);
        for (std::size_t i = 0; i < identity.size(); ++i)
            if (i != 8 && !((identity[i] >= '0' && identity[i] <= '9') ||
                (identity[i] >= 'A' && identity[i] <= 'F')))
                throw std::runtime_error("Canonical retained package file identity required");
        selected_xpak::sealed_file file(cwd / path);
        auto view = file.view();
        if (view.identity != identity || view.size != size || view.name != path.substr(5))
            throw std::runtime_error("Retained selected package differs from admitted request");
        packages.push_back(std::move(view)); // Retains the same handle through dump.
        root_input += "\n" + path + "\n" + identity + "\n" + std::to_string(size);
    }
    resident_export_load_zone(zone); // Locks legacy global XPAK access permanently.
    const auto header = db_find_x_asset_header(ASSET_TYPE_XMODEL, name.c_str());
    if (!header.data || DB_IsXAssetDefault(ASSET_TYPE_XMODEL, name.c_str()))
        throw std::runtime_error("Exact nondefault streamed source model required");
    selected_export_observe_material(reinterpret_cast<const XModel*>(header.data), name, lod);
    utils::memory::allocator allocator;
    auto selected = streamed_iw7::select(reinterpret_cast<XModel*>(header.data), name.c_str(), lod,
        expected_key, packages, LZ4_decompress_safe, allocator, render_only);
    const auto& observed = selected.payload.observed;
    std::string package_path;
    for (const auto& package : request["packages"])
        if (package["identity"] == observed.package_identity) package_path = package["path"].get<std::string>();
    if (package_path.empty()) throw std::runtime_error("Selected package provenance not in admitted request");
    auto descriptor = nlohmann::ordered_json::array();
    for (const auto word : selected.opaque_descriptor_words) descriptor.push_back(selected_streamed_hex(word));
    const nlohmann::ordered_json provenance = {
        {"key_hex", selected_streamed_hex(selected.source_key)},
        {"source_shared_flags", selected.source_shared_flags}, {"cpu_view_shared_flags", selected.cpu_view_shared_flags},
        {"source_surface_flags", selected.source_surface_flags}, {"opaque_descriptor_words_hex", descriptor},
        {"descriptor_field_semantics_verified", false}, {"package_path", package_path},
        {"package_identity", observed.package_identity}, {"file_bytes", observed.file_bytes},
        {"hash_table_offset", observed.hash_table_offset}, {"hash_entry_offset", observed.hash_entry_offset},
        {"payload_offset", observed.payload_offset}, {"compressed_bytes", observed.compressed_bytes},
        {"packed_entry_size", observed.packed_entry_size}, {"indexed_bytes", observed.indexed_bytes},
        {"opcodes", observed.opcodes}, {"opaque_header_offsets", observed.header_offsets},
        {"payload_bytes", selected.payload.bytes.size()},
        {"payload_sha256", utils::string::to_lower(utils::cryptography::sha256::compute(
            selected.payload.bytes.data(), selected.payload.bytes.size(), true))},
        {"headers_rechecked", true}, {"atomic_snapshot_proven", false}, {"engine_object_writes", false}};
    const auto root_key = "t7_iw7_streamed_" + utils::string::to_lower(utils::cryptography::sha256::compute(
        reinterpret_cast<const std::uint8_t*>(root_input.data()), root_input.size(), true));
    nlohmann::ordered_json collision_policy;
    if (render_only)
        collision_policy = {{"policy", "omit-source-rigid-collision-trees"}, {"scope", "render-only"},
            {"source_tree_present", selected.source_collision_tree_present},
            {"cpu_tree_present", std::vector<bool>(selected.source_collision_tree_present.size(), false)},
            {"collision_dropped", selected.source_collision_tree_present},
            {"collision_tree_payload_bytes_read", 0}, {"collision_conversion_attempted", false},
            {"collision_compatibility_verified", false}, {"ready", false}};
    write_selected_model_iw7(selected.model, zone, name, lod_arg, true, &provenance, root_key,
        render_only ? &collision_policy : nullptr);
}
