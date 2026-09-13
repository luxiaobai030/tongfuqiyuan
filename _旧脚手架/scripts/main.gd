extends Control
## 《同福奇缘》主界面 —— 角色属性面板 + 全局状态 + 存档

const DataSchema := preload("res://scripts/data_schema.gd")

const COL_BG     := Color("#24150e")
const COL_PANEL  := Color("#3b2418")
const COL_GOLD   := Color("#f4c875")
const COL_TEXT   := Color("#f7e6c8")
const COL_DIM    := Color("#a8917a")

var current_char: String = "ZG"
var header: Label
var attr_view: RichTextLabel
var global_view: RichTextLabel
var log_view: RichTextLabel
var char_bar: HBoxContainer
var day_label: Label
var char_buttons: Dictionary = {}

func _ready() -> void:
	GameState.changed.connect(_refresh)
	_build()
	_refresh()

# ---------------- 构建界面 ----------------

func _build() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)

	var bg := ColorRect.new()
	bg.color = COL_BG
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var root := MarginContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("margin_left", 16)
	root.add_theme_constant_override("margin_right", 16)
	root.add_theme_constant_override("margin_top", 12)
	root.add_theme_constant_override("margin_bottom", 12)
	add_child(root)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	root.add_child(col)

	# ---- 标题 ----
	header = Label.new()
	header.text = "同 福 奇 缘"
	header.add_theme_font_size_override("font_size", 28)
	header.add_theme_color_override("font_color", COL_GOLD)
	header.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(header)

	day_label = Label.new()
	day_label.add_theme_font_size_override("font_size", 16)
	day_label.add_theme_color_override("font_color", COL_TEXT)
	day_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(day_label)

	# ---- 角色页签 ----
	char_bar = HBoxContainer.new()
	char_bar.alignment = BoxContainer.ALIGNMENT_CENTER
	char_bar.add_theme_constant_override("separation", 6)
	col.add_child(char_bar)
	for prefix in DataSchema.CHAR_ORDER:
		var b := Button.new()
		b.text = str(DataSchema.CHAR_INFO[prefix]["name"])
		b.custom_minimum_size = Vector2(122, 44)
		b.add_theme_font_size_override("font_size", 16)
		b.pressed.connect(_on_char_pressed.bind(prefix))
		char_bar.add_child(b)
		char_buttons[prefix] = b

	# ---- 主体两栏 ----
	var split := HBoxContainer.new()
	split.add_theme_constant_override("separation", 12)
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(split)

	var left := _panel("江 湖 账 目")
	left.custom_minimum_size = Vector2(380, 0)
	split.add_child(left)
	global_view = _rich(_body(left), 16)

	var right := _panel("人 物 属 性")
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(right)
	attr_view = _rich(_body(right), 18)

	# ---- 日志 ----
	var logp := _panel("近 况")
	logp.custom_minimum_size = Vector2(0, 140)
	col.add_child(logp)
	log_view = _rich(_body(logp), 14)

	# ---- 底栏 ----
	var bar := HBoxContainer.new()
	bar.alignment = BoxContainer.ALIGNMENT_CENTER
	bar.add_theme_constant_override("separation", 10)
	col.add_child(bar)
	_button(bar, "新的一局", _on_new)
	_button(bar, "睡 觉（下一天）", _on_next_day)
	_button(bar, "存 档", _on_save)
	_button(bar, "读 档", _on_load)

## 造一个带标题的面板，返回面板本身
func _panel(title: String) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = COL_PANEL
	sb.corner_radius_top_left = 6
	sb.corner_radius_top_right = 6
	sb.corner_radius_bottom_left = 6
	sb.corner_radius_bottom_right = 6
	sb.content_margin_left = 12
	sb.content_margin_right = 12
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	p.add_theme_stylebox_override("panel", sb)

	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)

	var t := Label.new()
	t.text = title
	t.add_theme_font_size_override("font_size", 15)
	t.add_theme_color_override("font_color", COL_GOLD)
	v.add_child(t)
	return p

## 取面板内部的内容容器
func _body(p: PanelContainer) -> VBoxContainer:
	return p.get_child(0) as VBoxContainer

func _rich(parent: Node, font_size: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.scroll_active = true
	r.size_flags_vertical = Control.SIZE_EXPAND_FILL
	r.add_theme_font_size_override("normal_font_size", font_size)
	r.add_theme_color_override("default_color", COL_TEXT)
	parent.add_child(r)
	return r

func _button(parent: Node, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(165, 44)
	b.add_theme_font_size_override("font_size", 16)
	b.pressed.connect(cb)
	parent.add_child(b)
	return b

# ---------------- 刷新 ----------------

func _refresh() -> void:
	day_label.text = "第 %d 天 / %d 天        金钱 %d 文        人气 %d        称号 %d 个" % [
		GameState.day, DataSchema.TOTAL_DAYS,
		GameState.get_var("money"), GameState.get_var("renqi"), GameState.titles.size(),
	]
	for prefix in char_buttons:
		char_buttons[prefix].modulate = Color.WHITE if prefix == current_char else Color(0.62, 0.62, 0.62)
	_refresh_attrs()
	_refresh_globals()
	_refresh_log()

func _refresh_attrs() -> void:
	var lines: PackedStringArray = []
	var info: Dictionary = DataSchema.CHAR_INFO[current_char]
	var color: String = info["color"]
	lines.append("[b][color=%s]%s[/color][/b]   [color=%s]%s[/color]" % [
		color, info["name"], COL_DIM.to_html(), info["role"],
	])
	lines.append("")
	for f in DataSchema.CHAR_FIELDS[current_char]:
		var key := str(current_char, "_", f[0])
		var val := GameState.get_var(key)
		if f[0] == "chenghao":
			lines.append("  %s：[color=%s]%s[/color]" % [
				f[1], color, "有" if val > 0 else "无",
			])
		else:
			lines.append("  %s：[b]%d[/b]" % [f[1], val])
	var has_skill := false
	for sk in DataSchema.SKILLS:
		if DataSchema.SKILLS[sk][1] == current_char:
			if not has_skill:
				lines.append("")
				lines.append("[color=%s]武 功[/color]" % COL_GOLD.to_html())
				has_skill = true
			lines.append("  %s：[b]Lv %d[/b]" % [DataSchema.SKILLS[sk][0], GameState.get_var(sk)])
	attr_view.text = "\n".join(lines)

func _refresh_globals() -> void:
	var lines: PackedStringArray = []
	for g in DataSchema.GLOBAL_FIELDS:
		lines.append("  %s： [b]%d[/b]" % [g[1], GameState.get_var(g[0])])
	global_view.text = "\n".join(lines)

func _refresh_log() -> void:
	var lines: PackedStringArray = []
	var start: int = maxi(0, GameState.log_lines.size() - 12)
	for i in range(start, GameState.log_lines.size()):
		lines.append(str("· ", GameState.log_lines[i]))
	log_view.text = "\n".join(lines)

# ---------------- 交互 ----------------

func _on_char_pressed(prefix: String) -> void:
	current_char = prefix
	_refresh()

func _on_new() -> void:
	GameState.new_game()

func _on_next_day() -> void:
	if GameState.day >= DataSchema.TOTAL_DAYS:
		GameState.add_log("一百天过去了，这一年就到这里。")
		GameState.changed.emit()
		return
	GameState.day += 1
	GameState.add_log("第 %d 天开始了。" % GameState.day)
	GameState.changed.emit()

func _on_save() -> void:
	GameState.save_game()
	_refresh()

func _on_load() -> void:
	if not GameState.load_game():
		GameState.add_log("没有找到存档。")
	_refresh()
