extends Control
## 右上角的菜单 + 移植版额外加的几块界面（原版都没有）。
##
## 右上角常驻一块小木牌「菜单」，点开是四项：存档 / 读档 / 隐藏道具 / 关闭。
##   * 存档、读档 —— 三个档位随便挑，见 scripts/save_dialog.gd
##   * 隐藏道具   —— 十九件隐藏道具的图鉴，没拿到的显示 ？？？，见 hidden_items.json
##
## 位置是挑过的：只占最上面那条 20px，正好落在剧情帧「跳过情节」按钮上边那条空白里，
## 不挡它。菜单弹出来的是一竖排木牌，和标题页那几块一模一样。
##
## 长相一律照抄原版自己的界面（米黄底 + 深棕外框 + 朱红隶书字），见 scripts/ui_skin.gd。
##
## 道具从来不看「玩家有没有见过」，只看游戏自己的判定点：
## 帧 297 / 830 / 1317 各送一件倾城装，按钮 1288 是收下羞花衫，
## 帧 968（淘宝成功）按 TBWP 随机数决定淘到哪件珍品。

## 右上角：贴在最上沿，正好躲开剧情帧的「跳过情节」按钮（它在 y=22.8 往下）
const MENU_POS := Vector2(664, 1)
const MENU_SIZE := Vector2(132, 20)
const MENU_DOWN := Vector2(664, 24)
## 菜单项别矮于 40：木牌四角的云要 19px 边距才摆得下（见 ui_skin.gd）
const MENU_ITEM := Vector2(132, 46)
const MENU_GAP := 4.0

const ITEMS_POS := Vector2(70, 64)
const ITEMS_SIZE := Vector2(660, 470)
const CELL_W := 304.0
const NAME_W := 148.0

## 提示条：横向摆在哪几个地方是量过的 —— 左边躲开战斗界面的敌人属性框（到 x=312），
## 右边躲开「跳过情节」（从 x=663 起）
const TOAST_POS := Vector2(330, 2)
const TOAST_SIZE := Vector2(300, 26)

var main: Node = null
var plaque_font: Font = null      ## 木牌上的字（隶书，缺的字走系统兜底）

var sets: Array = []
var by_frame: Dictionary = {}      # 帧号 → [道具键, ...]
var by_button: Dictionary = {}     # 按钮 id → [道具键, ...]
var by_tbwp: Dictionary = {}       # 帧号 → [[随机数下限, 上限, 道具键], ...]

var panel_open: bool = false       ## 隐藏道具框开着没有
var dlg: SaveDialog = null         ## 存档 / 读档框

var _modal := ""                   ## "" / "menu" / "items"
var _menu: Control
var _toggle_btn: Button
var _backdrop: ColorRect
var _box: PanelContainer
var _progress: Label
var _toast: PanelContainer
var _toast_label: Label
var _toast_left: float = 0.0
var _cells: Dictionary = {}        # 道具键 → {n, f, name, fx}
var _menu_items: Button

func setup(main_node: Node, font: Font, cfg: Dictionary) -> void:
	main = main_node
	plaque_font = font
	sets = cfg.get("sets", [])
	_index()
	_build()
	refresh()

## 把「什么时候算拿到」的判定点整理成三张表，主程序每帧/每次点按钮喂进来
func _index() -> void:
	for s in sets:
		for it in s.get("items", []):
			var k := str(it.get("k", ""))
			if k == "":
				continue
			if it.has("frame"):
				var fr := int(it.get("frame", 0))
				if it.has("tbwp"):
					var rng: Array = it.get("tbwp", [])
					if rng.size() >= 2:
						if not by_tbwp.has(fr):
							by_tbwp[fr] = []
						by_tbwp[fr].append([int(rng[0]), int(rng[1]), k])
				else:
					if not by_frame.has(fr):
						by_frame[fr] = []
					by_frame[fr].append(k)
			if it.has("button"):
				var bid := int(it.get("button", 0))
				if not by_button.has(bid):
					by_button[bid] = []
				by_button[bid].append(k)

# ---------------------------------------------------------------- 判定：拿到了什么

func on_frame(n: int) -> void:
	var got := false
	if by_frame.has(n):
		for k in by_frame[n]:
			got = _mark(str(k)) or got
	if by_tbwp.has(n):
		var v := _tbwp()
		for h in by_tbwp[n]:
			if v >= int(h[0]) and v <= int(h[1]):
				got = _mark(str(h[2])) or got
	if got:
		refresh()

func on_button(id: int) -> void:
	if not by_button.has(id):
		return
	var got := false
	for k in by_button[id]:
		got = _mark(str(k)) or got
	if got:
		refresh()

func _mark(k: String) -> bool:
	return GameState.mark_item(k)

## 原版淘宝那一步的随机数（TBWP）：0~13 是十四种珍品，14 及以上是玉如意
func _tbwp() -> int:
	if main == null:
		return -1
	var lg = main.get("logic")
	if lg == null:
		return -1
	var v = lg.V("TBWP")
	return -1 if v == null else int(v)

# ---------------------------------------------------------------- 开关

## 菜单 / 道具框 / 存档框里有任何一个开着，游戏按键就不该再传下去
func ui_open() -> bool:
	return _modal != "" or (dlg != null and dlg.is_open)

## Tab 键：开着就全关掉，没开就弹菜单
func toggle_panel() -> void:
	if ui_open():
		close_menu()
		close_panel()
		if dlg != null:
			dlg.close()
	else:
		open_menu()

func open_menu() -> void:
	if _modal == "menu":
		return
	close_panel()
	if dlg != null:
		dlg.close()
	_modal = "menu"
	_backdrop.color = Color(0, 0, 0, 0.28)
	_backdrop.visible = true
	_menu.visible = true
	refresh()

func close_menu() -> void:
	if _modal == "menu":
		_modal = ""
	_menu.visible = false
	_backdrop.visible = panel_open

func open_panel() -> void:
	close_menu()
	_modal = "items"
	panel_open = true
	refresh()
	_backdrop.color = Color(0, 0, 0, 0.55)
	_backdrop.visible = true
	_box.visible = true
	_toggle_btn.visible = false

func close_panel() -> void:
	if _modal == "items":
		_modal = ""
	panel_open = false
	_backdrop.visible = false
	_box.visible = false
	_toggle_btn.visible = true
	refresh()

## 存档 / 读档框（标题页的「读档」按钮和菜单里都走这里）
func open_slots(which: String) -> void:
	close_menu()
	close_panel()
	_toggle_btn.visible = false
	dlg.open(which)

func _on_dialog_closed() -> void:
	_toggle_btn.visible = true

## 提示条：屏幕上方弹一句，几秒后自己消失
func flash(msg: String) -> void:
	if msg == "":
		return
	_toast_label.text = msg.split("\n")[0]
	_toast.visible = true
	_toast_left = 4.0

func _process(delta: float) -> void:
	if _toast_left > 0.0:
		_toast_left -= delta
		if _toast_left <= 0.0:
			_toast_left = 0.0
			_toast.visible = false

func _on_backdrop_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			close_menu()
			close_panel()

# ---------------------------------------------------------------- 界面

func _build() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	_toast = PanelContainer.new()
	_toast.add_theme_stylebox_override("panel", UiSkin.bar(false, 2))
	_toast.position = TOAST_POS
	_toast.size = TOAST_SIZE
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toast.visible = false
	add_child(_toast)
	_toast_label = _label("", 14, UiSkin.RED)
	_toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_toast.add_child(_toast_label)

	_backdrop = ColorRect.new()
	_backdrop.color = Color(0, 0, 0, 0.55)
	_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	_backdrop.visible = false
	_backdrop.gui_input.connect(_on_backdrop_input)
	add_child(_backdrop)

	_build_menu()
	_build_items()

	dlg = SaveDialog.new()
	add_child(dlg)
	dlg.setup(main, plaque_font)
	dlg.message.connect(flash)
	dlg.closed.connect(_on_dialog_closed)

	# 菜单按钮最后加：永远画在最上面，弹菜单、开道具框的时候也点得到
	_toggle_btn = Button.new()
	_toggle_btn.focus_mode = Control.FOCUS_NONE
	_toggle_btn.text = "菜单"
	_toggle_btn.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	_toggle_btn.add_theme_font_override("font", plaque_font)
	# 字号和边距都是卡着 20px 高度定的：再大一点按钮就会被撑高，压到「跳过情节」上
	_toggle_btn.add_theme_font_size_override("font_size", 12)
	_toggle_btn.add_theme_color_override("font_color", UiSkin.RED)
	_toggle_btn.add_theme_color_override("font_hover_color", UiSkin.RED_HOT)
	_toggle_btn.add_theme_stylebox_override("normal", UiSkin.bar(false, 0))
	_toggle_btn.add_theme_stylebox_override("hover", UiSkin.bar(true, 0))
	_toggle_btn.add_theme_stylebox_override("pressed", UiSkin.bar(true, 0))
	_toggle_btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_toggle_btn.pressed.connect(_on_toggle)
	_toggle_btn.position = MENU_POS
	add_child(_toggle_btn)
	# size 得在进树之后设：Control 的 size 只会被「最小尺寸」往上顶、不会自己缩回去，
	# 而最小尺寸要等节点进了树、主题缓存生效才是我们这套字体算出来的值
	# （早设一步就会按默认主题的字号算成 31px 高，多出来的 11px 正好压到「跳过情节」上）。
	_toggle_btn.size = MENU_SIZE

## 点右上角那块木牌：开着就收起来，没开就弹出来
func _on_toggle() -> void:
	if _modal == "menu":
		close_menu()
	else:
		open_menu()

## 菜单：一竖排木牌，和标题页那几块一个长相
func _build_menu() -> void:
	_menu = Control.new()
	_menu.position = MENU_DOWN
	_menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_menu.visible = false
	add_child(_menu)
	var texts := ["存档", "读档", "隐藏道具", "关闭"]
	for i in range(texts.size()):
		var b := UiSkin.text_button(str(texts[i]), plaque_font, 17, MENU_ITEM)
		b.position = Vector2(0, i * (MENU_ITEM.y + MENU_GAP))
		b.size = MENU_ITEM
		b.pressed.connect(_on_menu_item.bind(str(texts[i])))
		_menu.add_child(b)
		if i == 2:
			_menu_items = b

func _on_menu_item(what: String) -> void:
	match what:
		"存档":
			open_slots("save")
		"读档":
			open_slots("load")
		"隐藏道具":
			open_panel()
		"关闭":
			close_menu()

func _build_items() -> void:
	_box = PanelContainer.new()
	_box.add_theme_stylebox_override("panel", UiSkin.board())
	_box.mouse_filter = Control.MOUSE_FILTER_STOP
	_box.visible = false
	add_child(_box)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 5)
	_box.add_child(col)

	var head := HBoxContainer.new()
	col.add_child(head)
	head.add_child(_label("隐藏道具", 24, UiSkin.RED))
	_progress = _label("", 14, UiSkin.INK)
	_progress.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_progress.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_progress.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(_progress)

	col.add_child(_sep())

	for s in sets:
		col.add_child(_label(str(s.get("title", "")), 16, UiSkin.RED))
		col.add_child(_label(str(s.get("note", "")), 11, UiSkin.INK_NOTE))
		var grid := GridContainer.new()
		grid.columns = maxi(1, int(s.get("cols", 2)))
		grid.add_theme_constant_override("h_separation", 8)
		grid.add_theme_constant_override("v_separation", 3)
		grid.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.add_child(grid)
		for it in s.get("items", []):
			grid.add_child(_item_cell(it))

	col.add_child(_sep())
	var foot := HBoxContainer.new()
	col.add_child(foot)
	var back := UiSkin.text_button("关闭", plaque_font, 17, Vector2(96, 40))
	back.pressed.connect(close_panel)
	foot.add_child(back)
	col.add_child(_label("存档、读档在右上角的菜单里，随时可以存；F5 快速存档，F9 快速读档",
		12, UiSkin.INK_NOTE))

	_box.size = ITEMS_SIZE
	_box.position = ITEMS_POS

func _item_cell(it: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.custom_minimum_size = Vector2(CELL_W, 18)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var k := str(it.get("k", ""))
	var nm := _label(str(it.get("name", "?")), 14, UiSkin.INK)
	nm.custom_minimum_size = Vector2(NAME_W, 18)
	nm.clip_text = true
	var fx := _label(str(it.get("fx", "")), 12, UiSkin.INK_NOTE)
	# 效果这一格给死宽度：不给的话 BoxContainer 只会按最小宽度摆，文字会被裁掉
	fx.custom_minimum_size = Vector2(CELL_W - NAME_W - 6.0, 18)
	fx.clip_text = true
	row.add_child(nm)
	row.add_child(fx)
	_cells[k] = {"n": nm, "f": fx, "name": str(it.get("name", "?")), "fx": str(it.get("fx", ""))}
	return row

func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", plaque_font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _sep() -> Control:
	var r := ColorRect.new()
	r.color = UiSkin.SEP
	r.custom_minimum_size = Vector2(0, 1)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r

# ---------------------------------------------------------------- 刷新

func refresh() -> void:
	var total := 0
	var got := 0
	for k in _cells:
		total += 1
		var cell: Dictionary = _cells[k]
		var has := GameState.has_item(str(k))
		if has:
			got += 1
		var nm: Label = cell["n"]
		var fx: Label = cell["f"]
		nm.text = str(cell["name"]) if has else "？？？"
		nm.add_theme_color_override("font_color", UiSkin.INK if has else UiSkin.INK_DIM)
		fx.text = str(cell["fx"]) if has else ""
	_progress.text = "已收集 %d 件，共 %d 件" % [got, total]
	if _menu_items != null:
		_menu_items.text = "隐藏道具 %d/%d" % [got, total]
