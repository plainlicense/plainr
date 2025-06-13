# /// script
# requires_python = ">=3.12"
# dependencies = ["matplotlib", "numpy"]
# ///
import math

import matplotlib.pyplot as plt
import numpy as np


# Original Flesch grade mapping (converted to single values)
original_data = [
    (95, 5),  # 90-100 -> 5
    (85, 6),  # 80-90 -> 6
    (75, 7),  # 70-80 -> 7
    (65, 8.5),  # 60-70 -> 8,9 (midpoint)
    (55, 11),  # 50-60 -> 10,11,12 (midpoint)
    (40, 14),  # 30-50 -> "college" (assume ~14)
    (15, 16),  # 0-30 -> "college_graduate" (assume ~16)
]

scores = [x[0] for x in original_data]
grades = [x[1] for x in original_data]

# Generate test scores for plotting
test_scores = np.linspace(0, 100, 101)


# Option 1: Piecewise Linear
def piecewise_linear(score):
    if score >= 70:
        return max(5, 12 - score / 10)
    if score >= 50:
        return 16 - score / 2.5
    if score <= 0:
        return 18
    return min(18, 13 + 5 * math.log10(51 - score))


# Option 2: Sigmoid
def sigmoid_approach(score):
    a, b, c, d = 5, 13, 0.08, 60
    grade = a + b / (1 + math.exp(c * (score - d)))
    return grade


# Option 3: Power Law
def power_law(score):
    normalized = (100 - score) / 100
    k, p = 13, 1.8
    grade = 5 + k * (normalized**p)
    return grade


# Option 4: Simple inverse linear (baseline)
def simple_inverse(score):
    return 5 + (100 - score) * 13 / 100


# Calculate all approaches
piecewise_grades = [piecewise_linear(s) for s in test_scores]
sigmoid_grades = [sigmoid_approach(s) for s in test_scores]
power_grades = [power_law(s) for s in test_scores]
simple_grades = [simple_inverse(s) for s in test_scores]

# Plot
plt.figure(figsize=(12, 8))
plt.plot(test_scores, piecewise_grades, label="Piecewise Linear", linewidth=2)
plt.plot(test_scores, sigmoid_grades, label="Sigmoid", linewidth=2)
plt.plot(test_scores, power_grades, label="Power Law", linewidth=2)
plt.plot(test_scores, simple_grades, label="Simple Inverse", linewidth=2, alpha=0.7)

# Plot original data points
plt.scatter(scores, grades, color="red", s=100, zorder=5, label="Original Data Points")

plt.xlabel("Flesch Reading Ease Score")
plt.ylabel("Grade Level")
plt.title("Mathematical Approaches to Flesch Grade Level Mapping")
plt.legend()
plt.grid(True, alpha=0.3)
plt.xlim(0, 100)
plt.ylim(4, 18)

# Add annotations for key points
for score, grade in original_data:
    plt.annotate(
        f"({score}, {grade})",
        (score, grade),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8,
    )

plt.tight_layout()
plt.show()


# Let's also see how well each fits by calculating RMSE
def calculate_rmse(predicted, actual):
    return np.sqrt(
        np.mean([(p - a) ** 2 for p, a in zip(predicted, actual, strict=False)])
    )


# Get predictions for original data points
piecewise_pred = [piecewise_linear(s) for s in scores]
sigmoid_pred = [sigmoid_approach(s) for s in scores]
power_pred = [power_law(s) for s in scores]
simple_pred = [simple_inverse(s) for s in scores]

print("RMSE for each approach:")
print(f"Piecewise Linear: {calculate_rmse(piecewise_pred, grades):.3f}")
print(f"Sigmoid: {calculate_rmse(sigmoid_pred, grades):.3f}")
print(f"Power Law: {calculate_rmse(power_pred, grades):.3f}")
print(f"Simple Inverse: {calculate_rmse(simple_pred, grades):.3f}")

print("\nDetailed predictions vs actual:")
print("Score | Actual | Piecewise | Sigmoid | Power | Simple")
print("-" * 55)
for i, (score, actual) in enumerate(zip(scores, grades, strict=False)):
    print(
        f"{score:5.0f} | {actual:6.1f} | {piecewise_pred[i]:9.1f} | {sigmoid_pred[i]:7.1f} | {power_pred[i]:5.1f} | {simple_pred[i]:6.1f}"
    )
