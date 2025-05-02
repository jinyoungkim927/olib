import re

text = """#data-science #ML  

[[Ridge Regression]] (L2 [[Regularization]]) is a penalty on the L2 norm of the [[Beta]] coefficients in [[Linear [[Regression]]]]. As with all [[Regularization]], it combats overfitting by shrinking coefficient magnitudes.  

**Motivation**  
- Mitigates [[Multicollinearity]], particularly in models with highly correlated predictors.  
- Stabilizes estimates, reducing [[Variance]] at the cost of some [[Bias]].  
- Improves [[Efficient|efficiency]] in parameter estimation.  
- Unlike [[Lasso Regression|Lasso (L1)]], it does not eliminate features but shrinks all coefficients.  

**Key Properties**  
- Primarily prevents overfitting rather than performing [[Feature Selection]].  
- Retains all features but penalizes large coefficients, making it more stable when predictors are correlated.  
- [[Lasso Regression]] arbitrarily selects features, potentially leading to high-Variance models, whereas [[Ridge [[Regression]]] shrinks them continuously.  

**Solving for [[Beta]] / [[Optimisation Problem]]**
- **Solving Methods**
	- [[[[Normal]]]] Equation (closed form): [[[[Efficient]]]] for small to medium-sized datasets. Computationally expensive for large datasets due to $O(p^3)$ complexity.  
	- [[Conjugate]] [[Gradient Descent]]: Solves $(X^TX + \lambda I)\beta = X^Ty$ iteratively without inverting the matrix. Useful for sparse feature matrices.  
	- Alternating Direction Method of Multipliers ([[[[ADMM]]]]): Optimized for distributed Ridge [[Regression]], commonly used in big data settings, parallelizable and [[[[Efficient]]]] on GPU clusters.  
- **Real-World Considerations**  
	- Ridge is robust when dealing with correlated features since it shrinks them instead of discarding them.  
	- Selecting **$\lambda$** is crucial:  
		- High $\lambda$ → Excessive shrinkage, increasing [[Bias]].  
		- Low $\lambda$ → Weak [[Regularization]], reducing benefits.  
	- Ridge is commonly used in [[[[Elastic Net]]]], combining Ridge and Lasso for improved performance.  
	- Libraries: 
		- `scikit-learn`: [[[[Efficient]]]] closed form, SGD solvers
		- `Spark MLib`: Scalable [[Ridge [[[[Regression]]]]] for distributed data
		- `tensorflow + pytorch`: Implemented via L2 weight decay in deep learning models

**Math: Solution for [[[[Beta]]]]**  
Ridge [[[[Regression]]]] minimizes the penalized sum of squared errors:  
$\hat{\beta}^{\text{ridge}} = \arg\min_{\[[Beta]]} \left\{ \sum_{i=__SIMPLE_LINK_12__}^{N} (y_i - \beta_0 - \sum_{j=__SIMPLE_LINK_12__}^{p} x_{ij} \beta_j)^2 + \lambda \sum_{j=__SIMPLE_LINK_12__}^{p} \beta_j^2 \right\}$  
Closed-form solution:  
$\hat{\beta}_R = (X^TX + \lambda I)^{-__SIMPLE_LINK_12__}X^Ty$  
where $\lambda$ controls the [[Regularization]] strength.  
"""

from obsidian_librarian.commands.format import fix_math_formatting

print("BEFORE:")
print("=" * 80)
print(text)
print("=" * 80)

fixed = fix_math_formatting(text)

print("\nAFTER:")
print("=" * 80)
print(fixed)
print("=" * 80)

# Count how many changes were made
print("\nCHANGES DETECTED:")
nested_wiki_count = len(re.findall(r'\[\[.*?\[\[.*?\]\].*?\]\]', text))
triple_bracket_count = len(re.findall(r'\[{3,}[^\[\]]+?\]{3,}', text))
simple_link_count = len(re.findall(r'__SIMPLE_LINK_\d+__', text))

print(f"- Nested wiki links: {nested_wiki_count}")
print(f"- Triple or more brackets: {triple_bracket_count}")
print(f"- Simple link placeholders: {simple_link_count}")
print("\nTotal potential issues: {0}".format(nested_wiki_count + triple_bracket_count + simple_link_count))

if text == fixed:
    print("\nERROR: No changes were made\! The formatter didn't fix anything.")
else:
    print("\nSUCCESS: The formatter made changes to the text.")
