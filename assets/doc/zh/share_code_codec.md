# 编队压缩码编码层说明

编队码和卡包权重码编码方案

```
    原始dict
        ↓
    bitpack（忽略统计字段）
        ↓
    gzip 压缩
        ↓
    Base64 编码
        ↓
    最终编队码  
```


## 完整编队压缩码结构

输入数据结构为 `TeamConfig.copy_team()` 返回的裸字典：

```python
{
    "team_system": 4,
    "team_number": 1,
    "shop_strategy": 0,
    "sinners_be_select": 9,
    "chosen_sinners": [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0],
    "sinner_order": [5, 3, 2, 1, 0, 6, 0, 8, 7, 4, 9, 0],
    "...": "...",
    "alias": "小指良",
    "use_team_code": False,
    "team_code": "",
    "theme_pack_weight": {
        "preferred_thresholds": 0,
        "theme_pack_list": {},
        "theme_pack_list_hard": {},
        "theme_pack_list_cn": {},
        "theme_pack_list_hard_cn": {},
    },
}
```

解压输出也是裸 `team_setting` 字典，可直接对接：

```python
TeamConfig.paste_team(team_num, data)
```

## 主题卡包权重压缩码结构

主题卡包权重压缩码格式：

```text
<version>:W:<base64url(gzip(bitpack(theme_pack_weight)))>
```

输入数据结构是裸主题权重字典：

```python
{
    "preferred_thresholds": 0,
    "theme_pack_list": {
        "forgot": 2,
        "gambl": 3,
        "...": -5,
    },
    "theme_pack_list_hard": {
        "Theb": 10,
        "b·e": 10,
        "...": -5,
    },
    "theme_pack_list_cn": {
        "遗忘": 2,
        "赌徒": 3,
        "...": -5,
    },
    "theme_pack_list_hard_cn": {
        "凤皇": 10,
        "凤·皇": 10,
        "...": -5,
    },
}
```

压缩前会先读取默认模板：

```text
theme_pack_list.yaml
```

然后把输入权重合并到默认模板中。

解压输出是裸主题权重字典：

```python
TeamConfig.save_team_theme_pack_weight(team_num, weight)
```

## 数据结构

### 外层文本格式

```text
version ":" kind ":" payload
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | text | 来自 `assets/config/version.txt` 的规范化版本号 |
| `kind` | text | `T` 表示完整编队，`W` 表示主题权重 |
| `payload` | text | 去掉 `=` 补位的 Base64 |

## 示例

完整编队示例：

```text
DEFAULT_VERSION:T:H4sIA...
```

主题权重示例：

```text
DEFAULT_VERSION:W:H4sIA...
```
