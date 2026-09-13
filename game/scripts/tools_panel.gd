extends Control
## 工具箱（移植版额外加的，原版没有）：存档 / 读档 + 隐藏道具图鉴
##
## 右上角常驻一个小开关，上面写着已收集的进度；点它或按 Tab 弹出面板。
## 面板里列出全部隐藏道具：拿到过的显示名字和效果，没拿到的显示 ？？？。
## 面板打开时用一层半透明黑幕挡住下面的游戏画面 —— 底下的按钮点不到，
## 游戏按键（z x c v b n 等）也不再生效，免得看道具的时候把战斗指令发出去。
##
## 道具从来不看「玩家有没有见过」，只看游戏自己的判定点：
## 帧 297 / 830 / 1317 各送一件倾城装，按钮 1288 是收下羞花衫，
## 帧 968（淘宝成功）按 TBWP 随机数决定淘到哪件珍品。

const PANEL_POS := Vector2(70, 64)
const PANEL_SIZE := Vector2(660, 470)
## 右上角：贴在最上沿，正好躲开剧情帧的「跳过情节」按钮（它在 y=22.8 往下）
const TOGGLE_POS := Vector2(664, 1)
const TOGGLE_SIZE := Vector2(132, 19)
const CELL_W := 310.0
const NAME_W := 150.0

const C_BG        := Color(0.10, 0.078, 0.055, 0.97)
const C_BORDER    := Color(0.78, 0.64, 0.36)
const C_TITLE     := Color(0.96, 0.86, 0.60)
const C_TEXT      := Color(0.94, 0.90, 0.78)
const C_FX        := Color(0.72, 0.66, 0.52)
const C_DIM       := Color(0.55, 0.51, 0.44)
const C_NOTE      := Color(0.58, 0.54, 0.46)
const C_BTN       := Color(0.23, 0.18, 0.12, 1.0)
const C_BTN_HOVER := Color(0.35, 0.27, 0.16, 1.0)

var main: Node = null
var panel_font: Font = null
## 正文用的字体（游戏原来那个）：它不含拉丁字母，字母和「·」会走系统字体兜底，
## 显示比隶书那套干净 —— 隶书里 a 的字形和「·」是坏的，看着像乱码。
var ui_font: Font = null

var sets: Array = []
var by_frame: Dictionary = {}      # 帧号 → [道具键, ...]
var by_button: Dictionary = {}     # 按钮 id → [道具键, ...]
var by_tbwp: Dictionary = {}       # 帧号 → [[随机数下限, 上限, 道具键], ...]

var panel_open: bool = false

var _toggle: Button
var _backdrop: ColorRect
var _box: PanelContainer
var _progress: Label
var _status: Label
var _cells: Dictionary = {}        # 道具键 → {n, f, name, fx}
var _msg_left: float = 0.0

func setup(main_node: Node, font: Font, cfg: Dictionary) -> void:
	main = main_node
	panel_font = font
	ui_font = main.get("default_font")
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

# ---------------------------------------------------------------- 开关与面板

func toggle_panel() -> void:
	if panel_open:
		close_panel()
	else:
		open_panel()

func open_panel() -> void:
	panel_open = true
	_msg_left = 0.0
	refresh()
	_backdrop.visible = true
	_box.visible = true

func close_panel() -> void:
	panel_open = false
	_msg_left = 0.0
	_backdrop.visible = false
	_box.visible = false
	refresh()

## 面板开着就显示在面板上，关着就顶在右上角开关上，几秒后自动消失
func flash(msg: String) -> void:
	if msg == "":
		return
	if panel_open:
		_status.text = msg
		_msg_left = 4.0
	else:
		# 关着的时候提示就顶在右上角的开关上，那里窄，只留第一句（「已存档」这种）
		_toggle.text = msg.split(" · ")[0]
		_msg_left = 3.0

func _process(delta: float) -> void:
	if _msg_left > 0.0:
		_msg_left -= delta
		if _msg_left <= 0.0:
			_msg_left = 0.0
			refresh()

func _on_backdrop_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			close_panel()

# ---------------------------------------------------------------- 界面

func _build() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	_backdrop = ColorRect.new()
	_backdrop.color = Color(0, 0, 0, 0.55)
	_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	_backdrop.visible = false
	_backdrop.gui_input.connect(_on_backdrop_input)
	add_child(_backdrop)

	_box = PanelContainer.new()
	_box.add_theme_stylebox_override("panel", _panel_style())
	_box.mouse_filter = Control.MOUSE_FILTER_STOP
	_box.visible = false
	add_child(_box)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 5)
	_box.add_child(col)

	var head := HBoxContainer.new()
	col.add_child(head)
	head.add_child(_label("隐藏道具", 22, C_TITLE))
	_progress = _label("", 14, C_TEXT)
	_progress.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_progress.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_progress.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(_progress)

	col.add_child(_sep())

	for s in sets:
		col.add_child(_label(str(s.get("title", "")), 16, C_TITLE))
		col.add_child(_label(str(s.get("note", "")), 11, C_NOTE))
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
	foot.add_theme_constant_override("separation", 8)
	col.add_child(foot)
	foot.add_child(_btn("存档", _do_save))
	foot.add_child(_btn("读档", _do_load))
	foot.add_child(_btn("关闭", close_panel))
	_status = _label("", 12, C_TEXT)
	_status.add_theme_font_override("font", ui_font if ui_font != null else panel_font)
	_status.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foot.add_child(_status)

	var hint := _label("Tab 或右上角开关：打开关闭本框 · F5 存档 · F9 读档", 11, C_NOTE)
	hint.add_theme_font_override("font", ui_font if ui_font != null else panel_font)
	col.add_child(hint)

	_box.size = PANEL_SIZE
	_box.position = PANEL_POS

	# 开关最后加：永远画在最上面，面板打开时也点得到
	_toggle = Button.new()
	_toggle.focus_mode = Control.FOCUS_NONE
	_toggle.position = TOGGLE_POS
	_toggle.size = TOGGLE_SIZE
	_toggle.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	_toggle.add_theme_font_override("font", panel_font)
	_toggle.add_theme_font_size_override("font_size", 11)
	_toggle.add_theme_color_override("font_color", C_TITLE)
	_toggle.add_theme_color_override("font_hover_color", Color(1, 1, 1))
	# 开关压在画面上，给文字描一圈黑边，压到花哨的背景也看得清
	_toggle.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	_toggle.add_theme_constant_override("shadow_offset_x", 1)
	_toggle.add_theme_constant_override("shadow_offset_y", 1)
	_toggle.add_theme_stylebox_override("normal", _btn_style(Color(0.05, 0.04, 0.03, 0.55), 1))
	_toggle.add_theme_stylebox_override("hover", _btn_style(Color(0.05, 0.04, 0.03, 0.80), 1))
	_toggle.add_theme_stylebox_override("pressed", _btn_style(Color(0.05, 0.04, 0.03, 0.88), 1))
	_toggle.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_toggle.pressed.connect(toggle_panel)
	add_child(_toggle)

func _item_cell(it: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.custom_minimum_size = Vector2(CELL_W, 18)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var k := str(it.get("k", ""))
	var nm := _label(str(it.get("name", "?")), 14, C_TEXT)
	nm.custom_minimum_size = Vector2(NAME_W, 18)
	nm.clip_text = true
	var fx := _label(str(it.get("fx", "")), 12, C_FX)
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
	l.add_theme_font_override("font", panel_font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _btn(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.add_theme_font_override("font", panel_font)
	b.add_theme_font_size_override("font_size", 14)
	b.add_theme_color_override("font_color", C_TEXT)
	b.add_theme_color_override("font_hover_color", Color(1, 1, 1))
	b.custom_minimum_size = Vector2(84, 28)
	b.add_theme_stylebox_override("normal", _btn_style(C_BTN, 1))
	b.add_theme_stylebox_override("hover", _btn_style(C_BTN_HOVER, 1))
	b.add_theme_stylebox_override("pressed", _btn_style(C_BTN_HOVER, 1))
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.pressed.connect(cb)
	return b

func _panel_style() -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = C_BG
	s.border_color = C_BORDER
	s.set_border_width_all(2)
	s.set_corner_radius_all(6)
	s.set_content_margin_all(16)
	return s

func _btn_style(bg: Color, border: int) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = C_BORDER
	s.set_border_width_all(border)
	s.set_corner_radius_all(4)
	s.content_margin_left = 8
	s.content_margin_right = 8
	s.content_margin_top = 2
	s.content_margin_bottom = 2
	return s

func _sep() -> Control:
	var r := ColorRect.new()
	r.color = Color(0.55, 0.45, 0.26, 0.75)
	r.custom_minimum_size = Vector2(0, 1)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r

func _do_save() -> void:
	if main == null:
		return
	refresh()
	flash(main.do_save())

func _do_load() -> void:
	if main == null:
		return
	refresh()
	flash(main.do_load())

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
		nm.add_theme_color_override("font_color", C_TEXT if has else C_DIM)
		fx.text = str(cell["fx"]) if has else ""
	_progress.text = "已收集 %d 件，共 %d 件" % [got, total]
	_toggle.text = "隐藏道具 %d/%d" % [got, total]
	_status.text = ""
