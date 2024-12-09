python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
mkdir dist_release
mv dist/* dist_release/
cp -r 3rdparty dist_release/AALC/
cp -r pic dist_release/AALC/
cp config.yaml dist_release/AALC/
cp black_list_keyword.yaml dist_release/AALC/
