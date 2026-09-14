extends Node
## 同福奇缘 · 全局状态
## 变量表取自原版第 4907 帧的初始化脚本（ActionScript 的变量名不区分大小写，这里统一用小写键）
## 另补 hp=100：原版“开门营业”流程里从未给 hp 赋过值（原版遗留 bug），移植时给一个合理初值。
##
## 存档（移植版额外加的，原版没有存档功能）里除了变量表，还记着：
##   * items    —— 隐藏道具的收集进度（倾城装四件 + 淘宝珍品十五种）
##   * progress —— 存档那一刻游戏停在哪个帧、时间轴是不是在跑
##
## 一共三个档位。档位一用的就是当初单档版的文件名 —— 老玩家机器上原来那个存档
## 直接就是档位一，不用搬家也不会读不出来。

const SAVE_PATH := "user://tongfu_qiyuan_save.json"
const SAVE_PATH_FMT := "user://tongfu_qiyuan_save_%d.json"
const SAVE_SLOTS := 3
const SLOT_NAMES := ["档位一", "档位二", "档位三"]
const SAVE_VERSION := 2

signal changed

var vars: Dictionary = {}
var log_lines: Array = []
var items: Dictionary = {}          # 已收集的隐藏道具：道具键 → true
var progress: Dictionary = {}       # 存档位置：{frame, halted, time}

const INIT := {
	"jzg_haogan": 60, "lx_haogan": 70, "tzxy": 0, "wlrw": 0, "xxbb": 0,
	"yh": 0, "cs": 0, "ws": 0, "waichu": 0, "guaxiang": "吉", "time0": 0,
	"wlt": 1, "jiuhuandan": 1, "qctz": 5, "cc": 0, "fangyu": 0,
	"khdxs_lv": 0, "khdxs_gongji": 3, "khqls_lv": 0, "khqls_gongji": 15,
	"yzdt_lv": 0, "yzdt_gongji": 100, "psdh_lv": 0, "psdh_gongji": 30,
	"smhs_lv": 0, "smhs_gongji": 250, "zg_hjrt": 80,
	"xb_wan": 0, "aa1": 0, "aa2": 0, "aa3": 0, "hh": 0, "ff": 0,
	"hhs": 0, "ccs": 0, "ffs": 0, "smg": 0,
	"kzmc": "同福客栈", "boos_gongji": 85, "boos_hp": 6000,
	"money": 1000, "money_tishi": "1000文", "wlww": 0, "wm": 0,
	"day": 1, "day_tishi": "1天", "nandu": 1,
	"rmoney": 100, "hexie": 70, "hp": 100, "xiuwei": 200,
	"lb_chenghao": "跑堂的", "lb_gongji": 3, "lb_yongqi": 0, "lb_haogan": 10,
	"zg_jl": 100, "zg_chenghao": "掌柜", "zg_zixin": 20, "zg_meili": 50,
	"xg_chenghao": "打杂的", "xg_gongji": 15, "xg_zhengyi": 20, "xg_haogan": 20, "xg_xc": 50,
	"xc_chenghao": "穷酸秀才", "xc_zhongcheng": 50, "xc_caixue": 30, "xc_haogan": 20,
	"dz_chenghao": "一个厨子", "dz_yueli": 10, "dz_chuyi": 40, "dz_haogan": 10,
	"ws_chenghao": "天真小捕快", "ws_aixin": 20, "ws_cixiu": 40, "ws_haogan": 20,
	"xb_chenghao": "小丫头片子", "xb_tongxin": 100, "xb_xuexi": 100, "xb_haogan": 30,
	"renyuan": 0, "renqi": 0, "rmoney2": 0,
	"zhengjie": 0, "fuwu": 0, "yinshi": 0, "zhian": 0, "shouzhi": 0,
	"pingjia": "", "ch1": "", "ch2": "", "ch3": "", "ch4": "",
	"diren_hp": 0, "diren_gongji": 0, "hp_linshi": 0, "diren_hplinshi": 0, "shengli": 0,
}

func _ready() -> void:
	new_game()

func new_game() -> void:
	vars.clear()
	for k in INIT:
		vars[k] = INIT[k]
	log_lines = ["同福客栈，重新开张。"]
	items = {}
	progress = {}
	changed.emit()

## 记下一件隐藏道具，返回「这次是不是新拿到的」
func mark_item(k: String) -> bool:
	if items.has(k):
		return false
	items[k] = true
	changed.emit()
	return true

func has_item(k: String) -> bool:
	return items.has(k)

func item_count() -> int:
	return items.size()

func g(k: String, d = 0):
	var v = vars.get(k.to_lower())
	return d if v == null else v

func set_var(k: String, v) -> void:
	vars[k.to_lower()] = v
	changed.emit()

func add_log(t: String) -> void:
	log_lines.append(t)
	if log_lines.size() > 200:
		log_lines.pop_front()

func to_dict() -> Dictionary:
	return {"version": SAVE_VERSION, "vars": vars, "log": log_lines,
		"items": items, "progress": progress}

## 档位对应的存档文件。档位一 = 老的单档文件名，其余按序号排。
static func slot_path(slot: int) -> String:
	return SAVE_PATH if slot <= 1 else SAVE_PATH_FMT % slot

## 档位名（「档位一」这种），换算成中文数字，界面上直接用
static func slot_name(slot: int) -> String:
	var i := clampi(slot, 1, SAVE_SLOTS) - 1
	return SLOT_NAMES[i]

func save_game(slot: int = 1) -> bool:
	var f := FileAccess.open(slot_path(slot), FileAccess.WRITE)
	if f == null: return false
	f.store_string(JSON.stringify(to_dict(), "  "))
	f.close()
	return true

func has_save(slot: int = 1) -> bool:
	return FileAccess.file_exists(slot_path(slot))

## 存/读档框上那一行摘要：这个档位有没有东西、第几天、什么时候存的。
## 只读文件头，不碰当前游戏状态。
func slot_info(slot: int) -> Dictionary:
	var info := {"exists": false, "day": 0, "frame": 0, "time": ""}
	var p := slot_path(slot)
	if not FileAccess.file_exists(p):
		return info
	var f := FileAccess.open(p, FileAccess.READ)
	if f == null:
		return info
	var d = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(d) != TYPE_DICTIONARY:
		return info
	var sv = d.get("vars", {})
	var pr = d.get("progress", {})
	info["exists"] = true
	if sv is Dictionary:
		info["day"] = int(sv.get("day", 0))
	if pr is Dictionary:
		info["frame"] = int(pr.get("frame", 0))
		var t := str(pr.get("time", ""))
		# JSON 里存的是 2026-09-14T12:15:29，界面上只留日期和时间，T 换成空格
		info["time"] = (t.substr(5, 5) + " " + t.substr(11, 5)) if t.length() >= 16 else t
	return info

func load_game(slot: int = 1) -> bool:
	if not has_save(slot): return false
	var f := FileAccess.open(slot_path(slot), FileAccess.READ)
	if f == null: return false
	var txt := f.get_as_text()
	f.close()
	var d = JSON.parse_string(txt)
	if typeof(d) != TYPE_DICTIONARY: return false
	new_game()
	var sv = d.get("vars", {})
	if sv is Dictionary:
		for k in sv:
			vars[k] = _clean(sv[k])
	log_lines = d.get("log", [])
	items = {}
	var si = d.get("items", {})
	if si is Dictionary:
		for k in si:
			if bool(si[k]):
				items[str(k)] = true
	var sp = d.get("progress", {})
	progress = sp if sp is Dictionary else {}
	changed.emit()
	return true

## JSON 里没有整数，数值读回来一律是浮点（1000 会变成 1000.0）。
## 整数就转回整数 —— 否则读档之后游戏再拼字符串会拼出「1000.0文」这种东西。
func _clean(v):
	if v is float and absf(v - roundf(v)) < 0.0001:
		return int(roundf(v))
	return v
