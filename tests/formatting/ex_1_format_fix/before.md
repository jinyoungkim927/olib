# game-theory

Here is the full solution in your preferred markdown and LaTeX format, following your style conventions for technical rigor and concision.

---

**5. Subgame-Perfect Equilibria in Repeated Zero-Sum Games**

Let \$G = \langle N, A, g \rangle\$ be a finite, two-player, zero-sum game with \$N = {1,2}\$, \$A = A\_1 \times A\_2\$, and \$g\_1(a) = u(a)\$, \$g\_2(a) = -u(a)\$ for \$a = (a\_1, a\_2) \in A\$.

Let \$v\_1\$ and \$v\_2\$ denote the maxmin values of players 1 and 2 respectively in the stage game \$G\$. By the minimax theorem,

$$
v_1 = \max_{x_1 \in \Delta(A_1)} \min_{x_2 \in \Delta(A_2)} \mathbb{E}[u(x_1, x_2)] = \min_{x_2 \in \Delta(A_2)} \max_{x_1 \in \Delta(A_1)} \mathbb{E}[u(x_1, x_2)] =: v
$$

Then

$$
v_2 = \max_{x_2 \in \Delta(A_2)} \min_{x_1 \in \Delta(A_1)} \mathbb{E}[-u(x_1, x_2)] = -v
$$

So \$v\_1 + v\_2 = 0\$.

A mixed action \$x\_1^\* \in \Delta(A\_1)\$ is a maxmin action for player 1 if \$\mathbb{E}\[u(x\_1^*, x\_2)] \geq v\_1\$ for all \$x\_2 \in \Delta(A\_2)\$. Similarly, \$x\_2^* \in \Delta(A\_2)\$ is a maxmin action for player 2 if \$\mathbb{E}\[u(x\_1, x\_2^\*)] \leq v\_1\$ for all \$x\_1 \in \Delta(A\_1)\$.

Then \$(x\_1^*, x\_2^*)\$ is a Nash equilibrium of the stage game with payoff vector \$(v\_1, v\_2)\$.

The repeated game has discounted payoffs:

$$
U_i(\sigma_1, \sigma_2) = \mathbb{E}\left[(1 - \delta) \sum_{t=0}^{\infty} \delta^t g_i(a^t)\right]
$$

**(a) Nash equilibrium implies maxmin payoffs**

Let \$(\sigma\_1, \sigma\_2)\$ be a Nash equilibrium of the repeated game. Player 1 can guarantee at least \$v\_1\$ by playing a stationary strategy \$\sigma\_1'\$ that always plays a maxmin action \$x\_1^\*\$. Then:

$$
u_1(\sigma_1', \sigma_2) = (1 - \delta) \sum_{t=0}^{\infty} \delta^t \mathbb{E}[u(x_1^*, x_2^t)] \geq v_1
$$

Hence \$u\_1(\sigma\_1, \sigma\_2) \geq v\_1\$. By symmetry and the zero-sum property, we also get \$u\_2(\sigma\_1, \sigma\_2) \geq v\_2\$ and \$u\_1 + u\_2 = 0\$. Therefore,

$$
u_1(\sigma_1, \sigma_2) \geq v_1 \quad \text{and} \quad u_1(\sigma_1, \sigma_2) \leq v_1 \Rightarrow u_1 = v_1, \quad u_2 = v_2
$$

**(b) Subgame-perfect equilibrium implies maxmin payoffs in every subgame**

Let \$(\sigma\_1, \sigma\_2)\$ be a subgame-perfect equilibrium. Then for any history \$h\$, the continuation strategy \$(\sigma\_1|h, \sigma\_2|h)\$ is a Nash equilibrium of the subgame. By (a), we must have:

$$
u_i(\sigma_1, \sigma_2 \mid h) = v_i \quad \text{for all } h
$$
