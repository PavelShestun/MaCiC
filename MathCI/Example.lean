namespace MathCI

/-- Demonstration theorem used to smoke-test the CI template. -/
theorem identity_example (n : Nat) : n = n := by
  rfl

axiom Magic : False

theorem bad_axiom : False :=
  Magic

end MathCI
