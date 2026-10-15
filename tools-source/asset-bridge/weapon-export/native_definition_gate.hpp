#pragma once
// This is the only serializer-entry gate for the new neutral observation mode.
// Existing PROJECTILE/profile entry points do not use or change this contract.
namespace player_definition_readset
{
    template<class Serialize> bool with_pair(Reader& reader, const WeaponCompleteDef* weapon,
        const WeaponAttachment* pap, Serialize serialize)
    {
        if (!reader.object(weapon, "pair.weapon") || !reader.object(pap, "pair.pap") ||
            !reader.exact_name(&weapon->name, "iw7_shredder_zm", "pair.weapon_name") ||
            !reader.exact_name(&pap->name, "shredderpap1", "pair.pap_name")) return false;
        WeaponDef* definition;
        if (!reader.load(&weapon->weapDef, definition, "pair.weapDef") ||
            !reader.object(definition, "pair.weapDef")) return false;
        static_assert(sizeof(definition->weapType) == sizeof(std::int32_t) &&
            sizeof(pap->weaponType) == sizeof(std::int32_t) && sizeof(pap->papAttachment) == 1);
        std::int32_t base_type, pap_type;
        std::uint8_t pap_flag;
        if (!reader.load(reinterpret_cast<const std::int32_t*>(&definition->weapType), base_type, "pair.base_type") ||
            !reader.load(reinterpret_cast<const std::int32_t*>(&pap->weaponType), pap_type, "pair.pap_type") ||
            !reader.load(reinterpret_cast<const std::uint8_t*>(&pap->papAttachment), pap_flag, "pair.pap_flag") ||
            base_type != 1 || pap_type != 0 || pap_flag != 1) return reader.fail("pair.observed_1_0_1_required");
        size_t occurrences = 0;
        const auto own_slot = [&](const auto* count_address, const auto* list_address)
        {
            using Count = std::remove_cv_t<std::remove_reference_t<decltype(*count_address)>>;
            Count raw;
            size_t count;
            return reader.load(count_address, raw, "pair.attachment_count") &&
                reader.count(raw, count, "pair.attachment_count") &&
                reader.pointer_array(list_address, count, "pair.attachment_list", [&](const auto* address)
                {
                    WeaponAttachment* entry;
                    if (!reader.load(address, entry, "pair.attachment_pointer")) return false;
                    if (entry == pap) ++occurrences;
                    return true;
                }, true);
        };
        if (!own_slot(&weapon->numAttachments, &weapon->attachments) ||
            !own_slot(&weapon->numAttachments2, &weapon->attachments2) ||
            !own_slot(&weapon->numAttachments3, &weapon->attachments3) ||
            !own_slot(&weapon->numAttachments4, &weapon->attachments4) ||
            !own_slot(&weapon->numAttachments5, &weapon->attachments5) ||
            !own_slot(&weapon->numAttachments6, &weapon->attachments6) || occurrences != 1)
            return reader.fail("pair.exact_association_required");
        if (!validate(reader, weapon) || !validate(reader, pap)) return false;
        // The callbacks are the actual two public typed serializers in the CLI
        // and counted callbacks in the future native causal fixture. No flag,
        // enum, pointer or asset field has been changed by this readset.
        serialize(weapon, pap);
        return true;
    }
}
