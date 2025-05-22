# Game Theory Example

**5. Subgame-Perfect Equilibria in Repeated Zero-Sum Games**

Let $G = \langle N, A, g \rangle$ be a finite, two-player, zero-sum game with $N = \{1,2\}$, $A = A_1 \times A_2$, and $g_1(a) = u(a)$, $g_2(a) = -u(a)$ for $a = (a_1, a_2) \in A$.

Let $v_1$ and $v_2$ denote the maxmin values of players 1 and 2 respectively in the stage game $G$. By the minimax theorem, 
$$v_1 = \max_{x_1 \in \Delta(A_1)} \min_{x_2 \in \Delta(A_2)} \mathbb{E}[u(x_1, x_2)] = \min_{x_2 \in \Delta(A_2)} \max_{x_1 \in \Delta(A_1)} \mathbb{E}[u(x_1, x_2)] =: v$$

Then 
$$v_2 = \max_{x_2 \in \Delta(A_2)} \min_{x_1 \in \Delta(A_1)} \mathbb{E}[-u(x_1, x_2)] = -v$$

So $v_1 + v_2 = 0$.

A mixed action $x_1^* \in \Delta(A_1)$ is a maxmin action for player 1 if $\mathbb{E}[u(x_1^*, x_2)] \geq v_1$ for all $x_2 \in \Delta(A_2)$. Similarly, $x_2^* \in \Delta(A_2)$ is a maxmin action for player 2 if $\mathbb{E}[u(x_1, x_2^*)] \leq v_1$ for all $x_1 \in \Delta(A_1)$.

Then $(x_1^*, x_2^*)$ is a Nash equilibrium of the stage game with payoff vector $(v_1, v_2)$.

The repeated game has discounted payoffs:

$$U_i(\sigma_1, \sigma_2) = \mathbb{E}\left[(1 - \delta) \sum_{t=0}^{\infty} \delta^t g_i(a^t)\right]$$


**(a) Nash equilibrium implies maxmin payoffs**

Let $(\sigma_1, \sigma_2)$ be a Nash equilibrium of the repeated game. Player 1 can guarantee at least $v_1$ by playing a stationary strategy $\sigma_1'$ that always plays a maxmin action $x_1^*$. Then:

$$u_1(\sigma_1', \sigma_2) = (1 - \delta) \sum_{t=0}^{\infty} \delta^t \mathbb{E}[u(x_1^*, x_2^t)] \geq v_1$$

Hence $u_1(\sigma_1, \sigma_2) \geq v_1$. By symmetry and the zero-sum property, we also get $u_2(\sigma_1, \sigma_2) \geq v_2$ and $u_1 + u_2 = 0$. Therefore, 
$$u_1(\sigma_1, \sigma_2) \geq v_1 \quad \text{and} \quad u_1(\sigma_1, \sigma_2) \leq v_1 \Rightarrow u_1 = v_1, \quad u_2 = v_2$$

**(b) Subgame-perfect equilibrium implies maxmin payoffs**

Let $(\sigma_1, \sigma_2)$ be a subgame-perfect equilibrium of the repeated game. By definition, the strategies induce a Nash equilibrium in every subgame. Since every history $h^t$ leads to a subgame that is strategically equivalent to the original repeated game, the continuation value from any history must also be $(v_1, v_2)$ by the same argument as in part (a).

For any history $h^t$, let $V_i(h^t)$ represent player $i$'s continuation value. Then:

$$V_1(h^t) = v_1 \quad \text{and} \quad V_2(h^t) = v_2 \quad \forall h^t$$

This shows that in any subgame-perfect equilibrium, players must receive their maxmin values, regardless of the history of play.

**(c) Actions played in SPE are maxmin actions**

Let $(\sigma_1, \sigma_2)$ be a subgame-perfect equilibrium of the repeated game. We will show that at each stage, players must play their maxmin actions.

Suppose that at some history $h^t$, player 1 plays an action $x_1^t$ that is not a maxmin action. Then there exists some action $x_2$ for player 2 such that $\mathbb{E}[u(x_1^t, x_2)] < v_1$.

If player 2 deviates to play $x_2$ at this history, player 1's stage payoff would be strictly less than $v_1$. Since the continuation value from any history is exactly $v_1$ (as shown in part (b)), this would make player 1's total discounted payoff less than $v_1$:

$$(1-\delta) \mathbb{E}[u(x_1^t, x_2)] + \delta v_1 < (1-\delta)v_1 + \delta v_1 = v_1$$

This contradicts the fact that player 1 can guarantee at least $v_1$ by playing a maxmin action. Therefore, player 1 must play a maxmin action at every history.

By symmetry, player 2 must also play a maxmin action at every history. Thus, in any subgame-perfect equilibrium, both players must play maxmin actions at every stage of the game.

**(d) Converse: maxmin actions lead to SPE**

We now show that any strategy profile where both players always play maxmin actions constitutes a subgame-perfect equilibrium.

Let $\sigma_1$ be a strategy where player 1 plays a maxmin action $x_1^*$ after every history, and $\sigma_2$ be a strategy where player 2 plays a maxmin action $x_2^*$ after every history.

At any history $h^t$, if player 1 deviates to some other action $x_1$, their stage game payoff would be:

$$\mathbb{E}[u(x_1, x_2^*)] \leq v_1$$

Since player 2 is playing a maxmin action, player 1 cannot get more than $v_1$ in the stage game. The continuation value remains $v_1$ regardless of the deviation. Therefore, player 1 cannot improve their payoff by deviating.

Similarly, player 2 cannot improve their payoff by deviating from $x_2^*$ at any history.

Therefore, $(\sigma_1, \sigma_2)$ is a subgame-perfect equilibrium.

**Conclusion**

In repeated zero-sum games, the only possible payoff in any subgame-perfect equilibrium is the pair of maxmin values $(v_1, v_2)$. Moreover, players must play maxmin actions at every stage of the game. This illustrates a fundamental property of repeated zero-sum games: repetition does not allow players to escape the strategic constraints of the stage game. Unlike in general-sum games, where cooperation can emerge through repetition, zero-sum games maintain their strictly competitive character even when played repeatedly.