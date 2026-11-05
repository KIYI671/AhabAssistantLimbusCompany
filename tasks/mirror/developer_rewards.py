"""Opt-in no-reward detection; statistics remain in the original Mirror flow."""


def reward_page_visible(auto):
    return any(auto.find_element(path) for path in (
        "mirror/claim_reward/battle_statistics_assets.png",
        "mirror/claim_reward/clear_assets.png",
        "mirror/claim_reward/claim_rewards_assets.png",
        "mirror/claim_reward/use_enkephalin_assets.png",
    ))

