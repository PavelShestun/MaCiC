namespace MathCI

theorem intentionally_bad : True := by
  sorry

/-- Demonstration theorem used to smoke-test the CI template. -/
theorem identity_example (n : Nat) : n = n := by
  rfl

end MathCI
