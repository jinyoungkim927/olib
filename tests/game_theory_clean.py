#!/usr/bin/env python3
"""
Final clean formatter for game theory example.
"""
import re

# Input text from original example
input_text = """# Game Theory Example

**5. Subgame-Perfect Equilibria in Repeated Zero-Sum Games**

Let $G = \langle N, A, g \rangle $ be a finite, two-player, zero-sum game with $ N = {1,2}$, $ A = A_1 \times A_2 $, and $ g_1(a) = u(a)$, $ g_2(a) = -u(a)$ for $ a = (a_1, a_2) \in A $.

Let $ v_1 $ and $ v_2 $ denote the maxmin values of players 1 and 2 respectively in the stage game $ G $. By the minimax theorem,

$$
v_1 = \max_{x_1 \in \Delta(A_1)} \min_{x_2 \in \Delta(A_2)} \mathbb{E}[u(x_1, x_2)] = \min_{x_2 \in \Delta(A_2)} \max_{x_1 \in \Delta(A_1)} \mathbb{E}[u(x_1, x_2)] =: v
$$

Then

$$
v_2 = \max_{x_2 \in \Delta(A_2)} \min_{x_1 \in \Delta(A_1)} \mathbb{E}[-u(x_1, x_2)] = -v
$$

So $ v_1 + v_2 = 0 $.

A mixed action $ x_1^* \in \Delta(A_1)$ is a maxmin action for player 1 if $\mathbb{E}[u(x_1^*, x_2)] \geq v_1 $ for all $ x_2 \in \Delta(A_2)$. Similarly, $ x_2^* \in \Delta(A_2)$ is a maxmin action for player 2 if $\mathbb{E}[u(x_1, x_2^*)] \leq v_1 $ for all $ x_1 \in \Delta(A_1)$.

Then $(x_1^*, x_2^*)$ is a Nash equilibrium of the stage game with payoff vector $(v_1, v_2)$.

The repeated game has discounted payoffs:

$$
U_i(\sigma_1, \sigma_2) = \mathbb{E}\left[(1 - \delta) \sum_{t=0}^{\infty} \delta^t g_i(a^t)\right]
$$

**(a) Nash equilibrium implies maxmin payoffs**

Let $(\sigma_1, \sigma_2)$ be a Nash equilibrium of the repeated game. Player 1 can guarantee at least $ v_1 $ by playing a stationary strategy $\sigma_1'$ that always plays a maxmin action $ x_1^*$. Then:

$$
u_1(\sigma_1', \sigma_2) = (1 - \delta) \sum_{t=0}^{\infty} \delta^t \mathbb{E}[u(x_1^*, x_2^t)] \geq v_1
$$

Hence $ u_1(\sigma_1, \sigma_2) \geq v_1 $. By symmetry and the zero-sum property, we also get $ u_2(\sigma_1, \sigma_2) \geq v_2 $ and $ u_1 + u_2 = 0 $. Therefore,

$$
u_1(\sigma_1, \sigma_2) \geq v_1 \quad \text{and} \quad u_1(\sigma_1, \sigma_2) \leq v_1 \Rightarrow u_1 = v_1, \quad u_2 = v_2
$$"""

# Perform minimal manual fixes to correctly format the LaTeX spacing

# 1. Clean display math - compact each display math block into a single line with no internal newlines
def fix_display_math(match):
    inner = match.group(1).strip().replace('\n', ' ')
    return f"$${inner}$$"

output = re.sub(r'\$\$(.*?)\$\$', fix_display_math, input_text, flags=re.DOTALL)

# 2. Fix inline math - remove extra spaces inside dollar signs
output = re.sub(r'\$\s+(.*?)\s+\$', r'$\1$', output)

# 3. Format display math to be exactly as desired - this is a custom approach for the game theory text
output = output.replace("$$\nv_1", "$$v_1")
output = output.replace("$$\nv_2", "$$v_2")
output = output.replace("$$\nU_i", "$$U_i")
output = output.replace("$$\nu_1", "$$u_1")

# 4. Fix spacing between inline math and text
output = re.sub(r'(\$[^\$\n]+\$)([a-zA-Z0-9])', r'\1 \2', output)
output = re.sub(r'([a-zA-Z0-9])(\$[^\$\n]+\$)', r'\1 \2', output)

# Write the output
with open('tests/game_theory_final.md', 'w', encoding='utf-8') as f:
    f.write(output)

print("Formatted version written to tests/game_theory_final.md")