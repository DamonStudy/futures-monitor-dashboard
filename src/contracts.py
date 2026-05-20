"""Contract universe and board grouping for the futures monitor."""

BOARDS = {
    "黑色": [
        ("螺纹钢", "KQ.m@SHFE.rb"),
        ("热卷", "KQ.m@SHFE.hc"),
        ("铁矿石", "KQ.m@DCE.i"),
        ("焦煤", "KQ.m@DCE.jm"),
        ("焦炭", "KQ.m@DCE.j"),
        ("硅铁", "KQ.m@CZCE.SF"),
        ("锰硅", "KQ.m@CZCE.SM"),
    ],
    "有色": [
        ("沪铜", "KQ.m@SHFE.cu"),
        ("沪铝", "KQ.m@SHFE.al"),
        ("沪锌", "KQ.m@SHFE.zn"),
        ("沪铅", "KQ.m@SHFE.pb"),
        ("沪镍", "KQ.m@SHFE.ni"),
        ("沪锡", "KQ.m@SHFE.sn"),
        ("氧化铝", "KQ.m@SHFE.ao"),
        ("工业硅", "KQ.m@GFEX.si"),
    ],
    "能化": [
        ("原油", "KQ.m@INE.sc"),
        ("燃油", "KQ.m@SHFE.fu"),
        ("低硫燃油", "KQ.m@INE.lu"),
        ("沥青", "KQ.m@SHFE.bu"),
        ("橡胶", "KQ.m@SHFE.ru"),
        ("20号胶", "KQ.m@INE.nr"),
        ("PTA", "KQ.m@CZCE.TA"),
        ("短纤", "KQ.m@CZCE.PF"),
        ("PX", "KQ.m@CZCE.PX"),
        ("甲醇", "KQ.m@CZCE.MA"),
        ("乙二醇", "KQ.m@DCE.eg"),
        ("塑料", "KQ.m@DCE.l"),
        ("PP", "KQ.m@DCE.pp"),
        ("PVC", "KQ.m@DCE.v"),
        ("苯乙烯", "KQ.m@DCE.eb"),
        ("LPG", "KQ.m@DCE.pg"),
        ("纯碱", "KQ.m@CZCE.SA"),
        ("玻璃", "KQ.m@CZCE.FG"),
        ("尿素", "KQ.m@CZCE.UR"),
    ],
    "农产品": [
        ("豆一", "KQ.m@DCE.a"),
        ("豆二", "KQ.m@DCE.b"),
        ("豆粕", "KQ.m@DCE.m"),
        ("豆油", "KQ.m@DCE.y"),
        ("棕榈油", "KQ.m@DCE.p"),
        ("菜粕", "KQ.m@CZCE.RM"),
        ("菜油", "KQ.m@CZCE.OI"),
        ("玉米", "KQ.m@DCE.c"),
        ("淀粉", "KQ.m@DCE.cs"),
        ("鸡蛋", "KQ.m@DCE.jd"),
        ("生猪", "KQ.m@DCE.lh"),
    ],
    "软商品": [
        ("白糖", "KQ.m@CZCE.SR"),
        ("棉花", "KQ.m@CZCE.CF"),
        ("苹果", "KQ.m@CZCE.AP"),
        ("红枣", "KQ.m@CZCE.CJ"),
        ("花生", "KQ.m@CZCE.PK"),
    ],
    "贵金属": [
        ("黄金", "KQ.m@SHFE.au"),
        ("白银", "KQ.m@SHFE.ag"),
    ],
    "金融": [
        ("沪深300", "KQ.m@CFFEX.IF"),
        ("上证50", "KQ.m@CFFEX.IH"),
        ("中证500", "KQ.m@CFFEX.IC"),
        ("中证1000", "KQ.m@CFFEX.IM"),
        ("2年国债", "KQ.m@CFFEX.TS"),
        ("5年国债", "KQ.m@CFFEX.TF"),
        ("10年国债", "KQ.m@CFFEX.T"),
        ("30年国债", "KQ.m@CFFEX.TL"),
    ],
    "航运": [
        ("集运欧线", "KQ.m@INE.ec"),
    ],
}


def all_contracts():
    items = []
    for board, contracts in BOARDS.items():
        for name, symbol in contracts:
            items.append({"board": board, "name": name, "symbol": symbol})
    return items
