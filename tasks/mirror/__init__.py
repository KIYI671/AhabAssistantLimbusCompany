import os

purchase_path = "mirror/shop/must_purchase"
must_purchase_path ="./assets/images/share/mirror/shop/must_purchase"
must_purchase = []
for root, dirs, files in os.walk(must_purchase_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = f"{purchase_path}/{file}"
        # 将文件路径添加到列表中
        must_purchase.append(full_path)

abandoned_path = "mirror/shop/must_be_abandoned"
must_be_abandoned_path ="./assets/images/share/mirror/shop/must_be_abandoned"
must_be_abandoned = []
for root, dirs, files in os.walk(must_be_abandoned_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = f"{abandoned_path}/{file}"
        # 将文件路径添加到列表中
        must_be_abandoned.append(full_path)

fusion_material = {
    'burn': [['melted_paraffin.png', 'decamillennial_stewpot.png'], ['ashes_to_ashes.png', 'dust_to_dust.png', 'secret_cookbook.png']],
    'bleed': [['arrested_hymn.png', 'millarca.png'], ['devotion.png', 'smokes_and_wires.png', 'rusted_muzzle.png']],
    'tremor': ['nixie_divergence.png', 'interlocked_cogs.png', 'bell_of_truth.png'],
    'rupture': ['talisman_bundle.png', 'standard-duty_battery.png', 'thorny_rope_cuffs.png'],
    'poise': [['pendant_of_nostalgia.png', 'recollection_of_a_certain_day.png'],
              ['reminiscence.png', 'four-leaf_clover.png', 'ornamental_horseshoe.png']],
    'sinking': ['headless_portrait.png', 'midwinter_nightmare.png', 'tangled_bones.png'],
    'charge': ['wrist_guards.png', 'material_interference_force_field.png', 'T-18_octagonal_bolt.png'],
}
