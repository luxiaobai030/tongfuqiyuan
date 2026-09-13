extends Control
## 角色动画层：自己不做判断，只把主程序算好的角色（深度 / 贴图 / 位置）画出来。
## 引擎规定绘制命令必须在节点自己的 _draw() 里发，所以这层单独一个小脚本。
var draw_fn := Callable()

func _draw() -> void:
	if draw_fn.is_valid():
		draw_fn.call(self)
