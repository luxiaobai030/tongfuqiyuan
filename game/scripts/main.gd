extends Control
## 同福奇缘 · Godot 移植版主程序
##
## 原版是 800x600 / 19fps / 4907 帧的 Flash 时间轴游戏。这里把时间轴还原成一个逐帧推进的
## 状态机：每 1/19 秒推进一帧，遇到脚本帧就执行由 ActionScript 转译来的逻辑
## （scripts/ported/logic.gd），脚本里的 stop() 会让时间轴停下等玩家操作。
##
## 画面由四层拼成：
##   1. 背景层 —— 去重后的纯美术画面，已经不含“会自己动的角色”（assets/bg）
##   2. 角色层 —— 30 个会自己播动画的角色（assets/clips），各自有独立的时间轴（data/clips.json）
##   3. 控件层 —— 动态文本框（Label）+ 按钮热区（Button），数据来自 data/ui.json
## （原版美术里的静态文字本来就在背景层那张图里，不用再叠一层）
##
## 角色层是关键：原版里这些 MovieClip 有自己的时间轴，主时间轴 stop() 等玩家点按钮时它们照样在动
## （客栈里走来走去的伙计、战斗里出招的人物都是这样）。移植版如果只播“整幅逐帧画面”，
## 主时间轴一停角色就跟着一起冻住，所以必须把它们单独拿出来按各自的播放头画。
##
## 额外加的（原版没有，见 scripts/tools_panel.gd）：存档 / 读档（F5 / F9，右上角开关里也有按钮）、
## 隐藏道具图鉴（右上角常驻开关，按 Tab 也能开关，没拿到的道具显示 ？？？）。

const TOTAL_FRAMES := 4907
const TICK := 1.0 / 19.0
const TEX_CACHE_MAX := 64
## 超过这个时长的音频当背景音乐（循环播放、同一首不重复起播），
## 其余当音效。原版 5 首 BGM 都 ≥39 秒，最长的音效只有 6.4 秒。
const MUSIC_MIN_SECONDS := 20.0
## 角色贴图的显存预算：贴图集最多同时留几张、逐帧图最多占多少字节
const CLIP_ATLAS_KEEP := 6
const CLIP_OBJ_BYTES := 48 * 1024 * 1024

const FONT_FALLBACK := {180: 15, 1072: 171}
## 原版里 180(Arial) / 1072(黑体) 是没内嵌字形的设备字体，优先用系统同名字体
const DEVICE_FONTS := {180: ["Arial"], 1072: ["黑体", "SimHei", "Microsoft YaHei"]}
const ALIGN_MAP := {0: HORIZONTAL_ALIGNMENT_LEFT, 1: HORIZONTAL_ALIGNMENT_RIGHT, 2: HORIZONTAL_ALIGNMENT_CENTER}

@onready var bg_rect: TextureRect = $BG
@onready var clip_view: Control = $ClipView
@onready var label_root: Control = $Labels
@onready var btn_root: Control = $Buttons
@onready var over_rect: TextureRect = $Over
@onready var tools: Control = $Tools

var logic: RefCounted
var frames_data: Dictionary = {}
var ui_data: Dictionary = {}
var tf_data: Dictionary = {}
var btn_over: Dictionary = {}        # 按钮 id → 悬停态贴图信息（按钮自己换图的那部分）
var hidden_data: Dictionary = {}     # 帧号 → 这一帧被弹窗盖住、要藏起来的文本框
var key_map: Dictionary = {}
var sound_frames: Dictionary = {}
var sound_files: Dictionary = {}
var fonts: Dictionary = {}
var default_font: FontFile
var panel_font: Font              # 工具箱面板用的字体（内嵌隶书 + 系统字体兜底）
var _items_cfg: Dictionary = {}   # data/hidden_items.json：隐藏道具表

var beats: PackedInt32Array = PackedInt32Array()
var clips_data: Dictionary = {}      # 角色 id → 贴图信息（尺寸/摆放基准/自身时间轴）
var clip_events: Dictionary = {}     # 主帧号-1 → 那一帧对角色层的改动
var clip_names: Dictionary = {}      # 原版给角色起的名字 → 角色 id（剧本里点名播动画用）
var clip_state: Dictionary = {}      # 深度 → {id, ph, x, y, sx, sy, held}
var _clip_dirty: bool = false
var _atlas: Dictionary = {}          # 角色 id → {tex, used, bytes}   贴图集（小角色）
var _atlas_cell: Dictionary = {}     # "角色id:帧" → AtlasTexture      贴图集里的一格
var _obj: Dictionary = {}            # 路径 → Texture2D               逐帧图（整屏大角色）
var _obj_order: Array = []
var _obj_bytes: int = 0
var _clip_tick_no: int = 0
var cur: int = 1
var pending: int = 0
var halted: bool = true
var accum: float = 0.0
var dirty: bool = true

var _items: Array = []
var _tex_cache: Dictionary = {}
var _tex_order: Array = []
var _sound_cache: Dictionary = {}
var _music: AudioStreamPlayer
var _music_path: String = ""
var _sfx: Array[AudioStreamPlayer] = []
var _sfx_next: int = 0
var _hover_id: int = -1
var _over_tex: Dictionary = {}

func _ready() -> void:
	randomize()
	frames_data = _load_json("res://data/frames.json", {})
	ui_data = _load_json("res://data/ui.json", {})
	tf_data = _load_json("res://data/textfields.json", {})
	btn_over = _load_json("res://data/buttons.json", {})
	hidden_data = _load_json("res://data/hidden.json", {})
	_items_cfg = _load_json("res://data/hidden_items.json", {})
	key_map = _load_json("res://data/keys.json", {})
	var snd: Dictionary = _load_json("res://data/sounds.json", {})
	sound_frames = snd.get("frames", {})
	sound_files = snd.get("sounds", {})
	var cj: Dictionary = _load_json("res://data/clips.json", {})
	clips_data = cj.get("clips", {})
	clip_events = cj.get("events", {})
	clip_names = cj.get("names", {})
	clip_view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	clip_view.draw_fn = func(ci): _draw_clips(ci)
	for v in _load_json("res://data/beats.json", []):
		beats.append(int(v))
	_load_fonts()
	_setup_audio()
	logic = load("res://scripts/ported/logic.gd").new()
	logic.vars = GameState.vars
	logic.jump = _goto
	# 剧本里对角色动画的点名（如 dr_boos.gotoAndPlay(24)）交给角色层执行
	logic.clip_go_cb = _clip_go
	logic.clip_play_cb = _clip_play
	logic.clip_stop_cb = _clip_stop
	tools.setup(self, panel_font, _items_cfg)
	_enter_frame(1)
	_drain()

func _load_json(path: String, fallback):
	if not FileAccess.file_exists(path):
		push_warning("缺少数据文件: " + path)
		return fallback
	var f := FileAccess.open(path, FileAccess.READ)
	var txt := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(txt)
	return fallback if parsed == null else parsed

func _load_fonts() -> void:
	for fid in [15, 34, 171, 174, 1192, 1198]:
		var path := "res://assets/fonts/f%d.ttf" % fid
		if ResourceLoader.exists(path):
			fonts[fid] = load(path)
	for fid in DEVICE_FONTS:
		var f := _system_font(DEVICE_FONTS[fid])
		if f != null:
			fonts[fid] = f
	if fonts.has(171):
		default_font = fonts[171]
	elif fonts.size() > 0:
		default_font = fonts.values()[0]
	panel_font = _panel_font()

## 工具箱面板的字体：内嵌隶书（f34）字形最全，但缺「企 兑 序 灯 猬 瓶 瓷 窑 纹」这几个字
## （原版游戏里没用到），所以挂一圈系统字体当兜底，缺哪个字就从系统字体里取。
func _panel_font() -> Font:
	var base = fonts.get(34)
	if base == null:
		base = fonts.get(171, default_font)
	if base is FontFile:
		var fb: Array[Font] = []
		var sys := SystemFont.new()
		sys.font_names = PackedStringArray(["Microsoft YaHei", "微软雅黑", "SimHei",
			"黑体", "SimSun", "宋体", "Noto Sans CJK SC"])
		fb.append(sys)
		for fid in [171, 174, 1192]:
			var f = fonts.get(fid)
			if f != null and f != base:
				fb.append(f)
		(base as FontFile).fallbacks = fb
	return base

func _system_font(names: Array) -> FontFile:
	for n in names:
		var path := OS.get_system_font_path(str(n))
		if path == "":
			continue
		var f := FontFile.new()
		if f.load_dynamic_font(path) == OK:
			return f
	return null

func _setup_audio() -> void:
	_music = AudioStreamPlayer.new()
	add_child(_music)
	for i in 6:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_sfx.append(p)

# ---------------------------------------------------------------- 时间轴

func _goto(target) -> void:
	pending = int(target)

func _process(delta: float) -> void:
	_clip_tick_no += 1
	accum += delta
	var guard := 0
	while accum >= TICK and guard < 4:
		accum -= TICK
		guard += 1
		_tick()
	if dirty:
		_render()
	if _clip_dirty:
		_clip_dirty = false
		clip_view.queue_redraw()

func _tick() -> void:
	# 角色动画每帧都要往前走一格 —— 哪怕主时间轴 stop() 停住等玩家操作。
	# 原版就是这样：客栈里的人物、战斗里的人物在对话框/选择框弹出来的时候照样在动。
	_step_clips()
	if pending != 0:
		_drain()
		return
	if halted:
		return
	_enter_frame(cur + 1 if cur < TOTAL_FRAMES else 1)
	_drain()

func _drain() -> void:
	var guard := 0
	while pending != 0 and guard < 500:
		guard += 1
		var t := pending
		pending = 0
		_enter_frame(t)

func _enter_frame(n: int) -> void:
	cur = clampi(n, 1, TOTAL_FRAMES)
	_apply_clip_events(cur)
	logic.halted = false
	if logic.has_frame(cur):
		logic.run_frame(cur)
	halted = logic.halted
	if logic.want_stop_sounds:
		logic.want_stop_sounds = false
		_stop_all_sounds()
	tools.on_frame(cur)
	_play_frame_sounds(cur)
	dirty = true

# ---------------------------------------------------------------- 渲染

func _render() -> void:
	dirty = false
	var b := _beat_for(cur)
	_show_layer(b)
	_items = _items_for(cur, b)
	var want := {}
	var gone := _hidden_here()
	for it in _items:
		var box: Array = it.get("box", [])
		if box.size() < 4:
			continue
		# 原版里被弹出来的说明框/黑幕压在底下的文本框，这一帧本来就看不见
		if it.get("k", "") != "btn" and gone.has(str(it.get("var", ""))):
			continue
		want[_item_key(it)] = it
	_sync_nodes(btn_root, want, true)
	_sync_nodes(label_root, want, false)
	if _hover_id >= 0:
		_update_over()

## 这一帧有哪些文本框被后画上去的美术盖住了
func _hidden_here() -> Dictionary:
	var out := {}
	var lst = hidden_data.get(str(cur))
	if lst is Array:
		for v in lst:
			out[str(v)] = true
	return out

func _item_key(it: Dictionary) -> String:
	return "%s:%s" % [str(it.get("k", "")), str(it.get("id", -1))]

## 原版是「换帧就整套控件重建」，但那样会把鼠标底下的按钮一起换掉：
## 悬停/按下信号会错乱（发布版直接崩），鼠标移开的预览也接不上。
## 这里改成按 id 复用节点：位置和文字更新，节点本身留着。
func _sync_nodes(root: Control, want: Dictionary, is_btn: bool) -> void:
	var have := {}
	for c in root.get_children():
		var key := str(c.get_meta("key", ""))
		if key == "" or key.begins_with("btn:") != is_btn:
			continue
		if want.has(key):
			have[key] = c
		else:
			# 界面重建时把鼠标底下的按钮摘掉，Godot 会补一个 mouse_exited 信号。
			# 原版按钮被移出画面时不会触发 rollOut（鼠标并没有真的移开），所以这里打个标记，
			# 让 _on_hover_out 认出来忽略掉 —— 否则点了技能会立刻被 rollOut 拉回技能菜单。
			c.set_meta("dropped", true)
			if is_btn and int(c.get_meta("id", -1)) == _hover_id:
				_set_hover(-1)
			root.remove_child(c)
			c.queue_free()
	for key in want:
		if str(key).begins_with("btn:") != is_btn:
			continue
		var it: Dictionary = want[key]
		var box: Array = it.get("box")
		var node: Control = have.get(key)
		if node == null:
			if is_btn:
				node = _make_button(int(it.get("id", -1)), box)
			else:
				node = _make_label(int(it.get("id", -1)), str(it.get("var", "")), box)
			if node != null:
				node.set_meta("key", key)
			continue
		node.position = Vector2(float(box[0]), float(box[1]))
		node.size = Vector2(float(box[2]), float(box[3]))
		if not is_btn:
			(node as Label).text = _val_text(str(it.get("var", "")))

func _beat_for(n: int) -> int:
	if beats.is_empty():
		return n
	var lo := 0
	var hi := beats.size() - 1
	var res := beats[0]
	while lo <= hi:
		@warning_ignore("integer_division")
		var mid := (lo + hi) / 2
		if beats[mid] <= n:
			res = beats[mid]
			lo = mid + 1
		else:
			hi = mid - 1
	return res

func _show_layer(b: int) -> void:
	var bg_id = frames_data.get("bg", {}).get(str(b))
	bg_rect.texture = _tex("res://assets/bg/%s.webp" % str(bg_id)) if bg_id != null else null
	if bg_rect.texture != null:
		bg_rect.size = bg_rect.texture.get_size()

func _tex(path: String) -> Texture2D:
	if _tex_cache.has(path):
		return _tex_cache[path]
	if not ResourceLoader.exists(path):
		return null
	var t := ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE) as Texture2D
	if t == null:
		return null
	_tex_cache[path] = t
	_tex_order.append(path)
	while _tex_order.size() > TEX_CACHE_MAX:
		var old = _tex_order.pop_front()
		if old != path:
			_tex_cache.erase(old)
	return t

func _items_for(n: int, b: int) -> Array:
	var direct = ui_data.get(str(n))
	if direct is Array and not direct.is_empty():
		return direct
	var lo := b
	var hi := b
	for i in range(beats.size()):
		if beats[i] == b and i + 1 < beats.size():
			hi = beats[i + 1] - 1
			break
	for d in range(0, 40):
		for f in [n - d, n + d]:
			if f < lo or f > hi:
				continue
			var it = ui_data.get(str(f))
			if it is Array and not it.is_empty():
				return it
	return []

func _make_button(id: int, box: Array) -> Control:
	var btn := Button.new()
	btn.flat = true
	btn.focus_mode = Control.FOCUS_NONE
	btn.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	btn.position = Vector2(float(box[0]), float(box[1]))
	btn.size = Vector2(float(box[2]), float(box[3]))
	btn.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
	btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	btn.add_theme_stylebox_override("hover", _hover_style(0.10))
	btn.add_theme_stylebox_override("pressed", _hover_style(0.20))
	btn.pressed.connect(_on_button.bind(id))
	btn.mouse_entered.connect(_on_hover.bind(id))
	btn.mouse_exited.connect(_on_hover_out.bind(id, btn))
	btn.set_meta("id", id)
	btn_root.add_child(btn)
	return btn

func _hover_style(a: float) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = Color(1, 1, 1, a)
	s.set_corner_radius_all(3)
	return s

func _make_label(id: int, varname: String, box: Array) -> Control:
	if varname == "":
		return null
	var sty: Dictionary = tf_data.get(str(id), {})
	var lbl := Label.new()
	lbl.position = Vector2(float(box[0]), float(box[1]))
	lbl.size = Vector2(float(box[2]), float(box[3]))
	lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var fid := int(sty.get("font", -1))
	var f = fonts.get(fid)
	if f == null:
		f = fonts.get(FONT_FALLBACK.get(fid, 171), default_font)
	if f != null:
		lbl.add_theme_font_override("font", f)
	lbl.add_theme_font_size_override("font_size", maxi(6, int(round(float(sty.get("size", 20.0))))))
	lbl.add_theme_color_override("font_color", Color(str(sty.get("color", "#000000"))))
	lbl.horizontal_alignment = ALIGN_MAP.get(int(sty.get("align", 0)), HORIZONTAL_ALIGNMENT_LEFT)
	var ml := bool(sty.get("ml", false))
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_TOP if ml else VERTICAL_ALIGNMENT_CENTER
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART if bool(sty.get("ww", false)) else TextServer.AUTOWRAP_OFF
	lbl.clip_text = not ml
	lbl.set_meta("varname", varname)
	lbl.text = _val_text(varname)
	label_root.add_child(lbl)
	return lbl

func _val_text(varname: String) -> String:
	var v = logic.V(varname)
	if v == null:
		return ""
	if v is String:
		return v
	if v is bool:
		return "true" if v else "false"
	if v is float:
		if absf(v - roundf(v)) < 0.001:
			return str(int(roundf(v)))
		return String.num(v, 2)
	return str(v)

func _refresh_labels() -> void:
	for c in label_root.get_children():
		if c.has_meta("varname"):
			(c as Label).text = _val_text(str(c.get_meta("varname")))

# ---------------------------------------------------------------- 交互

func _on_button(id: int) -> void:
	logic.run_button(id)
	tools.on_button(id)
	_after_script()

func _on_hover(id: int) -> void:
	_set_hover(id)
	logic.run_button_hover(id)
	_after_script()

## 原版按钮的 on(rollOut)：鼠标移开时把画面切回去（技能说明、人物页预览等）
func _on_hover_out(id: int, btn: Control) -> void:
	# 界面重建时被删掉/挪走的按钮也会发这个信号，那种不算「鼠标真的移开了」
	if not is_instance_valid(btn):
		_set_hover(-1)
		return
	if bool(btn.get_meta("dropped", false)):
		_set_hover(-1)
		return
	if not btn.is_inside_tree():
		return
	# 画面重建时按钮被就地挪了位置，鼠标其实还压在上面，这也不算移开
	if Rect2(Vector2.ZERO, btn.size).has_point(btn.get_local_mouse_position()):
		return
	_set_hover(-1)
	logic.run_button_out(id)
	_after_script()

## 鼠标压着的按钮换成它的「悬停态」贴图（原版按钮自己有 up/over 两套画）。
## 客栈属性的说明框就是这样弹出来的：按钮的 over 状态里带着一整块说明。
func _set_hover(id: int) -> void:
	if _hover_id == id:
		return
	_hover_id = id
	_update_over()

func _update_over() -> void:
	var info = btn_over.get(str(_hover_id))
	var box := _box_of(_hover_id)
	if not (info is Dictionary) or box.size() < 4:
		over_rect.texture = null
		over_rect.visible = false
		return
	var key := str(_hover_id)
	var tex = _over_tex.get(key)
	if tex == null:
		var path := "res://assets/btnover/" + str(info.get("f", ""))
		if not ResourceLoader.exists(path):
			over_rect.visible = false
			return
		tex = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE) as Texture2D
		if tex == null:
			over_rect.visible = false
			return
		_over_tex[key] = tex
	var s := float(box[2]) / maxf(1.0, float(info.get("uw", 1)))
	var uc := Vector2(float(info.get("ux", 0)) + float(info.get("uw", 1)) * 0.5,
		float(info.get("uy", 0)) + float(info.get("uh", 1)) * 0.5)
	var center := Vector2(float(box[0]) + float(box[2]) * 0.5, float(box[1]) + float(box[3]) * 0.5)
	var origin := center - uc * s
	over_rect.position = origin + Vector2(float(info.get("ox", 0)), float(info.get("oy", 0))) * s
	over_rect.size = Vector2(float(info.get("w", 1)), float(info.get("h", 1))) * s
	over_rect.texture = tex
	over_rect.visible = true

func _box_of(bid: int) -> Array:
	for it in _items:
		if it.get("k", "") == "btn" and int(it.get("id", -1)) == bid:
			var b: Array = it.get("box", [])
			return b
	return []

func _after_script() -> void:
	_drain()
	halted = logic.halted
	if logic.want_stop_sounds:
		logic.want_stop_sounds = false
		_stop_all_sounds()
	if dirty:
		# 这个函数是从按钮的 pressed / mouse_entered 信号里调进来的，
		# 此时立刻重建界面会把正在发信号的按钮释放掉（发布版会直接崩）。
		# 推迟到本帧空闲时再重建。
		call_deferred("_render_if_dirty")
	else:
		_refresh_labels()

func _render_if_dirty() -> void:
	if dirty:
		_render()

# ---------------------------------------------------------------- 存档 / 读档

## 存档：变量表 + 隐藏道具收集进度 + 当前帧号，一起写进存档文件
func do_save() -> String:
	GameState.progress = {
		"frame": cur,
		"halted": halted,
		"time": Time.get_datetime_string_from_system(false, true),
	}
	if not GameState.save_game():
		return "存档失败"
	return "已存档 · 第 %d 天 · %s" % [int(logic.V("day")),
		str(GameState.progress["time"]).substr(11, 5)]

## 读档：把存档里的变量和收集进度装回来，画面跳回存档那一刻的帧。
## 这里故意不重跑那一帧的脚本 —— 脚本效果存档时已经算过一遍了，重跑会把属性再加一次。
func do_load() -> String:
	if not GameState.has_save():
		return "还没有存档"
	if not GameState.load_game():
		return "存档读不出来"
	_set_hover(-1)
	over_rect.visible = false
	pending = 0
	cur = clampi(int(GameState.progress.get("frame", cur)), 1, TOTAL_FRAMES)
	_apply_clip_events(cur)
	halted = bool(GameState.progress.get("halted", true))
	dirty = true
	_render()
	tools.refresh()
	return "已读档 · 第 %d 天" % int(logic.V("day"))

func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var k := event as InputEventKey
	match k.keycode:
		KEY_TAB:
			tools.toggle_panel()
			return
		KEY_ESCAPE:
			if tools.panel_open:
				tools.close_panel()
				return
		KEY_F5:
			tools.flash(do_save())
			return
		KEY_F9:
			tools.flash(do_load())
			return
	# 道具面板开着的时候，按键只在面板里用（z/x/c 这些别再传给游戏，免得背后放出技能）
	if tools.panel_open:
		return
	match k.keycode:
		KEY_SPACE, KEY_ENTER, KEY_KP_ENTER:
			_press_key("space")
		_:
			if k.unicode > 0:
				_press_key(char(k.unicode).to_lower())

func _press_key(key: String) -> void:
	var bid := find_key_button(key)
	if bid >= 0:
		_on_button(bid)

## 找到当前画面上绑定了某个按键的按钮（原版的 on(keyPress) 按钮）
func find_key_button(key: String) -> int:
	var raw = key_map.get(key, [])
	if not (raw is Array) or raw.is_empty():
		return -1
	var ids := {}
	for v in raw:
		ids[int(v)] = true
	for it in _items:
		if it.get("k", "") != "btn":
			continue
		var bid := int(it.get("id", -1))
		if ids.has(bid):
			return bid
	return -1

# ---------------------------------------------------------------- 声音

# ---------------------------------------------------------------- 角色动画层
#
# 原版根时间轴上有 30 个“会自己播动画的角色”。移植版把它们的每一帧都预先渲染好，
# 运行时按各自的播放头单独画在背景层上面：
#   * 每一格 +1 帧；角色自己时间轴上的 gotoAndPlay(1)（回到开头重播）和 stop()（停住定格）照原样执行。
#     战斗人物大多是“播一次就定格”，循环播放会让同福客栈的伙计在打架时也不停挥刀。
#   * 剧本点名（dr_boos.gotoAndPlay(24) 之类）通过 logic 回调过来，直接把播放头拨过去。
#   * 主时间轴 halt 时角色照样往前走，所以选择框弹出来时后面的人物不会僵住。

func _apply_clip_events(n: int) -> void:
	var evs = clip_events.get(str(n - 1))
	if not (evs is Array):
		return
	for e in evs:
		var d := int(e[0])
		var cid := int(e[1])
		if cid == -2:
			if clip_state.erase(d):
				_clip_dirty = true
		elif cid == -1:
			var mv = clip_state.get(d)
			if mv != null:
				# 只改动列出来的项：原版常用“只改透明度”的帧来做淡入淡出
				if e[2] != null: mv.x = float(e[2])
				if e[3] != null: mv.y = float(e[3])
				if e[4] != null: mv.sx = float(e[4])
				if e[5] != null: mv.sy = float(e[5])
				if e[6] != null: mv.a = float(e[6])
				_clip_dirty = true
		elif clips_data.has(str(cid)):
			var it := {"id": cid, "ph": 1, "x": float(e[2]), "y": float(e[3]),
				"sx": float(e[4]), "sy": float(e[5]), "a": float(e[6]), "held": false}
			_clip_enter(it)
			clip_state[d] = it
			_clip_dirty = true

## 走一格：先 +1 帧，再看角色自己时间轴上这一帧有没有脚本
func _clip_enter(it: Dictionary) -> void:
	var m: Dictionary = clips_data[str(it.id)]
	var j = m.get("jump")
	if j is Dictionary and j.has(str(it.ph)):
		it.ph = int(j[str(it.ph)])
	var st = m.get("stop")
	if st is Array and it.ph in st:
		it.held = true

func _step_clips() -> void:
	if clip_state.is_empty():
		return
	for d in clip_state:
		var it: Dictionary = clip_state[d]
		if it.held:
			continue
		var m: Dictionary = clips_data[str(it.id)]
		it.ph = int(it.ph) % int(m.n) + 1
		_clip_enter(it)
		_clip_dirty = true

## 剧本里点名让某个角色从第几帧开始播（原版：名字.gotoAndPlay(帧)）
func _clip_go(nm: String, target: int) -> void:
	_clip_apply(nm, func(it: Dictionary, m: Dictionary) -> void:
		it.ph = clampi(target, 1, int(m.n))
		it.held = false
		_clip_enter(it))

func _clip_play(nm: String) -> void:
	_clip_apply(nm, func(it: Dictionary, _m: Dictionary) -> void:
		it.held = false)

func _clip_stop(nm: String) -> void:
	_clip_apply(nm, func(it: Dictionary, _m: Dictionary) -> void:
		it.held = true)

func _clip_apply(nm: String, fn: Callable) -> void:
	var cid := int(clip_names.get(nm, -1))
	if cid < 0:
		return
	for d in clip_state:
		var it: Dictionary = clip_state[d]
		if int(it.id) == cid:
			fn.call(it, clips_data[str(cid)])
			_clip_dirty = true

func _draw_clips(ci: CanvasItem) -> void:
	var ds := clip_state.keys()
	ds.sort()
	for d in ds:
		var it: Dictionary = clip_state[d]
		var m: Dictionary = clips_data[str(it.id)]
		var tex := _clip_tex(int(it.id), int(it.ph))
		var a := float(it.get("a", 1.0))
		if tex == null or a <= 0.004:
			continue
		var r: Dictionary = m.get("ref", {})
		var kx := float(it.sx) / float(r.get("sx", 1.0))
		var ky := float(it.sy) / float(r.get("sy", 1.0))
		var x := float(it.x) + (float(m.x) - float(r.get("tx", 0.0))) * kx
		var y := float(it.y) + (float(m.y) - float(r.get("ty", 0.0))) * ky
		if absf(kx - 1.0) < 0.003 and absf(ky - 1.0) < 0.003:
			ci.draw_texture(tex, Vector2(roundf(x), roundf(y)), Color(1, 1, 1, a))
		else:
			ci.draw_texture_rect(tex, Rect2(x, y, float(m.w) * kx, float(m.h) * ky), false, Color(1, 1, 1, a))

func _clip_tex(cid: int, ph: int) -> Texture2D:
	var m: Dictionary = clips_data[str(cid)]
	if m.has("per"):
		# 整屏大角色：一帧一张图，用到哪张读哪张，显存占用恒定
		var p := "res://assets/clips/%d/%d.webp" % [cid, ph]
		var t = _obj.get(p)
		if t != null:
			return t
		if not ResourceLoader.exists(p):
			return null
		t = ResourceLoader.load(p, "", ResourceLoader.CACHE_MODE_IGNORE) as Texture2D
		if t == null:
			return null
		_obj[p] = t
		_obj_order.append(p)
		_obj_bytes += t.get_width() * t.get_height() * 4
		while _obj_bytes > CLIP_OBJ_BYTES and _obj_order.size() > 1:
			var old = _obj_order.pop_front()
			var ot = _obj.get(old)
			_obj.erase(old)
			if ot != null:
				_obj_bytes -= ot.get_width() * ot.get_height() * 4
		return t
	# 小角色：一张贴图集里所有帧，切格子用
	var e = _atlas.get(cid)
	if e == null:
		var ap := "res://assets/clips/" + str(m.file)
		if not ResourceLoader.exists(ap):
			return null
		var at := ResourceLoader.load(ap, "", ResourceLoader.CACHE_MODE_IGNORE) as Texture2D
		if at == null:
			return null
		e = {"tex": at, "used": 0, "bytes": at.get_width() * at.get_height() * 4}
		_atlas[cid] = e
	e.used = _clip_tick_no
	_clip_trim_atlas()
	var key := "%d:%d" % [cid, ph]
	var cell = _atlas_cell.get(key)
	if cell == null:
		var cols := int(m.cols)
		var i := (ph - 1) % int(m.n)
		var c := AtlasTexture.new()
		c.atlas = e.tex
		c.region = Rect2(float((i % cols) * int(m.w)), float((i / cols) * int(m.h)),
			float(m.w), float(m.h))
		_atlas_cell[key] = c
		cell = c
	return cell

## 贴图集只在显存里留最近用到的几张（几张整屏角色一起上场时也不至于把显卡塞满）
func _clip_trim_atlas() -> void:
	if _atlas.size() <= CLIP_ATLAS_KEEP:
		return
	var ids := _atlas.keys()
	ids.sort_custom(func(a, b): return int(_atlas[a].used) > int(_atlas[b].used))
	var keep := {}
	for i in mini(CLIP_ATLAS_KEEP, ids.size()):
		keep[ids[i]] = true
	for cid in ids:
		if keep.has(cid):
			continue
		if _clip_tick_no - int(_atlas[cid].used) < 3:
			continue
		_atlas.erase(cid)
		for k in _atlas_cell.keys():
			if str(k).begins_with("%d:" % cid):
				_atlas_cell.erase(k)

func _play_frame_sounds(n: int) -> void:
	var list = sound_frames.get(str(n))
	if not (list is Array):
		return
	for sid in list:
		_play_sound(str(int(sid)))

func _play_sound(sid: String) -> void:
	var info = sound_files.get(sid)
	if not (info is Dictionary):
		return
	var path := "res://assets/sfx/" + str(info.get("file", ""))
	if not _sound_cache.has(path):
		if not ResourceLoader.exists(path):
			return
		_sound_cache[path] = load(path)
	var stream = _sound_cache[path]
	if stream == null:
		return
	# 注意：导出成 exe 后，res:// 里的原始 mp3 文件不在包里（只有导入后的资源），
	# 所以不能用文件大小判断，只能看音频本身的时长。
	var is_music := false
	if stream is AudioStreamMP3:
		is_music = (stream as AudioStreamMP3).get_length() >= MUSIC_MIN_SECONDS
		(stream as AudioStreamMP3).loop = is_music
	if is_music:
		if _music_path == path and _music.playing:
			return
		_music_path = path
		_music.stream = stream
		_music.play()
	else:
		var p := _sfx[_sfx_next]
		_sfx_next = (_sfx_next + 1) % _sfx.size()
		p.stream = stream
		p.play()

func _stop_all_sounds() -> void:
	_music.stop()
	_music_path = ""
	for p in _sfx:
		p.stop()
