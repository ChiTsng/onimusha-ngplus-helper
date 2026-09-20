# 鬼武者 · 周目继承助手 0.9

Windows x64 / Steam版 / 简体中文、English、日本語离线工具。无需安装 Python 或 .NET。完整解压发布包，运行 OnimushaNGPlus.exe。

从 [Releases](https://github.com/ChiTsng/onimusha-ngplus-helper/releases/latest) 下载 Windows ZIP。请保留独立备份；本工具非 CAPCOM 官方产品。以下版本记录按新到旧排列，以最新版本说明为准。

0.9：删除此前宝箱名称的猜译，直接采用本机游戏MSG多语言文本。42个具名物品全部匹配 `itemdatatext.msg.23` 的同一条英文/简中/日文记录；27个具名地区匹配破魔镜地点表 `gm900_001_00points.msg.23`。15个编号区域由 `gm900_001_00stage.msg.23` 的官方大区名加“地图区域/地図エリア”编号组成，编号不是官方地名。1个“Special chest”在地图中未注明内容，仍显示特殊宝箱（内容未标注），不猜物品。英文原名和地图链接保留。`official_labels.json` 附记录键与源文件哈希，方便核查。此说明取代下方0.7版的参考译名说明（此前物品数44也更正为42个具名物品加1个特殊宝箱占位）。

0.9 uses the game's own Chinese/Japanese strings for all 42 named items and 27 named places. Fifteen numbered map areas combine official region names with explicitly unofficial map numbers. The unnamed special chest remains unknown. Only the required short names and provenance are bundled, not complete game text files.

0.9では、アイテム42種と固有地名27種にゲーム内の中国語・日本語表記を使用します。番号付きの地図エリア15種は公式の大地域名と地図独自の番号を組み合わせています。内容不明の特殊宝箱は推測で補完しません。

0.8：同步最终战前只补齐16项鬼杀再战资格。弁庆（武器解放）与最终源义经不提前解锁；目标原本已解锁则保持，不反向锁回。旧版已开放全部资格的存档不会因此恢复成未解锁状态。此规则取代下文旧版“18名Boss”的说明。共享完成状态仍不修改。

0.8 unlocks only 16 pre-finale Carnage rematches. Benkei (Weapon Unleashed) and final Yoshitsune are not newly unlocked; existing access is never revoked, including access granted by older versions.

0.8では最終連戦前の鬼殺再戦16項目のみを補完します。弁慶（武器解放）と最終戦の源義経は先行解放しません。旧版で解放済みの場合を含め、既存の資格は取り消しません。

0.7：宝箱列表的全部42种地区名称、44种物品名称加入中日文参考译名，随界面语言切换。不是已核实的官方本地化词表；部分装备/幻魔名可能与游戏用词不同。选中条目后可在底部查看英文原名。宝箱编号、数量、状态与定位链接不变；游戏存档内的任务摘要仍保留原文。此更新取代下文0.6版本关于地图名称保留原文的说明。

Chest labels now follow the UI language. Chinese/Japanese labels are reference translations, not a verified official glossary. Select a row to see the original English; quantities, IDs and map links are unchanged.

宝箱の地域名・内容は画面の言語に合わせて表示します。中日名称は公式対訳を確認したものではなく、参考訳です。項目を選択すると英語原文を確認できます。数量・ID・地図リンクは変更しません。

0.6：支持简体中文 / English / 日本語，右上角切换。覆盖主界面、查漏状态、预览、应用确认、备份恢复和工具自身的错误提示。切换语言会重建界面并清空预览，需要重新读取；文件路径和账号输入保留，不写入游戏文件。处理期间禁止切换。语言选择仅本次运行有效，未写入额外配置。游戏写入的存档标题/任务摘要、第三方地图地区与道具名保留原文，系统文件对话框和底层组件错误可能遵循系统/组件语言。

再战数据分两层：手动栏位各有 `_BossRematch`（包含普通/高难度资格位图及Boss列表），共享区另有 `RematchStateA/B/C` 三组Boss状态列表。共享完成状态不是可从一号位单独恢复的历史快照。当前同步补齐目标的16项最终连战前鬼杀资格，不提前解锁弁庆（武器解放）和最终源义经，已有资格不撤销；不复制来源的再战成绩、不重置共享完成状态。尚未据这三个字段认定全部计时/奖励数据的具体编码。

## English quick start

Select **English** at the top right. Save and exit the game, load your save, optionally check source chests, then select different source/destination manual slots. The destination must be Carnage NG+ created in-game. Preview before applying; existing files are backed up automatically. The final-battle mode requires manual confirmation that the cleared source is before BOTH final missions. Shared rematch completion is preserved, not copied from the source. Language changes clear the preview and require reloading, but do not write game files. Save summaries and third-party map text remain in their original language. This is an unofficial Steam/Windows tool; keep backups and do not assume compatibility with future versions.

## 日本語クイックスタート

右上で **日本語** を選択してください。ゲームで保存して終了後、セーブを読み込みます。必要に応じて移行元の宝箱を確認し、異なる手動スロットを移行元・移行先に指定してください。移行先はゲーム内で作成した鬼殺NG+が必要です。変更をプレビューしてから適用します。既存ファイルは自動でバックアップされます。最終連戦前への同期には、クリア済みの移行元が最後の連続する2つの主線任務の開始前であることを手動確認する必要があります。共通の再戦達成状態は維持し、移行元の成績はコピーしません。言語変更後は再読み込みが必要ですが、ゲームファイルへの書き込みは行いません。セーブの任務概要・外部地図の名称は原文のままです。非公式のSteam/Windows用ツールです。必ずバックアップを保管してください。

0.5：主页面、预览区和宝箱列表统一使用无箭头、低对比度细滚动条，悬停和拖动时加深。本次仅调整样式，按要求未执行测试。

0.4：确认框选中后使用绿色底、白色对勾，不再使用叉号；仍支持键盘空格切换。启动时显示的账号来自运行电脑的Steam目录，不是作者账号预设。请仅分享发布ZIP，不要附带自己的存档或备份。

0.3：更新卡片式界面、模式高亮、可滚动主页面。最终战前位置勾选框明确为人工确认，仅在同步模式下启用；切换模式、来源栏位、文件或账号后清除确认，避免沿用上一个来源的确认。数据修改逻辑与0.2相同。

1. 在游戏中保存并退出。打开工具，选择账号对应的存档；也可手动选择文件并输入原账号的SteamID64。
2. 推荐先选一周目来源栏位，检查不刷新宝箱（不限内容）。双击条目可打开外部地图；存档不会上传。补齐后重新保存、退出并重新读取。
3. 在游戏内正常创建鬼杀NG+并保存到另一手动栏位，再退出。选择来源和目标。
4. 选择仅继承养成，或同步最终战前。生成预览，检查后写回或另存。
5. 游戏内选择目标手动栏位加载，不选择“继续”读取自动存档。进入后重新保存以刷新选档界面摘要。

“仅继承养成”复制数值强化与红魂，保留目标剧情。“同步最终战前”以来源重建目标剧情、背包、地图与收集状态，补齐7件鬼杀剧情外观、最终连战前16项Boss鬼杀再战资格、已解锁商品库存，并按来源持有量追加力石53、鬼石55。弁庆（武器解放）和最终源义经不提前解锁，目标已有资格不撤销；不改动共享再战完成状态。相同来源重复执行不重复累加素材。

同步模式要求来源已通关并返回最后两段连续主线之前。工具检查通关标记，但不能仅凭标记可靠判断所有中途存档的位置；请如实确认界面提示。推荐用刚创建的NG+作为目标，其已有剧情和背包会被来源替换。共享外观对全部栏位生效。

补偿口径：一轮固定来源各领取一次。力石55减最终连续主线2=53；鬼石57减天守2=55。最终阶段留给玩家自己游玩领取。工具不修改自动存档，不提供任意道具修改。

已验证的存档结构来自此次研究的Steam版本。未知结构、异常数值、空栏位、布局不一致、重复道具ID均拒绝修改。适用范围不是所有游戏版本的保证。发布前已进行离线备份回归与加密回读测试；其他玩家的游戏内行为仍需验证。

每次写入前在输出文件同目录的 OnimushaEditor_Backups 建立完整备份与修改报告；“恢复备份”恢复整份文件，覆盖当时所有栏位和共享数据，同时备份恢复前版本。工具不自动操作Steam云同步；若Steam提示冲突，请保留所需的本地版本。

宝箱查漏覆盖当前地图数据收录的114箱，其中排除最终战区域随循环重置的3箱，检查111个不刷新宝箱。不限鬼石，也包含力石、装备、藏宝图相关箱子等。仅识别当前状态：0未开启，15已开启，其他值显示未知；未开启也可能尚未满足剧情/藏宝图条件。不能据此证明全部任务奖励、地面拾取或未来版本新增内容均已收集。内容和地区暂保留地图原文；双击打开精确地图标记。

## 自动寻找、兼容性与隐私

自动寻找只读本机Steam注册表安装路径（当前用户及32位安装项），并尝试Program Files下的默认Steam目录。在这些目录的 `userdata/*/2638890/remote/win64_save/data001Slot.bin` 中枚举候选，不扫描全盘，也不读取Steam密码、Cookie或登录令牌。程序启动时仅寻找路径，点击“读取”才解密所选文件。多个候选必须自行选择；只有一个候选且当前路径为空时才自动填入。

SteamID64由 `userdata` 后的数字账号目录加常量76561197960265728本地换算，供存档加解密使用，不向Steam查询或上传。它不是密码，但可关联公开账号资料；分享截图时遮住ID、Windows用户名和存档路径。加解密组件在本机临时目录运行，SteamID会作为本地进程参数传递，临时文件正常结束后清理；这不防御已能读取本机文件/进程的其他程序。备份包含完整存档，不应公开分享。

本工具的查找、查漏、预览、修改均无联网代码；对随附加密组件对应源码的审查未发现网络请求调用，但未进行独立二进制网络审计。只有主动双击地图条目才由浏览器访问第三方网站，链接仅含公共地图与宝箱编号，不附加账号或存档；该网站仍可能收到通常的浏览器访问资料（IP、Cookie等）。

非默认Steam安装通常可通过注册表找到；移动过Steam、注册表缺失、多套安装、无目录权限或仅有云端未下载存档时可能找不到，请手动选择并填写原账号SteamID64。不支持跨账号移植，也不保证其他平台、Proton/Steam Deck及未来存档版本兼容。自动寻找不改变存档格式；解析结构不匹配会拒绝操作，但结构检查不能保证未来版本字段语义不变，请始终保留备份。

依赖与来源：MandarinJuice CLI（MIT，Mi5hmasH）负责加密与解密，.NET运行库及许可证随包提供。见 THIRD_PARTY.md。研究数据参考 https://www.onimusha.tools/ 。此工具为非官方项目，与Capcom无关联。

开发：Python 3.13和PyInstaller。解压源码包，将程序包 `_internal` 中的 `vendor` 与 `notices` 文件夹复制到源码旁，再运行 `python app.py` 或 `python build.py`。测试：`python tests.py --work ../onimusha-save-work`；真实存档测试夹具不随公开源码分发。测试仅操作副本与临时目录。
