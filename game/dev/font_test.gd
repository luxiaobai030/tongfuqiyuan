extends Node2D
## 一次性试验：比较几种字体加载方式的渲染结果
func _ready() -> void:
	var y := 40.0
	var txt := "十八里铺的街道上有人注意到了佟湘玉的出现 123ABC"
	var a := SystemFont.new()
	a.font_names = PackedStringArray(["黑体", "SimHei"])
	_row(a, "SystemFont 黑体", txt, y); y += 50
	var b := FontFile.new()
	b.load_dynamic_font("C:/WINDOWS/FONTS/simhei.ttf")
	_row(b, "FontFile.load_dynamic_font", txt, y); y += 50
	var c = load("res://assets/fonts/f34.ttf")
	_row(c, "内嵌 隶书", txt, y); y += 50
	var d = load("res://assets/fonts/f171.ttf")
	_row(d, "内嵌 楷体", txt, y); y += 50
	var e := load("res://assets/fonts/f174.ttf")
	_row(e, "内嵌 宋体", txt, y)
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("res://../截图预览/字体对比.png")
	get_tree().quit()

func _row(f: Font, tag: String, txt: String, y: float) -> void:
	var lbl := Label.new()
	lbl.add_theme_font_override("font", f)
	lbl.add_theme_font_size_override("font_size", 20)
	lbl.add_theme_color_override("font_color", Color("#990000"))
	lbl.text = tag + " : " + txt
	lbl.position = Vector2(10, y)
	lbl.size = Vector2(780, 30)
	add_child(lbl)