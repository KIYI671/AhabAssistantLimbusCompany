import os
import requests
from my_decorator.decorator import begin_and_finish_time_log
from my_log.my_log import my_log
import re
import subprocess
import sys
from PyQt5.QtCore import QCoreApplication

API_URL="https://api.github.com/repos/KIYI671/AhabAssistantLimbusCompany/releases/latest"
version=''

@begin_and_finish_time_log(task_name="检查更新")
def check_update():
    response = requests.get(API_URL)

    if response.status_code != 200:
        my_log("info",f"无法检测更新，请检查网络连接")
        return
    
    release_data = response.json()

    # 查找 .7z 文件的下载链接
    download_url = None
    for asset in release_data['assets']:
        if asset['name'].endswith('.7z'):
            match = re.search(r'AALC_(.+)\.7z', asset['name'])
            if match:
                current_version = match.group(1)
                if current_version == version:
                   my_log("info",f"当前版本为最新版本：{current_version}")
                   return
                else:
                    download_url = asset['browser_download_url']
            else:
                my_log("info",f"未找到 .7z 文件")
                return
            break

    if not download_url:
        print("未找到 .7z 文件的下载链接")
        return
    
    file_name = download_url.split('/')[-1]  # 提取文件名
    my_log("info",f"正在下载 {file_name} ...")
    response = requests.get(download_url, stream=True)

    # 检查文件下载是否成功
    if response.status_code == 200:
        with open(file_name, 'wb') as f:
           for chunk in response.iter_content(chunk_size=8192):
              f.write(chunk)
        print(f"下载完成,请手动解压 {file_name} 完成更新")
    else:
        print(f"下载失败，请检查网络")

    return
    