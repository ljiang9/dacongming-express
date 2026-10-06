"""dacongming_express: 大聪明高速返程博弈模拟器.

国庆 10 天假期,玩家扮演返程车主,在 10 月 4/5/6/7 四天中选一天出发,
再选时段(凌晨/上午/下午/深夜).AI NPC 车主各有"聪明度":
聪明度越高越倾向"提前走避堵"——结果扎堆之后,高速上挤满了聪明人.

纯 Python 标准库.
"""

from __future__ import annotations

import argparse
import random
import sys
import time

DAYS = (4, 5, 6, 7)  # 10 月 4/5/6/7 可选返程日
SLOTS = ("凌晨", "上午", "下午", "深夜")

# 各返程日基础返程流(单位:抽象车流单位,越高天然越堵)
BASE_FLOW = {4: 10, 5: 22, 6: 45, 7: 70}
# 各时段拥堵系数
SLOT_FACTOR = {"凌晨": 0.4, "上午": 1.0, "下午": 1.5, "深夜": 0.6}
# 路程基准耗时(小时)
BASE_HOURS = 6.0

EVENT_TABLE = [
    # (名称, 平均增加小时, 梗文案)
    ("服务区野餐泡茶", 1.5, "前车在服务区摆开了折叠桌泡功夫茶,后备箱还拿出了烧烤架——堵成停车场,咱不吃点啥说不过去"),
    ("下车遛狗拉伸", 1.0, "车门一开,三只狗窜上了应急车道。全高速的人都在看狗,只有你在看导航上越来越红的路段"),
    ("新能源充电取号", 5.0, "服务区充电桩排队取号:您前面还有 99 位。看着油车车主加满油扬长而去,你默默打开了手机热点"),
    ("错过出口倒车", 2.5, "导航说'前方 500 米右转',你看着 500 米长的车龙选择了相信自己,结果在下一个出口多绕了 40 公里"),
    ("后备箱特产大甩卖", 0.8, "隔壁车大哥摇下车窗:老乡,土鸡蛋要不要?堵着也是堵着,你买了两箱,还加了大哥微信"),
]


class IllegalMove(ValueError):
    """非法输入(不存在的日期/时段等)."""


def validate_choice(day: int, slot: str) -> None:
    if day not in DAYS:
        raise IllegalMove(f"返程日只能是 {DAYS},你选了 {day}")
    if slot not in SLOTS:
        raise IllegalMove(f"时段只能是 {SLOTS},你选了 {slot}")


class NPC:
    """AI 车主NPC.聪明度越高,越倾向于"提前走避堵"."""

    def __init__(self, smartness: float):
        self.smartness = max(0.0, min(100.0, smartness))

    def choose(self, rng: random.Random) -> tuple[int, str]:
        s = self.smartness
        # 聪明人想"提前避堵":聪明度越高,越偏向 4/5 号和凌晨
        early_bias = s / 100.0  # 0..1
        day_weights = [
            1.0 + 3.0 * early_bias,   # 4 号
            1.0 + 2.0 * early_bias,   # 5 号
            1.0 - 0.5 * early_bias,   # 6 号
            0.6 - 0.4 * early_bias,   # 7 号
        ]
        day = rng.choices(DAYS, weights=day_weights, k=1)[0]
        slot_weights = [
            0.6 + 2.4 * early_bias,   # 凌晨
            1.0,                       # 上午
            1.0 - 0.3 * early_bias,   # 下午
            0.7 + 0.8 * early_bias,   # 深夜
        ]
        slot = rng.choices(SLOTS, weights=slot_weights, k=1)[0]
        return day, slot


def congestion(day: int, slot: str, npc_count: int, rng: random.Random) -> float:
    """拥堵指数.同日同段车越多越堵;随机事故系数 0~25."""
    accident = rng.uniform(0, 25)
    return (BASE_FLOW[day] + npc_count * 2.0) * SLOT_FACTOR[slot] + accident


def travel_hours(day: int, slot: str, npc_count: int, rng: random.Random) -> tuple[float, list[str]]:
    """返回(总耗时小时, 触发的事件文案列表)."""
    cong = congestion(day, slot, npc_count, rng)
    hours = BASE_HOURS + cong / 10.0
    events: list[str] = []
    # 拥堵越严重,越可能触发高速名场面
    for name, avg_add, desc in EVENT_TABLE:
        prob = min(0.75, cong / 220.0)
        if rng.random() < prob:
            add = rng.uniform(avg_add * 0.5, avg_add * 1.5)
            hours += add
            events.append(f"【{name}】+{add:.1f}h:{desc}")
    return hours, events


def rank_player(hours: float, day: int, slot: str, npc_hours: list[float]) -> tuple[str, str]:
    """按耗时和"避堵意图"打出大聪明等级.毒舌但善意."""
    median = sorted(npc_hours)[len(npc_hours) // 2]
    tried_to_dodge = (day in (4, 5)) or (slot in ("凌晨", "深夜"))
    failed = hours > median  # 想避堵却比一半人还慢 = 失算

    if tried_to_dodge and failed:
        if hours >= median * 1.6:
            return ("大聪明之王",
                    "提前三天做攻略、凌晨四点就出发,结果在高速上看了日出又看了日落。"
                    "全国的'聪明人'今晚都在这条路上开茶话会,你是会长。")
        if hours >= median * 1.3:
            return ("钻石大聪明",
                    "你的避堵计划书可以出版了,唯一的读者是堵在你前面的 99 号充电桩。"
                    "别灰心,至少你的朋友圈定位比别人早发了两小时。")
        return ("黄金大聪明",
                "想法是对的,执行是拉的,队友(全国车主)是猪——哦不,队友也是大聪明。"
                "下次记得:当所有人都在避堵,避堵本身就是最堵的路。")
    if failed:
        return ("青铜大聪明",
                "老老实实跟着大部队堵,输得明明白白。虽败犹荣——至少你没假装自己能赢。")
    if hours <= median * 0.7:
        return ("反套路大师",
                "当所有聪明人都在凌晨四点挤高速,你睡到自然醒反而一路畅通。"
                "最大的聪明,是承认自己算不过命。")
    return ("普通返程人",
            "不早不晚,不堵不空。你避开了所有热搜,也错过了所有故事。"
            "平平安安到家,就是最大的胜利。")


class Game:
    def __init__(self, npc_count: int = 60, seed: int | None = None):
        self.npc_count = npc_count
        self.rng = random.Random(seed)
        self.npcs = [NPC(self.rng.uniform(0, 100)) for _ in range(npc_count)]

    def play(self, day: int, slot: str) -> dict:
        validate_choice(day, slot)
        npc_choices = [npc.choose(self.rng) for npc in self.npcs]
        npc_hours: list[float] = []
        for d, s in npc_choices:
            same = sum(1 for dd, ss in npc_choices if dd == d and ss == s)
            h, _ = travel_hours(d, s, same, self.rng)
            npc_hours.append(h)
        my_count = sum(1 for dd, ss in npc_choices if dd == day and ss == slot)
        hours, events = travel_hours(day, slot, my_count, self.rng)
        title, comment = rank_player(hours, day, slot, npc_hours)
        return {
            "day": day, "slot": slot, "hours": hours,
            "events": events, "title": title, "comment": comment,
            "npc_median": sorted(npc_hours)[len(npc_hours) // 2],
            "npc_on_my_road": my_count,
        }

    def auto_player(self) -> tuple[int, str]:
        """AI 玩家:随机策略选日子时段."""
        return self.rng.choice(DAYS), self.rng.choice(SLOTS)


def print_report(result: dict) -> None:
    print(f"返程选择:10 月 {result['day']} 日 {result['slot']}")
    print(f"同路聪明人:{result['npc_on_my_road']} 位 NPC 和你挤同一天同时段")
    print(f"总耗时:{result['hours']:.1f} 小时 (NPC 中位数 {result['npc_median']:.1f} 小时)")
    for e in result["events"]:
        print(" " + e)
    print(f"【{result['title']}】")
    print(result["comment"])


def interactive() -> int:
    if not sys.stdin.isatty():
        print("需要交互式终端;非交互环境请用 --auto 模式。", file=sys.stderr)
        return 2
    print("=== 大聪明高速返程博弈 ===")
    print("10 天假期,10 月 4/5/6/7 选一天返程,再选时段(凌晨/上午/下午/深夜)。")
    print("记住:高速上挤满了聪明人,越想避堵可能越堵。")
    try:
        day = int(input("返程日(4/5/6/7):").strip())
        slot = input("时段(凌晨/上午/下午/深夜):").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已退出。")
        return 0
    except ValueError:
        print("日期必须是数字。", file=sys.stderr)
        return 2
    try:
        validate_choice(day, slot)
    except IllegalMove as e:
        print(e, file=sys.stderr)
        return 2
    game = Game(seed=int(time.time()) % 100000)
    print_report(game.play(day, slot))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大聪明高速返程博弈模拟器")
    ap.add_argument("--auto", action="store_true", help="自动演示模式")
    ap.add_argument("--games", type=int, default=1, help="自动模式局数")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--verbose", action="store_true", help="打印单局战报")
    ap.add_argument("--npc", type=int, default=60, help="NPC 车主数量")
    args = ap.parse_args(argv)
    if args.games < 1:
        print("--games 必须 >= 1", file=sys.stderr)
        return 2
    if args.npc < 1:
        print("--npc 必须 >= 1", file=sys.stderr)
        return 2
    if not args.auto:
        return interactive()
    seed = args.seed if args.seed is not None else 42
    titles: dict[str, int] = {}
    total_hours = 0.0
    for i in range(args.games):
        game = Game(npc_count=args.npc, seed=seed + i)
        day, slot = game.auto_player()
        result = game.play(day, slot)
        titles[result["title"]] = titles.get(result["title"], 0) + 1
        total_hours += result["hours"]
        if args.verbose:
            print(f"--- 第 {i + 1} 局 ---")
            print_report(result)
    print(f"共 {args.games} 局,平均耗时 {total_hours / args.games:.1f} 小时,大聪明等级分布:")
    for t, c in sorted(titles.items(), key=lambda x: -x[1]):
        print(f"  {t}:{c} 次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
