# game-theory

![[Screenshot 2025-05-21 at 9.55.32 am.png]]

![[Screenshot 2025-05-21 at 9.55.38 am.png]]
---

OCR processing: 2025-05-21 14:09:52

**Weak Perfect Bayesian Equilibrium (wPBE)**

**Key Concepts**

- **Deviation at Positive-Probability Info Sets**: A profitable deviation at a positive-probability information set would be profitable ex ante.
- **Nash Equilibrium (NE) vs. wPBE**:
- NE imposes no restriction on strategies at zero-probability information sets.
- wPBE requires them to be sequentially rational given some beliefs.

**Problem with wPBE**

- **Weird Beliefs at Zero-Probability Info Sets**: wPBE allows unusual beliefs at zero-probability information sets, which may sustain unintuitive equilibria.

**Example 1**

**Game Structure**

- The game tree is as follows:
- Player 2 can choose between "Out" and "In".
- If "Out" is chosen, the payoff is (2, 0).
- If "In" is chosen, Player 1 can choose between "A" and "F".
- If Player 1 chooses "A", Player 2 can again choose between "A" and "F".
- Payoffs for the choices are:
- (1, 1) for (A, A)
- (-1, -1) for (A, F)
- (-1, -2) for (F, A)
- (0, -2) for (F, F)

**Analysis**

- The game has a wPBE where Player 2 plays (Out, A) and Player 1 plays F, supported by Player 1's belief at the zero-probability information set that Player 2 played F.
- This is not a Subgame Perfect Equilibrium (SPE):
- In the subgame following "In", Player 2's strictly dominant strategy is A.
- Player 1's unique best response to A is A.
- Therefore, the only SPE is ((In, A), A).

**Problem and Ad Hoc Fix**

- A wPBE need not be an SPE. An ad hoc fix is proposed:
- Require wPBE in each subgame (hence, NE in each subgame, hence, SPE).
- Adding a redundant action "In'" for Player 2, which has the same continuation game as "In" but Player 1 doesn’t observe which was chosen, results in no proper subgames. The "bad" PBE remains, even though entry by Player 2 seems to be the unique plausible outcome.

![[Screenshot 2025-05-21 at 9.55.46 am.png]]
---

OCR processing: 2025-05-21 14:10:17

**Weak Perfect Bayesian Equilibrium (wPBE)**

**Example 2**

**Game Description**

- **Initial Move by Nature (Player 0):**
- With probability 0.99, Nature moves left, resulting in "normal" payoffs.
- With probability 0.01, Nature moves right, resulting in "weird" payoffs where Player 1 prefers $F$to$A$.
- **Game Tree:**
- **Node 0:*- Nature's move.
- **Left (0.99 probability):*-
- Player 2 chooses between "Out" (payoff 2,0) and "In".
- If "In," Player 1 chooses between "A" (payoff 1,1) and "F" (payoff -1,-1).
- **Right (0.01 probability):**
- Player 2 chooses between "Out" (payoff 2,0) and "In".
- If "In," Player 1 chooses between "A" (payoff -1,1) and "F" (payoff 1,-1).

**Analysis**

- **Beliefs and Moves:**
- Nobody observes Nature's move.
- On expectation, $A$is better than$F$.
- A wPBE exists where Player 2 goes "Out" and Player 1 assigns 1% belief to the "weird" state and 99% to the "normal" state after "In," leading Player 1 to choose $F$.
- **Outcome:**
- In this wPBE, Player 2's move "signals what he doesn’t know" (Nature’s move), resulting in a counterintuitive outcome.

**Strong PBE**

- **Definition by Fudenberg & Tirole:**
- Imposes restrictions such as "no signaling what you don’t know."
- Other authors may impose subsets of restrictions depending on the application.

**General Approach to Restrictions**

- **Trembles:**
- Assign probability to zero information sets by attributing them to "trembles" by opponents.
- Opponents are assumed to have "trembling hands" and thus play fully mixed strategies.
- All information sets have a positive probability, and all beliefs are refined by Bayesian updating.
- **Convergence:**
- As trembles shrink and beliefs converge to equilibrium strategies, the probability of some strategies becomes negligible.

![[Screenshot 2025-05-21 at 9.55.52 am.png]]

![[Screenshot 2025-05-21 at 9.56.00 am.png]]

![[Screenshot 2025-05-21 at 9.56.07 am.png]]

![[Screenshot 2025-05-21 at 9.56.15 am.png]]
---

OCR processing: 2025-05-21 14:11:58

**Notes on Weak Perfect Bayes Equilibrium**

**Game Equivalence and Strategic Stability**

- Some argue that the game discussed is equivalent to Example 1, where the only Subgame Perfect Equilibrium (SPE) was $(( ext{In}, A), A)$. This raises the question of whether predictions should be invariant to whether player 1 makes two decisions simultaneously or sequentially. In normal form, these games are essentially the same, with player 2's strategies $( ext{Out}, A)$and$( ext{Out}, F)$combined into a single strategy,$ ext{Out}$.
- Kohlberg-Mertens aimed to unify various arguments by introducing "strategic stability," which assumes that only the normal-form representation matters and incorporates "trembles." However, this concept faced challenges:
  1. Generally, no single strategy profile survived, necessitating the definition of a "stable set."
  2. The original concept wasn't always consistent with backward induction, prompting the development of later concepts to address this.

- Due to complexities, instead of pursuing a "universal" solution concept, game theorists have focused on tailored refinements for specific applications, combining "backward induction" and "forward induction" reasoning.

**Signaling Games**

- **Question:*- Why do employers pay more for Stanford graduates? Is it because Stanford teaches useful skills, or because Stanford graduates tend to be smarter?
- **Answer:*- Probably a bit of both.
- **Question:*- Why can't less smart students work harder and get into Stanford to mimic smarter students?
- **Answer:*- It may be too hard for them.

**Footnote on Trembles**

- "Trembles" are defined as shrinking positive lower bounds on the probabilities of choosing each action. All sequences of Nash equilibria where players optimize under these bounds converge to the putative equilibrium as the trembles vanish. This eliminates $( ext{Out}, F)$, as player 2 would always place the minimal probability on $F$. If the minimal probability is low, player 1 would prefer $A$. The strategy $(( ext{In}, A), A)$ survives as it is a strict Nash Equilibrium (NE). When the other player plays this equilibrium strategy with high probability, the best response is to play one's equilibrium strategy with maximal probability allowed by trembles.

![[Screenshot 2025-05-21 at 9.56.22 am.png]]

![[Screenshot 2025-05-21 at 9.56.46 am.png]]

![[Screenshot 2025-05-21 at 9.56.55 am.png]]

![[Screenshot 2025-05-21 at 9.57.04 am.png]]

![[Screenshot 2025-05-21 at 9.57.10 am.png]]

![[Screenshot 2025-05-21 at 9.57.21 am.png]]

![[Screenshot 2025-05-21 at 9.57.29 am.png]]

![[Screenshot 2025-05-21 at 9.57.37 am.png]]

![[Screenshot 2025-05-21 at 9.57.44 am.png]]

![[Screenshot 2025-05-21 at 9.57.55 am.png]]

![[Screenshot 2025-05-21 at 9.58.02 am.png]]

![[Screenshot 2025-05-21 at 9.58.09 am.png]]
---

OCR processing: 2025-05-21 14:15:52

**Weak Perfect Bayesian Equilibrium (wPBE)**

**Uninformative "Babbling" wPBE**

- For any finite set $A_1$, there exists an uninformative "babbling" wPBE.
- In this equilibrium, the Sender randomizes over $A_1$with a full-support distribution that is independent of$ heta$.
- The Receiver ignores the message and chooses $1/2$.
- As all messages are used with probability $>0$, no refinement can eliminate this equilibrium.
- Any other wPBE outcome can also be sustained with the Sender's full-support strategy.

**Restricting Equilibria to "Succinct" Messages**

- Consider restricting equilibria to use "succinct" messages, meaning some messages in the large space $A_1$ must remain unused.

**Sequential Equilibrium**

- Allows for the assignment of arbitrary beliefs following unused messages.
- These beliefs can be "punishing" to prevent deviations.

**Forward-Induction Reasoning**

- May allow the Sender to use unused messages as "credible" signals.
- This leads to the "neologism-proofness" refinement.
