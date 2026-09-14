class_name UiSkin
extends RefCounted
## 移植版额外界面（右上角菜单、存档框、隐藏道具框、标题页读档按钮）的统一皮肤。
##
## 原版没有这些东西，新加的界面要是自己另搞一套颜色，摆在游戏里就很出戏
## （右上角最早那版工具箱就是深棕底 + 浅金字，和游戏完全不是一个画风）。
## 原版自己的界面长什么样，这里就照着抄：
##
##   * 标题页的四块菜单木牌、战斗界面敌人/自己的属性框、先机后发按钮，
##     全是「米黄底 + 深棕外框 + 朱红隶书字」。
##   * 底板和外框的像素直接取自标题页底图（tools/build_plaque.py 抠的），
##     所以是一模一样的颜色和云纹，不存在「看起来差不多」。
##
## 字一律用隶书（f34，见 main.gd 的 panel_font）：它缺的字和数字由系统字体兜底，
## 和原版数字走系统字体的情况一致。

const PLAQUE := "res://assets/ui/plaque.png"          # 155x42 空木牌
const PLAQUE_ON := "res://assets/ui/plaque_on.png"    # 同上，悬停提亮
const BOARD := "res://assets/ui/board.png"            # 310x84 木板，给面板当九宫格底
const BAR := "res://assets/ui/bar.png"                # 16x16 窄条，没有云纹
const BAR_ON := "res://assets/ui/bar_on.png"

## 木牌上的颜色（量的，不是估的）
const FILL := Color8(226, 197, 135)
const EDGE := Color8(124, 90, 50)
const RED := Color8(153, 0, 0)              # 木牌上的字：朱红
const RED_HOT := Color8(198, 30, 20)        # 鼠标压上去的字
const INK := Color8(88, 58, 22)             # 面板正文：比朱红浅，长段落才不刺眼
const INK_DIM := Color8(160, 140, 108)      # 没拿到的道具：？？？
const INK_NOTE := Color8(132, 110, 76)      # 小字注解
const SEP := Color8(198, 172, 124)          # 分隔线

## 九宫格边距：必须把四角那朵云整个圈进去，不然云会被抻成横条糊在边线上。
## 木牌上的云从外框往里有 13px，加上 5px 外框 = 18px，所以留 19。
## 代价是按钮高度别低于 40：矮了 Godot 会把边距往回缩，四角就对不齐了。
const PLAQUE_MARGIN := 19                   # plaque.png 的九宫格边距
const BOARD_MARGIN := 38                    # board.png（木牌 2 倍大）的九宫格边距
const BAR_MARGIN := 5                       # bar.png 的九宫格边距

static func _tex(path: String) -> Texture2D:
	return load(path) if ResourceLoader.exists(path) else null

## 木牌：1:1 用在按钮上，或者当九宫格拉成一行（四角云纹留着，中间拉伸）
static func plaque(hot: bool = false) -> StyleBoxTexture:
	var s := StyleBoxTexture.new()
	s.texture = _tex(PLAQUE_ON if hot else PLAQUE)
	s.set_texture_margin_all(PLAQUE_MARGIN)
	s.set_content_margin_all(4)
	return s

## 面板底：木牌放大 2 倍的九宫格，边框 8px，够撑大框
static func board() -> StyleBoxTexture:
	var s := StyleBoxTexture.new()
	s.texture = _tex(BOARD)
	s.set_texture_margin_all(BOARD_MARGIN)
	s.set_content_margin_all(22)
	return s

## 右上角那条：20px 高的地方塞不下云纹，只留底板和边框。
## pad 是内容边距 —— 顶上那条木牌只有 20px，得给 0 才塞得下
## （隶书 12 号的行高就有 18px，上下再垫 4px 就会被顶到 26px 高、压到「跳过情节」）。
static func bar(hot: bool = false, pad: int = 4) -> StyleBoxTexture:
	var s := StyleBoxTexture.new()
	s.texture = _tex(BAR_ON if hot else BAR)
	s.set_texture_margin_all(BAR_MARGIN)
	s.set_content_margin_all(pad)
	return s

## 面板上的小按钮（关闭 / 档位 / 菜单项）：木牌九宫格，朱红字
static func text_button(text: String, font: Font, size: int, min_size: Vector2) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.custom_minimum_size = min_size
	b.add_theme_font_override("font", font)
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", RED)
	b.add_theme_color_override("font_hover_color", RED_HOT)
	b.add_theme_color_override("font_pressed_color", RED_HOT)
	b.add_theme_stylebox_override("normal", plaque(false))
	b.add_theme_stylebox_override("hover", plaque(true))
	b.add_theme_stylebox_override("pressed", plaque(true))
	b.add_theme_stylebox_override("disabled", plaque(false))
	b.add_theme_color_override("font_disabled_color", INK_DIM)
	return b
