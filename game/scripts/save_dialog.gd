class_name SaveDialog
extends Control
## 存档 / 读档框：三个档位，点哪个存（读）哪个。
##
## 存档时点一个已经存过的档位，会先变成「再点一下覆盖」问一遍 ——
## 免得手一抖把前面的进度盖掉；三秒不点就自己变回去。
## 读档时空档位是灰的，点不动。
##
## 长相和标题页那几块菜单木牌一样（见 scripts/ui_skin.gd）。

signal closed
signal message(text: String)      ## 要主界面闪一句提示

const BOX_SIZE := Vector2(470, 332)
const ROW_H := 46.0
const CONFIRM_SECONDS := 3.0

var main: Node = null
var font: Font = null             ## 木牌上的字（隶书，缺的字走系统兜底）

var mode := "save"                ## "save" / "load"
var is_open := false

var _backdrop: ColorRect
var _box: PanelContainer
var _title: Label
var _rows: Array[Button] = []
var _foot: Label
var _confirm := -1                ## 正在问「覆盖？」的档位
var _confirm_left := 0.0

func setup(main_node: Node, panel_font: Font) -> void:
	main = main_node
	font = panel_font
	_build()

# ---------------------------------------------------------------- 开关

func open(which: String) -> void:
	mode = which
	is_open = true
	_confirm = -1
	_confirm_left = 0.0
	_fit()
	_refresh()
	_backdrop.visible = true
	_box.visible = true

## 这层黑幕要盖满整个画面。锚点是在刚 new 出来、父节点还没定下大小时算的，
## 那次会算成 0x0（黑幕就整块看不见），所以每次打开都按父节点的尺寸重摆一遍。
func _fit() -> void:
	var p := Vector2(800, 600)
	var parent := get_parent()
	if parent is Control and (parent as Control).size.x > 0.0:
		p = (parent as Control).size
	size = p
	_backdrop.position = Vector2.ZERO
	_backdrop.size = p

func close() -> void:
	if not is_open:
		return
	is_open = false
	_confirm = -1
	_backdrop.visible = false
	_box.visible = false
	closed.emit()

func _process(delta: float) -> void:
	if _confirm_left > 0.0:
		_confirm_left -= delta
		if _confirm_left <= 0.0:
			_confirm_left = 0.0
			_confirm = -1
			_refresh()

func _on_backdrop_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			close()

# ---------------------------------------------------------------- 界面

func _build() -> void:
	# 这里四个锚点都钉在左上角：整块画面是靠自己量父节点尺寸摆的（_fit），
	# 要是用「铺满父节点」的锚点，Godot 会在 _ready 之后按当时（还是 0）的父节点尺寸
	# 把 size 改回去，黑幕就成了 0x0、整块看不见。
	set_anchors_preset(Control.PRESET_TOP_LEFT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	_backdrop = ColorRect.new()
	_backdrop.color = Color(0, 0, 0, 0.55)
	_backdrop.set_anchors_preset(Control.PRESET_TOP_LEFT)
	_backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	_backdrop.visible = false
	_backdrop.gui_input.connect(_on_backdrop_input)
	add_child(_backdrop)

	_box = PanelContainer.new()
	_box.add_theme_stylebox_override("panel", UiSkin.board())
	_box.mouse_filter = Control.MOUSE_FILTER_STOP
	_box.visible = false
	_box.size = BOX_SIZE
	_box.position = (Vector2(800, 600) - BOX_SIZE) * 0.5
	add_child(_box)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 9)
	_box.add_child(col)

	_title = _label("存档", 26, UiSkin.RED)
	col.add_child(_title)
	col.add_child(_sep())

	for i in range(1, GameState.SAVE_SLOTS + 1):
		var b := UiSkin.text_button("", font, 20, Vector2(0, ROW_H))
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_on_slot.bind(i))
		col.add_child(b)
		_rows.append(b)

	col.add_child(_sep())
	var foot := HBoxContainer.new()
	foot.add_theme_constant_override("separation", 12)
	col.add_child(foot)
	var back := UiSkin.text_button("关闭", font, 18, Vector2(96, 40))
	back.pressed.connect(close)
	foot.add_child(back)
	_foot = _label("", 13, UiSkin.INK_NOTE)
	_foot.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_foot.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foot.add_child(_foot)
	_fit()

# ---------------------------------------------------------------- 刷新

func _refresh() -> void:
	_title.text = "存档" if mode == "save" else "读档"
	_foot.text = ("点一个档位存进去；存过的会再问一遍，免得存错"
		if mode == "save" else "点一个档位读回来；灰色的还是空档位")
	for i in range(1, GameState.SAVE_SLOTS + 1):
		var b: Button = _rows[i - 1]
		var info := GameState.slot_info(i)
		var nm := GameState.slot_name(i)
		if not bool(info["exists"]):
			b.text = "%s　　（空档位）" % nm
			# 空档位写灰字，一眼看得出哪儿还空着（存档时照样点得动）
			b.add_theme_color_override("font_color", UiSkin.INK_DIM)
			b.add_theme_color_override("font_hover_color", UiSkin.RED)
		else:
			var t := str(info["time"])
			b.text = "%s　　第 %d 天　%s" % [nm, int(info["day"]), t if t != "" else "已存"]
			b.add_theme_color_override("font_color", UiSkin.RED)
			b.add_theme_color_override("font_hover_color", UiSkin.RED_HOT)
		if mode == "load":
			b.disabled = not bool(info["exists"])
		else:
			b.disabled = false
			if _confirm == i:
				b.text = "%s　再点一下重写" % nm

func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
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

# ---------------------------------------------------------------- 点档位

func _on_slot(slot: int) -> void:
	if main == null:
		return
	if mode == "load":
		var got := str(main.do_load(slot))
		close()
		message.emit(got)
		return
	# 存档：已经存过的档位先问一遍，再点一下才真的盖
	if GameState.has_save(slot) and _confirm != slot:
		_confirm = slot
		_confirm_left = CONFIRM_SECONDS
		_refresh()
		return
	_confirm = -1
	_confirm_left = 0.0
	var msg := str(main.do_save(slot))
	_refresh()
	message.emit(msg)
