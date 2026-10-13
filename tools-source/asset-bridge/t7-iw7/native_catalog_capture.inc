// Existing DB hook: copy bounded names, never throw or retain engine pointers.
static std::atomic_bool resident_catalog_active{false};
static std::atomic_bool resident_catalog_failed{false};
static std::mutex resident_catalog_mutex;
static std::vector<std::string> resident_catalog_names;
static size_t resident_catalog_name_bytes = 0;
static constexpr size_t resident_catalog_max_names = 1024;
static constexpr size_t resident_catalog_max_name_bytes = 256u * 1024u;

static void resident_catalog_capture(XAssetType type, XAssetHeader header) noexcept
{
    if (type != ASSET_TYPE_XMODEL || !resident_catalog_active.load()) return;
    try
    {
        std::lock_guard<std::mutex> lock(resident_catalog_mutex);
        if (!resident_catalog_active.load() || resident_catalog_failed.load()) return;
        const auto& model = resident_iw7::detail::object(reinterpret_cast<const XModel*>(header.data));
        auto name = resident_iw7::detail::name(model.name);
        if (std::find(resident_catalog_names.begin(), resident_catalog_names.end(), name) != resident_catalog_names.end()) return;
        if (resident_catalog_names.size() >= resident_catalog_max_names ||
            name.size() + 1 > resident_catalog_max_name_bytes - resident_catalog_name_bytes)
        {
            resident_catalog_failed.store(true);
            return;
        }
        resident_catalog_name_bytes += name.size() + 1;
        resident_catalog_names.push_back(std::move(name));
    }
    catch (...) { resident_catalog_failed.store(true); }
}
