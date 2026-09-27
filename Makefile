.PHONY: install test validate workflow-audit agent-manifest lean audit deps-exact env-lock smoke-ci acceptance demo packet
install:
	python -m pip install -e '.[dev]'
test:
	pytest -q
validate:
	researchctl validate
workflow-audit:
	researchctl workflow-audit
agent-manifest:
	researchctl agent-manifest
lean:
	lake --no-ansi build
audit:
	researchctl audit H-0001
deps-exact:
	researchctl deps-exact-all
env-lock:
	researchctl env-lock
smoke-ci:
	scripts/smoke_ci.sh
acceptance:
	researchctl acceptance
demo:
	researchctl status H-0001
packet:
	researchctl packet H-0001
