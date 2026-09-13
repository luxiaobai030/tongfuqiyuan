extends SceneTree
## 一次性自检：确认音效/字体/背景资源都能正常加载
func _init() -> void:
	var files := ["res://assets/sfx/46_myMusic.mp3", "res://assets/sfx/618.mp3", "res://assets/sfx/337.mp3"]
	for f in files:
		if not ResourceLoader.exists(f):
			print("缺少: ", f)
			continue
		var s = load(f)
		print(f, " -> ", s.get_class(), " 时长=%.1fs" % s.get_length())
	var fonts := ["res://assets/fonts/f34.ttf", "res://assets/fonts/f171.ttf", "res://assets/fonts/f15.ttf"]
	for f in fonts:
		var ft = load(f)
		print(f, " -> ", ft.get_class(), " 字体名=", ft.get_font_name())
	var bg = load("res://assets/bg/b0000.webp")
	print("背景 -> ", bg.get_class(), " 尺寸=", bg.get_size())
	var clip = load("res://assets/clips/2159.webp")
	print("角色动画层 -> ", clip.get_class(), " 尺寸=", clip.get_size())
	var big = load("res://assets/clips/2576/1.webp")
	print("整屏角色逐帧图 -> ", big.get_class(), " 尺寸=", big.get_size())
	var dir := ProjectSettings.globalize_path("res://../截图预览")
	print("截图目录: ", dir, " 存在=", DirAccess.dir_exists_absolute(dir))
	for n in ["黑体", "SimHei", "Microsoft YaHei", "Arial", "宋体"]:
		print("系统字体 ", n, " -> ", OS.get_system_font_path(n))
	quit()
