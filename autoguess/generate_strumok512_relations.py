#!/usr/bin/env python3
import os
# Feedback (Fibonacci form): s_new = alpha * s[0] XOR s[2] XOR alpha^-1 * s[11] XOR s[15]

#   s_<t , i> is LFSR cell i at clock t
#   r1_<t> is FSM register r1 at clock t
#   r2_<t> is FSM register r2 at clock t
#   v_<t> is FSM output at clock t (derived: s_t_15, r1_t, r2_t)
#   z_<t> is keystream word at clock t (KNOWN)
###############################################   HUGE SHUTOUT TO THOSE WORKS https://ela.kpi.ua/server/api/core/bitstreams/2b34f986-0c3f-45fc-868a-bae33cdbcafb/content    &    https://ela.kpi.ua/server/api/core/bitstreams/974135ee-ddc2-4e94-a28d-9c5c43fa868a/content
### Most of the code logic here and in strumok512_restore is made based on those works where they provided a lot of neccessary information. 
# Like honestly, those works saved me. BUT I`m not quite sure the file will work, I kinda borrowed my sisters laptop to test the model in those days, but she had to 
# confiscate her laptop with mac os from me - so I have no clear idea if the output format is ok for the autoguesser because I failed to install a virtual machine for that by myself (libraries conflict)
NUM_CLOCKS = 11   # as required in the task
LFSR_SIZE  = 16
def s(t, i):
    return f"s_{t}_{i}"
def r1(t):
    return f"r1_{t}"
def r2(t):
    return f"r2_{t}"
def v(t):
    return f"v_{t}"
def z(t):
    return f"z_{t}"

def generate_relation_file(num_clocks=NUM_CLOCKS, output_file = None):
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, f"strumok512_{num_clocks}clk_1.txt")
    lines = []
    lines.append(f"# Strumok-512 relation file for Autoguess")
    lines.append(f"# {num_clocks} clock ticks, 64-bit word variables")
    lines.append(f"# LFSR length = 16 (cells s_t_0 .. s_t_15)")
    lines.append(f"# FSM: registers r1_t, r2_t; output v_t; keystream z_t (known)")
    lines.append(f"# State at t=0: s_0_0..s_0_15, r1_0, r2_0  (18 unknowns = 1152 bits)")
    lines.append(f"# Attack target: recover all state variables at t=0")
    lines.append(f"# Complexity target: 2^448 = 7 x 64-bit words to guess")
    lines.append(f"connection relations")

    for t in range(num_clocks):
        lines.append(f"#Clock tick t={t} -> t+1")

        for i in range(15): # LFSR shift: s_{t+1}_i = s_t_{i+1} for i=0..14
            lines.append(f"{s(t,i+1)}, {s(t+1,i)}")
        lines.append(f"")

        lines.append(f"# LFSR feedback") # s_{t+1}_15 from s_t_0, s_t_2, s_t_11, s_t_15
        lines.append(f"{s(t,0)}, {s(t,2)}, {s(t,11)}, {s(t,15)} => {s(t+1,15)}")
        lines.append(f"")

        lines.append(f"# FSM output") # v_t = (s_t_15 + r1_t) XOR r2_t  we have two of the three FSM variables and we need to find v
        lines.append(f"{s(t,15)}, {r1(t)}, {r2(t)} => {v(t)}")
        # backward: v_t and r2_t => (s_t_15 + r1_t), but cannot split sum from just XOR
        # but we know v_t + r2_t and r2_t => v_t (XOR part): if both r1 and r2 are known => s_t_15
        lines.append(f"{v(t)}, {r1(t)}, {r2(t)} => {s(t,15)}")
        lines.append(f"")

        lines.append(f"# FSM r2 update") # r2_{t+1} = T(r1_t)
        lines.append(f"{r1(t)} => {r2(t+1)}")
        lines.append(f"{r2(t+1)} => {r1(t)}")
        lines.append(f"")

        lines.append(f"# FSM r1 update") # r1_{t+1} = r2_t + (s_t_5 XOR r1_t) and by knowing all three inputs - determin r1_{t+1}
        lines.append(f"{r2(t)}, {s(t,5)}, {r1(t)} => {r1(t+1)}")
        # Backward: r1_{t+1} - r2_t = s_t_5 XOR r1_t => need r2_t and one of {s_t_5, r1_t} and knowing r1_{t+1} and r2_t and r1_t => s_t_5 XOR r1_t => s_t_5
        lines.append(f"{r1(t+1)}, {r2(t)}, {r1(t)} => {s(t,5)}")
        # knowing r1_{t+1} and r2_t and s_t_5 => r1_t (from XOR + subtraction)
        # r1_{t+1} = r2_t + (s_t_5 XOR r1_t), so (s_t_5 XOR r1_t) = r1_{t+1} - r2_t then s_t_5 XOR r1_t is known, and if s_t_5 is known => r1_t, or if r1_t known => s_t_5
        lines.append(f"{r1(t+1)}, {r2(t)}, {s(t,5)} => {r1(t)}")
        lines.append(f"")

        lines.append(f"# Keystream ")# z_t = v_t XOR s_t_0 where z_t is known
        lines.append(f"{s(t,0)}, {z(t)} => {v(t)}")
        lines.append(f"{v(t)}, {z(t)} => {s(t,0)}")
        # symmetry of z_t, v_t, s_t_0 is any two determine the third
        lines.append(f"{v(t)}, {s(t,0)} => {z(t)}")
        lines.append(f"")
    lines.append(f"")
    lines.append(f"known")
    
    for t in range(num_clocks):# Keystream words z_0 .. z_{num_clocks-1} are known
        lines.append(f"{z(t)}")
    lines.append(f"")
    lines.append(f"target")

    for i in range(LFSR_SIZE): # all LFSR cells and FSM registers must be at t=0
        lines.append(f"{s(0,i)}")
    lines.append(f"{r1(0)}")
    lines.append(f"{r2(0)}")

    lines.append(f"")
    lines.append(f"end")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Written: {output_file}")

    var_set = set()
    rel_count = 0
    in_relations = False
    for line in lines:
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        if line == "connection relations":
            in_relations = True
            continue
        if line in ("known", "target", "end"):
            in_relations = False
            continue
        if in_relations:
            rel_count += 1
            parts = line.replace("=>", ",").split(",")
            for p in parts:
                p = p.strip()
                if p:
                    var_set.add(p)
        else:
            var_set.add(line.strip())

    print(f"Variables: {len(var_set)}")
    print(f"Relations: {rel_count}")
    print(f"Target variables: {LFSR_SIZE + 2} = {LFSR_SIZE} LFSR + 2 FSM = 18 x 64-bit = 1152 bites")
    print(f"Attack goal: guess 7 x 64-bit words (complexity 2^448 < 2^512)")

    return output_file

import sys
n = int(sys.argv[1]) if len(sys.argv) > 1 else NUM_CLOCKS
out = sys.argv[2] if len(sys.argv) > 2 else None
out_path = generate_relation_file(num_clocks=n, output_file=out)

print(f"\nUsage with Autoguess (SAT solver, targeting 7 guesses):")
print(f"python3 autoguess.py --inputfile \"{out_path}\" --solver sat --maxguess 7 --maxsteps 20")

print(f"\nUsage with Autoguess (CP solver):")
print(f"python3 autoguess.py --inputfile \"{out_path}\" --solver cp --maxsteps 20")

print(f"\nUsage with Autoguess (Groebner):")
print(f"python3 autoguess.py --inputfile \"{out_path}\" --solver groebner")