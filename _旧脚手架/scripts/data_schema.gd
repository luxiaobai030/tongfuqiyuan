extends RefCounted
## 《同福奇缘》数据模型
## 变量名与结构全部来自原版 SWF 的 DefineEditText 变量表（79 个唯一变量）

const CHAR_ORDER := ["ZG", "LB", "XG", "XC", "DZ", "WS", "XB"]

const CHAR_INFO := {
	"ZG": {"name": "佟湘玉", "role": "掌柜", "color": "#f4c875"},
	"LB": {"name": "白展堂", "role": "跑堂的", "color": "#9ec8e8"},
	"XG": {"name": "郭芙蓉", "role": "打杂的", "color": "#e8a0a0"},
	"XC": {"name": "吕秀才", "role": "穷酸秀才", "color": "#b8d8a0"},
	"DZ": {"name": "李大嘴", "role": "一个厨子", "color": "#e8c890"},
	"WS": {"name": "祝无双", "role": "小丫头片子", "color": "#d8b0e0"},
	"XB": {"name": "莫小贝", "role": "衡山小掌门", "color": "#f0b0c0"},
}

## 角色属性字段： [变量后缀, 显示名, 初始值]
const CHAR_FIELDS := {
	"ZG": [["JL", "技力", 20], ["zixin", "自信", 10], ["meili", "魅力", 10], ["chenghao", "称号", 0]],
	"LB": [["gongji", "攻击", 10], ["yongqi", "勇气", 10], ["haogan", "好感", 30], ["money", "私房钱", 0], ["chenghao", "称号", 0]],
	"XG": [["gongji", "攻击", 10], ["zhengyi", "正义", 10], ["haogan", "好感", 30], ["XC", "感情", 0], ["chenghao", "称号", 0]],
	"XC": [["zhongcheng", "忠诚", 10], ["caixue", "才学", 10], ["haogan", "好感", 30], ["chenghao", "称号", 0]],
	"DZ": [["yueli", "阅历", 10], ["chuyi", "厨艺", 10], ["haogan", "好感", 30], ["chenghao", "称号", 0]],
	"WS": [["aixin", "爱心", 10], ["cixiu", "刺绣", 0], ["haogan", "好感", 30], ["chenghao", "称号", 0]],
	"XB": [["tongxin", "童心", 30], ["xuexi", "学习", 10], ["haogan", "好感", 40], ["chenghao", "称号", 0]],
}

## 武功等级： 变量名 -> [显示名, 归属角色]
const SKILLS := {
	"KHDXS_lv": ["葵花点穴手", "LB"],
	"KHQLS_lv": ["葵花千裂手", "LB"],
	"YZDT_lv": ["洞天一指", "LB"],
	"PSDH_lv": ["排山倒海", "XG"],
	"SMHS_lv": ["山盟海誓", "XG"],
}

## 全局属性： [变量名, 显示名, 初始值]
const GLOBAL_FIELDS := [
	["hp", "生命", 100],
	["fangyu", "防御", 0],
	["xiuwei", "修为", 0],
	["renqi", "人气", 0],
	["wm", "威望", 0],
	["pingjia", "评价", 0],
	["money", "金钱", 100],
	["zhengjie", "客栈整洁", 50],
	["fuwu", "客栈服务", 50],
	["zhian", "治安", 50],
	["yinshi", "饮食", 50],
	["renyuan", "人员", 0],
	["hexie", "和谐", 50],
	["jiuhuandan", "九还丹", 0],
	["WLT", "武林帖", 0],
	["WLWW", "武林外传", 0],
	["WM", "威望(大写)", 0],
	["taobao", "淘宝", 0],
	["zuomeng", "做梦", 0],
	["anwei", "安慰", 0],
	["guli", "鼓励", 0],
	["guaxiang", "挂像", 0],
	["TZ_cishu", "投资次数", 0],
	["xiaomi", "小米", 0],
	["rmoney", "奖励金", 0],
	["rmoney2", "奖励金2", 0],
	["shouzhi", "收支", 0],
	["guangjietishi", "逛街提示", 0],
	["wupintishi", "物品提示", 0],
	["kzmc", "客栈名称", 0],
	["ch1", "进度1", 0],
	["ch2", "进度2", 0],
	["ch3", "进度3", 0],
	["ch4", "进度4", 0],
	["smg", "smg", 0],
	["spk", "spk", 0],
	["spk1", "spk1", 0],
	["wlww", "wlww(小写)", 0],
	["wm", "wm(小写)", 0],
	["day_tishi", "天数提示", 0],
	["money_tishi", "金钱提示", 0],
]

## 战斗中的临时变量
const COMBAT_FIELDS := [
	["diren_HP", "敌人生命", 0],
	["diren_gongji", "敌人攻击", 0],
	["BOOS_HP", "首领生命", 0],
	["BOOS_gongji", "首领攻击", 0],
]

## 一天的上限天数（原版道具「时间前进3天，97天后无法使用」推出总长 100 天）
const TOTAL_DAYS := 100

## 生成全新一局的变量表
static func make_initial_vars() -> Dictionary:
	var v := {}
	for prefix in CHAR_ORDER:
		for f in CHAR_FIELDS[prefix]:
			v[str(prefix, "_", f[0])] = int(f[2])
	for key in SKILLS:
		v[key] = 0
	for g in GLOBAL_FIELDS:
		v[g[0]] = int(g[2])
	for c in COMBAT_FIELDS:
		v[c[0]] = int(c[2])
	return v

## 所有变量的显示名，用于调试面板
static func label_of(key: String) -> String:
	for prefix in CHAR_ORDER:
		for f in CHAR_FIELDS[prefix]:
			if str(prefix, "_", f[0]) == key:
				return str(CHAR_INFO[prefix]["name"], "·", f[1])
	for g in GLOBAL_FIELDS:
		if g[0] == key:
			return str(g[1])
	for c in COMBAT_FIELDS:
		if c[0] == key:
			return str(c[1])
	if SKILLS.has(key):
		return str(SKILLS[key][0], " Lv")
	return key
