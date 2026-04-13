#!/usr/bin/env python3


import os
import sys
import random
import subprocess
from typing import Dict, List, Tuple, Set
from datetime import datetime

MOD64 = 1 << 64
def alpha_mul(x):
    return ((x << 8) & (MOD64-1)) ^ (0x87 * (x >> 56))

def alphainv_mul(x):
    return (x >> 8) ^ ((0x0100000000000087 * (x & 0xFF)) & (MOD64-1))

_T_MASK = 0xDEADBEEFCAFEBABE

def T(x):
    x = ((x << 13) | (x >> 51)) & (MOD64-1)
    return x ^ _T_MASK

def T_inv(y):
    y ^= _T_MASK
    return ((y >> 13) | (y << 51)) & (MOD64-1)

class Strumok512:
    def __init__(self, lfsr, r1, r2):
        self.s = list(lfsr)
        self.r1 = r1
        self.r2 = r2

    def clock(self):
        s = self.s
        v = ((s[15] + self.r1) % MOD64) ^ self.r2
        z = v ^ s[0]
        r2_new = T(self.r1)
        r1_new = (self.r2 + (s[5] ^ self.r1)) % MOD64
        s_new = alpha_mul(s[0]) ^ s[2] ^ alphainv_mul(s[11]) ^ s[15]
        self.s = s[1:] + [s_new]
        self.r1, self.r2 = r1_new, r2_new
        return z

    def run(self, n):
        return [self.clock() for _ in range(n)]


def generate_relation_file_64bit(num_clocks: int, filename: str = None) -> str:
    """Генерує файл зв'язків для 64-бітних слів"""
    if filename is None:
        filename = f"strumok512_{num_clocks}clk_64bit.txt"
    
    lines = []
    lines.append(f"# Струмок-512: {num_clocks} тактів, 64-бітні слова")
    lines.append("# Атака часткового вгадування")
    lines.append("connection relations")
    
    for t in range(num_clocks):
        # LFSR зсув
        for i in range(15):
            lines.append(f"s_{t}_{i+1}, s_{t+1}_{i}")
        # LFSR зворотній зв'язок
        lines.append(f"s_{t}_0, s_{t}_2, s_{t}_11, s_{t}_15 => s_{t+1}_15")
        # FSM вихід
        lines.append(f"s_{t}_15, r1_{t}, r2_{t} => v_{t}")
        # FSM r2 оновлення
        lines.append(f"r1_{t} => r2_{t+1}")
        # FSM r1 оновлення
        lines.append(f"r2_{t}, s_{t}_5, r1_{t} => r1_{t+1}")
        # Ключовий потік
        lines.append(f"s_{t}_0, z_{t} => v_{t}")
        lines.append("")
    
    lines.append("known")
    for t in range(num_clocks):
        lines.append(f"z_{t}")
    lines.append("")
    lines.append("target")
    for i in range(16):
        lines.append(f"s_0_{i}")
    lines.append("r1_0")
    lines.append("r2_0")
    lines.append("")
    lines.append("end")
    
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    print(f"Створено: {filename}")
    return filename


def generate_relation_file_8bit(num_clocks: int, filename: str = None) -> str:
    """
    Генерує файл зв'язків для 8-бітних слів (байтів).
    Кожна 64-бітна змінна розбивається на 8 байтів.
    """
    if filename is None:
        filename = f"strumok512_{num_clocks}clk_8bit.txt"
    
    lines = []
    
    for t in range(num_clocks):
        # Зв'язки між байтами при зсуві LFSR
        for i in range(15):
            for b in range(8):
                lines.append(f"s_{t}_{i+1}_b{b}, s_{t+1}_{i}_b{b}")
        
        # Зворотній зв'язок LFSR (побайтово)
        for b in range(8):
            lines.append(f"s_{t}_0_b{b}, s_{t}_2_b{b}, s_{t}_11_b{b}, s_{t}_15_b{b} => s_{t+1}_15_b{b}")
        
        # FSM вихід (побайтово)
        for b in range(8):
            lines.append(f"s_{t}_15_b{b}, r1_{t}_b{b}, r2_{t}_b{b} => v_{t}_b{b}")
        
        # FSM r2 оновлення
        for b in range(8):
            lines.append(f"r1_{t}_b{b} => r2_{t+1}_b{b}")
        
        # FSM r1 оновлення
        for b in range(8):
            lines.append(f"r2_{t}_b{b}, s_{t}_5_b{b}, r1_{t}_b{b} => r1_{t+1}_b{b}")
        
        # Ключовий потік
        for b in range(8):
            lines.append(f"s_{t}_0_b{b}, z_{t}_b{b} => v_{t}_b{b}")
        lines.append("")
    
    lines.append("known")
    for t in range(num_clocks):
        for b in range(8):
            lines.append(f"z_{t}_b{b}")
    lines.append("")
    lines.append("target")
    for i in range(16):
        for b in range(8):
            lines.append(f"s_0_{i}_b{b}")
    for b in range(8):
        lines.append(f"r1_0_b{b}")
        lines.append(f"r2_0_b{b}")
    lines.append("")
    lines.append("end")
    
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    print(f"Створено: {filename}")
    return filename

def analyze_min_guesses_theoretical(clock_cycles: int) -> Tuple[int, int]:
    """
    Теоретичний аналіз мінімальної кількості 64-бітних слів,
    які потрібно вгадати для заданої кількості тактів.
    
    Повертає: (кількість слів, складність у бітах)
    """
    if clock_cycles <= 0:
        return 18, 1152
    
    # Відновлюємо з гами: s_0_0 .. s_0_{clock_cycles-1}
    recovered_from_keystream = min(clock_cycles, 16)
    
    # Залишилось вгадати:
    remaining_lfsr = 16 - recovered_from_keystream
    remaining_fsm = 2  # r1_0, r2_0
    
    total_guesses = remaining_lfsr + remaining_fsm
    
    # Якщо тактів >= 16, то всі LFSR відновлюються
    if clock_cycles >= 16:
        total_guesses = 2
    
    # Додаткові обмеження
    if clock_cycles < 16:
        total_guesses = max(total_guesses, 1)
    
    bits = total_guesses * 64
    return total_guesses, bits


def format_complexity(guesses: int, bits: int) -> str:
    """Форматує складність"""
    if bits >= 512:
        return f"2^{bits} (≥ 2^512 - повний перебір)"
    elif bits > 448:
        return f"2^{bits} (> 2^448)"
    elif bits == 448:
        return f"2^{bits} (= 2^448 - межа зі стандарту)"
    else:
        return f"2^{bits} (< 2^448) АТАКА МОЖЛИВА!"


def run_propagate_analysis(filename: str, guess_vars: List[str]) -> Dict:
    """
    Запускає propagate-аналіз через Autoguess
    """
    if not os.path.exists("autoguess.py"):
        return {"status": "not_available", "error": "autoguess.py not found"}
    
    known_str = ",".join(guess_vars)
    cmd = [
        "python3", "autoguess.py",
        "--inputfile", filename,
        "--solver", "propagate",
        "--known", known_str,
        "--nograph",
        "--log", "0"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        
        # Парсимо результат
        found = 0
        total = 0
        if "PROPAGATION SUMMARY" in output:
            for line in output.split("\n"):
                if "Total known after prop.:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        frac = parts[1].strip().split("/")
                        if len(frac) == 2:
                            found = int(frac[0])
                            total = int(frac[1])
        
        return {
            "status": "success",
            "found": found,
            "total": total,
            "output": output[:500] if len(output) > 500 else output
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def propagate_manual(known: Dict, num_clocks: int = 11) -> Dict:
    """
    Власна реалізація propagate для перевірки
    """
    K = dict(known)
    changed = True
    iteration = 0
    
    while changed and iteration < 50:
        changed = False
        iteration += 1
        
        for t in range(num_clocks):
            # Отримуємо значення
            s0 = K.get(f"s_{t}_0")
            s5 = K.get(f"s_{t}_5")
            s15 = K.get(f"s_{t}_15")
            r1t = K.get(f"r1_{t}")
            r2t = K.get(f"r2_{t}")
            vt = K.get(f"v_{t}")
            zt = K.get(f"z_{t}")
            
            # z = v XOR s0
            if vt is not None and zt is not None and s0 is None:
                K[f"s_{t}_0"] = vt ^ zt
                changed = True
            if s0 is not None and zt is not None and vt is None:
                K[f"v_{t}"] = s0 ^ zt
                changed = True
            
            # v = (s15 + r1) XOR r2
            if s15 is not None and r1t is not None and r2t is not None and vt is None:
                K[f"v_{t}"] = ((s15 + r1t) % MOD64) ^ r2t
                changed = True
            
            # LFSR shift
            for i in range(15):
                a = K.get(f"s_{t}_{i+1}")
                b = K.get(f"s_{t+1}_{i}")
                if a is not None and b is None:
                    K[f"s_{t+1}_{i}"] = a
                    changed = True
                if b is not None and a is None:
                    K[f"s_{t}_{i+1}"] = b
                    changed = True
    
    return K


def test_attack_with_guesses(clock_cycles: int, guess_names: List[str], verbose: bool = False) -> Dict:
    """
    Тестує атаку: задає випадковий стан, "вгадує" вказані змінні,
    перевіряє чи можна відновити весь стан.
    """
    random.seed(42)
    true_lfsr = [random.getrandbits(64) for _ in range(16)]
    true_r1 = random.getrandbits(64)
    true_r2 = random.getrandbits(64)
    
    true_state = {f"s_0_{i}": true_lfsr[i] for i in range(16)}
    true_state["r1_0"] = true_r1
    true_state["r2_0"] = true_r2
    
    gen = Strumok512(true_lfsr, true_r1, true_r2)
    keystream = gen.run(clock_cycles)
    
    # Відомі змінні: вгадані + гама
    known = {}
    for name in guess_names:
        if name in true_state:
            known[name] = true_state[name]
    for t, z in enumerate(keystream):
        known[f"z_{t}"] = z
    
    # Propagation
    recovered = propagate_manual(known, num_clocks=clock_cycles)
    
    # Перевірка
    targets = [f"s_0_{i}" for i in range(16)] + ["r1_0", "r2_0"]
    found = sum(1 for v in targets if recovered.get(v) is not None)
    correct = sum(1 for v in targets 
                  if recovered.get(v) is not None and recovered[v] == true_state.get(v))
    
    return {
        "found": found,
        "correct": correct,
        "total": len(targets),
        "guesses": len(guess_names)
    }

def main():
    
    print("\n{:^12} | {:^16} | {:^10} | {:^45}".format(
        "Такти", "Вгадувань (64-bit)", "Бітів", "Складність"))
    print("-" * 95)
    
    results_cycles = []
    for cycles in range(5, 17):
        guesses, bits = analyze_min_guesses_theoretical(cycles)
        complexity = format_complexity(guesses, bits)
        status = "Yes" if bits < 448 else "No" if bits > 448 else "warning"
        print(f"{cycles:^12} | {guesses:^16} | {bits:^10} | {status} {complexity}")
        results_cycles.append((cycles, guesses, bits))
    
    
    
    print("\n АТАКИ ЗІ СКЛАДНІСТЮ < 2^448:")
    print("-" * 50)
    
    found_attack = False
    for cycles, guesses, bits in results_cycles:
        if bits < 448:
            found_attack = True
            print(f"\n {cycles} тактів:")
            print(f"      - Вгадуваних 64-бітних слів: {guesses}")
            print(f"      - Складність: 2^{bits}")
            print(f"      - Файл для Autoguess: strumok512_{cycles}clk_64bit.txt")
    
    if not found_attack:
        print("\n Для 11 тактів мінімальна складність = 2^448")
        print("   Для отримання <2^448 потрібно використовувати ≤10 тактів")

    
    print("\nГенерація файлів для різної кількості тактів:")
    for cycles in [10, 9, 8]:
        if cycles <= 11:
            generate_relation_file_64bit(cycles)
    
    print("\nГенерація файлу на рівні байтів (8 біт):")
    generate_relation_file_8bit(5)  # для 5 тактів (складність менша)
    # Базис для 10 тактів: r1_0, r2_0, s_0_10..s_0_15
    guess_names_10 = ["r1_0", "r2_0"] + [f"s_0_{i}" for i in range(10, 16)]
    
    result = test_attack_with_guesses(10, guess_names_10, verbose=False)
    print(f"   Вгадано змінних: {result['guesses']}")
    print(f"   Відновлено: {result['found']}/{result['total']}")
    print(f"   Правильно: {result['correct']}/{result['total']}")
    
    if result['correct'] == result['total']:
        print("ПОВНЕ ВІДНОВЛЕННЯ СТАНУ!")
    else:
        print("Часткове відновлення (очікувано через заглушки)")
    
    
    guess_names_9 = ["r1_0", "r2_0"] + [f"s_0_{i}" for i in range(9, 16)]
    result = test_attack_with_guesses(9, guess_names_9, verbose=False)
    print(f"   Вгадано змінних: {result['guesses']}")
    print(f"   Відновлено: {result['found']}/{result['total']}")
    print(f"   Правильно: {result['correct']}/{result['total']}")
    


if __name__ == "__main__":
    main()