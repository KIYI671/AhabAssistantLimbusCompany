import os

purchase_path = "mirror/shop/must_purchase"
must_purchase_path = "./assets/images/share/mirror/shop/must_purchase"
must_purchase = []
for root, dirs, files in os.walk(must_purchase_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = f"{purchase_path}/{file}"
        # 将文件路径添加到列表中
        must_purchase.append(full_path)

abandoned_path = "mirror/shop/must_be_abandoned"
must_be_abandoned_path = "./assets/images/share/mirror/shop/must_be_abandoned"
must_be_abandoned = []
for root, dirs, files in os.walk(must_be_abandoned_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = f"{abandoned_path}/{file}"
        # 将文件路径添加到列表中
        must_be_abandoned.append(full_path)

result_path = "mirror/shop/fusion_result"
fusion_result_path = "./assets/images/share/mirror/shop/fusion_result"
fusion_result = []
for root, dirs, files in os.walk(fusion_result_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = f"{result_path}/{file}"
        # 将文件路径添加到列表中
        fusion_result.append(full_path)
