[[Shapley Values]] $\phi_i(v)$ for player $i$ is the average of $i___DISPLAY_MATH_PLACEHOLDER_0___\phi_i(v) = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!(n - |S| - 1)!}{n!} \left[v(S \cup \{i\}) - v(S)\right]___DISPLAY_MATH_PLACEHOLDER_1___\pi$ of players; for each $\pi$, $ i___DISPLAY_MATH_PLACEHOLDER_2___v(\text{predecessors of } i \cup \{i\}) - v(\text{predecessors of } i)___DISPLAY_MATH_PLACEHOLDER_3___N = {1, \dots, n}$and a [[Characteristic Function]]$ v: 2^N \to \mathbb{R}$assigning a value $ v(S)$to each coalition $ S \subseteq N$such that $ v(\emptyset) = 0$.

**Goal**
Distribute total value $ v(N)$ among players fairly based on their marginal contributions.

**Axioms Characterizing the Shapley Value**

1. Efficiency: $\sum_{i \in N} \phi_i(v) = v(N)$ 2. Symmetry: If $v(S \cup{i}) = v(S \cup{j})$ for all $S \not\ni i,j$, then $\phi_i(v) = \phi_j(v)$ 3. Dummy player: If $v(S \cup{i}) = v(S)$ for all $S$, then $\phi_i(v) = 0 $ 4. Additivity: For games$v,w $, $\phi_i(v + w) = \phi_i(v) + \phi_i(w)$

**Properties**

- Unique: Shapley value is the unique function satisfying the above axioms.
- Linearity: Computation decomposes over basis games.
- Fairness: Reflects marginal contributions over uncertainty about coalition formation.

**Special Case: 3-player Example**
Let $ N = {1,2,3}___DISPLAY_MATH_PLACEHOLDER_4___\phi_1 = \frac{1}{6} \sum_{\pi} \text{marginal contribution of } 1 \text{ in } \pi___DISPLAY_MATH_PLACEHOLDER_5___v({1}) = 1 $, $ v({1,2}) = 4 $, $ v({1,2,3}) = 7 $, compute $\phi_i $ for each player.

**Applications**

- Cost/revenue sharing in coalition settings
- Attribution in machine learning (e.g., SHAP)
- Voting power (Banzhaf vs. Shapley-Shubik indices)

**Computation Complexity**

- Exact computation is exponential in $ n $(due to summation over$ 2^n$ subsets)
- Approximation via sampling permutations (Monte Carlo methods)