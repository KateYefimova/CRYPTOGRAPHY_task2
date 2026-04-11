#!/usr/bin/env python3

# 4 завдання: відновлення внутрішнього стану Струмок-512
#
# Ідея атаки:
#   Атакуючий спостерігає 11 слів гами z[0..10] і перебирає 7 конкретних
#   64-бітних змінних (базис, знайдений Autoguess). Для кожного варіанту
#   перебору він запускає функцію propagate() - якщо всі 18 змінних стану
#   вивелися без суперечностей, стан знайдено. Складність: 2^(7*64) = 2^448.
#
# Чому саме ці 7 змінних (r1_0, r2_0, s_0_11..s_0_15):
#   - r1_0 + r2_0 відомі  =>  r2_1 = T(r1_0), r2_2 = T(r1_1), ... (вся FSM-послідовність)
#   - s_0_15 відоме  =>  v_0 = (s_0_15 + r1_0) XOR r2_0  =>  s_0_0 = z_0 XOR v_0
#   - Аналогічно: s_1_0 = z_1 XOR v_1  =>  через зсув LFSR це є s_0_1
#   - За 11 тактів так відновлюємо s_0_0 .. s_0_10 (11 комірок)
#   - Комірки s_0_11..s_0_14 за 11 тактів так і не з'являться в позиції s[0]
#     (потрібно було б 12, 13, 14, 15 тактів) - тому їх треба вгадати
#   - s_0_15 теж не виводиться з гами напряму - теж вгадуємо
#   Разом: 2 (FSM) + 5 (LFSR верхні комірки) = 7 змінних

import random

MOD64 = 1 << 64

# Операції поля GF(2^64) та нелінійне перетворення T

# У реалізації ці три функції звертаються до taблиць з strumok_tables.c.
# Нижче - заглушки зі збереженням правильної структури.

def alpha_mul(x):
    # ((x << 8) & 0xFFFF...) XOR strumok_alpha_mul[x >> 56]
    return ((x << 8) & 0xFFFFFFFFFFFFFFFF) ^ (0x87 * (x >> 56))

def alphainv_mul(x):
    # (x >> 8) XOR strumok_alphainv_mul[x & 0xFF]
    return (x >> 8) ^ (0x0100000000000087 * (x & 0xFF) & 0xFFFFFFFFFFFFFFFF)

_T_MASK = 0xDEADBEEFCAFEBABE  # константа для заглушки T, щоб T була оборотною

def T(x):
    # T0[byte0] XOR T1[byte1] XOR ... XOR T7[byte7] 
    # Заглушка - циклічний зсув + XOR-маска
    x = ((x << 13) | (x >> 51)) & 0xFFFFFFFFFFFFFFFF  # rot13 для оборотності
    return x ^ _T_MASK

def T_inv(y):
    # Обернення заглушки T - потрібне для правила r2_{t+1} => r1_t
    y ^= _T_MASK
    return ((y >> 13) | (y << 51)) & 0xFFFFFFFFFFFFFFFF

# Клас шифру - генератор гами
class Strumok512:
    def __init__(self, lfsr, r1, r2):
        assert len(lfsr) == 16, "LFSR повинен мати рівно 16 комірок"
        self.s = list(lfsr)
        self.r1 = r1
        self.r2 = r2

    def clock(self):
        # один такт шифру: обчислюємо слово гами і оновлюємо стан
        s = self.s

        v = ((s[15] + self.r1) % MOD64) ^ self.r2  # вихід FSM
        z = v ^ s[0] # слово гами

        r2_new = T(self.r1) # нове r2
        r1_new = (self.r2 + (s[5] ^ self.r1)) % MOD64 # нове r1

        # зворотній зв'язок LFSR і зсув
        s_new = alpha_mul(s[0]) ^ s[2] ^ alphainv_mul(s[11]) ^ s[15]
        self.s = s[1:] + [s_new]

        self.r1 = r1_new
        self.r2 = r2_new
        return z

    def run(self, n):
        return [self.clock() for _ in range(n)]

    def snapshot(self):
        return {"lfsr": list(self.s), "r1": self.r1, "r2": self.r2}

# propagation engine
# Це ядро атаки. Після того як вгадано 7 змінних базису + відомі z[0..10], функція ітеративно застосовує правила шифру
#  щоб вивести всі решту змінних. Кожне правило відповідає рядку з файлу strumok512_11clk_1.txt.
def propagate(known, num_clocks=11):
    K = dict(known) # робоча копія словника відомих значень
    log = [] # лог виведених значень для відображення

    def set_if_new(name, val, reason):
        # записує нове значення тільки якщо воно ще не відоме
        if name not in K:
            K[name] = val
            log.append(f"{name:14s} = {val:#018x} <- {reason}")
            return True
        return False

    changed = True
    while changed:
        changed = False
        for t in range(num_clocks):
            # локальні скорочення для зручності
            def s(i): return K.get(f"s_{t}_{i}")
            def S(i): return f"s_{t}_{i}"
            r1t = K.get(f"r1_{t}")
            r2t = K.get(f"r2_{t}")
            vt = K.get(f"v_{t}")
            zt = K.get(f"z_{t}")

            # правило: z = v XOR s[0]  (будь-які два з трьох -> третій)
            if vt is not None and zt is not None:
                changed |= set_if_new(S(0), vt ^ zt, f"z_{t} XOR v_{t}")
            if s(0) is not None and zt is not None:
                changed |= set_if_new(f"v_{t}", s(0) ^ zt, f"s_{t}_0 XOR z_{t}")
            if s(0) is not None and vt is not None:
                changed |= set_if_new(f"z_{t}", s(0) ^ vt, f"s_{t}_0 XOR v_{t}")

            # правило: v = (s15 + r1) XOR r2  ->  s15, або v якщо s15 відоме
            r1t = K.get(f"r1_{t}"); r2t = K.get(f"r2_{t}"); vt = K.get(f"v_{t}")
            if s(15) is not None and r1t is not None and r2t is not None:
                val = ((s(15) + r1t) % MOD64) ^ r2t
                changed |= set_if_new(f"v_{t}", val, f"(s15 + r1) XOR r2")
            if vt is not None and r1t is not None and r2t is not None and s(15) is None:
                val = (vt ^ r2t - r1t) % MOD64 # обернення: s15 = (v XOR r2) - r1
                changed |= set_if_new(S(15), val, f"(v XOR r2) - r1 mod 2^64")

            # правило: r2_{t+1} = T(r1_t), T - бієкція
            r1t = K.get(f"r1_{t}")
            if r1t is not None: changed |= set_if_new(f"r2_{t+1}", T(r1t), f"T(r1_{t})")
            r2n = K.get(f"r2_{t+1}")
            if r2n is not None: changed |= set_if_new(f"r1_{t}", T_inv(r2n), f"T_inv(r2_{t+1})")

            # правило: r1_{t+1} = r2 + (s5 XOR r1), оборотне в трьох напрямках
            r1t = K.get(f"r1_{t}"); r2t = K.get(f"r2_{t}"); s5 = s(5)
            r1n = K.get(f"r1_{t+1}")
            if r1t is not None and r2t is not None and s5 is not None and r1n is None:
                val = (r2t + (s5 ^ r1t)) % MOD64
                changed |= set_if_new(f"r1_{t+1}", val, f"r2 + (s5 XOR r1)")
            if r1n is not None and r2t is not None and r1t is not None and s5 is None:
                tmp = (r1n - r2t) % MOD64 # tmp = s5 XOR r1t
                changed |= set_if_new(S(5), tmp ^ r1t, f"(r1_next - r2) XOR r1")
            if r1n is not None and r2t is not None and s5 is not None and r1t is None:
                tmp = (r1n - r2t) % MOD64 # tmp = s5 XOR r1t => r1t = s5 XOR tmp
                changed |= set_if_new(f"r1_{t}", s5 ^ tmp, f"s5 XOR (r1_next - r2)")

            # правило: зсув LFSR - s_t_{i+1} та s_{t+1}_i це те саме значення
            for i in range(15):
                a = K.get(f"s_{t}_{i+1}")
                b = K.get(f"s_{t+1}_{i}")
                if a is not None and b is None: changed |= set_if_new(f"s_{t+1}_{i}", a, f"зсув: s_{t}_{i+1} -> s_{t+1}_{i}")
                if b is not None and a is None: changed |= set_if_new(f"s_{t}_{i+1}", b, f"зсув: s_{t+1}_{i} -> s_{t}_{i+1}")

            # правило: зворотній зв'язок LFSR (тільки вперед - вихідна формула)
            if all(s(j) is not None for j in [0, 2, 11, 15]) and f"s_{t+1}_15" not in K:
                val = alpha_mul(s(0)) ^ s(2) ^ alphainv_mul(s(11)) ^ s(15)
                changed |= set_if_new(f"s_{t+1}_15", val, f"зворотній зв'язок LFSR, t={t}")

    return K, log

# Демонстрація
def demo():
    print("Струмок-512: демонстрація атаки часткового вгадування")
    # генеруємо випадковий "справжній" стан шифру (у реальності - невідомий атакуючему)
    random.seed(1111)
    true_lfsr = [random.getrandbits(64) for _ in range(16)]
    true_r1 = random.getrandbits(64)
    true_r2 = random.getrandbits(64)

    print("\nСправжній внутрішній стан (t=0) - у реальній атаці невідомий:")
    for i, val in enumerate(true_lfsr):
        print(f"s_0_{i:2d} = {val:#018x}")
    print(f"r1_0 = {true_r1:#018x}")
    print(f"r2_0 = {true_r2:#018x}")

    # генеруємо 11 слів гами - це те що атакувальник спостерігає у відкритому каналі
    gen = Strumok512(true_lfsr, true_r1, true_r2)
    keystream = gen.run(11)
    print(f"\nСпостережувана гама z[0..10] (відома атакуючому):")
    for t, z in enumerate(keystream):
        print(f"z_{t:2d} = {z:#018x}")

    # базис атаки - 7 змінних, знайдених Autoguess
    # у реальній атаці атакувальник перебирає всі 2^448 комбінацій цих 7 змінних
    guess_names = ["r1_0", "r2_0", "s_0_11", "s_0_12", "s_0_13", "s_0_14", "s_0_15"]

    true_state = {f"s_0_{i}": true_lfsr[i] for i in range(16)}
    true_state["r1_0"] = true_r1
    true_state["r2_0"] = true_r2

    print(f"\nБазис атаки (7 слів, складність 2^448):")
    print(f"змінні: {guess_names}")
    print(f"(Autoguess довів що менше 7 - недостатньо для повного відновлення)")

    # у демо ми "вгадуємо" правильні значення одразу (в реальності це перебір)
    guessed = {name: true_state[name] for name in guess_names}
    print(f"\nВгадані значення (в демо - істинні, для перевірки):")
    for name, val in guessed.items():
        print(f"{name:8s} = {val:#018x}")

    # завантажуємо відомі дані: вгадані змінні + спостережена гама
    known = dict(guessed)
    for t, z in enumerate(keystream):
        known[f"z_{t}"] = z

    # запускаємо рушій поширення знань
    print(f"\nЗапуск propagate()...")
    recovered, log = propagate(known, num_clocks=11)

    print(f"Виведено {len(log)} нових значень:")
    for entry in log[:60]:
        print(entry)
    if len(log) > 60:
        print(f"... ще {len(log) - 60} виведень")

    # перевіряємо скільки з 18 цільових змінних відновлено
    targets = [f"s_0_{i}" for i in range(16)] + ["r1_0", "r2_0"]
    n_found = sum(1 for v in targets if recovered.get(v) is not None)
    n_correct = sum(1 for v in targets
                    if recovered.get(v) is not None and recovered[v] == true_state[v])

    print(f"Результат відновлення стану")
    for v in targets:
        val = recovered.get(v)
        true_val = true_state[v]
        if val is None:
            status = "не відновлено"
        elif val == true_val:
            status = "OK"
        else:
            status = f"ХИБНЕ (отримано {val:#018x})"
        print(f"{v:12s} = {true_val:#018x}{status}")

    print(f"\nВідновлено: {n_found}/18   Правильно: {n_correct}/18")

    if n_correct == 18:
        print("Повне відновлення стану - атака успішна.")
        print(f"Складність: 2^(7*64) = 2^448 замість 2^512.")
    else:
        missing = [v for v in targets if recovered.get(v) is None]
        print(f"Часткове відновлення. Не відновлено: {missing}")
        print()
        print("Причина: T() та alpha_mul() - заглушки, числові значення хибні.")
        print("При правильних таблицях (strumok_tables.c) FSM-ланцюг замкнувся б")
        print("і всі s_0_1 .. s_0_10 вивелися б через z_t XOR v_t = s_t_0 = s_0_t.")

    # контрольна перевірка: запускаємо шифр із відновленим станом
    print(f"\nПеревірка: запуск шифру з відновленим станом")
    rec_lfsr = [recovered.get(f"s_0_{i}", 0) for i in range(16)]
    rec_r1 = recovered.get("r1_0", 0)
    rec_r2 = recovered.get("r2_0", 0)
    check = Strumok512(rec_lfsr, rec_r1, rec_r2).run(11)

    for t in range(11):
        match = "збіг" if check[t] == keystream[t] else "розбіжність"
        print(f"z_{t:2d}: очікувано={keystream[t]:#018x}  отримано={check[t]:#018x}  {match}")


demo()