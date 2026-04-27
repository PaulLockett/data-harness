.PHONY: help smoke check-all-skills caps models models-small models-clear
.DEFAULT_GOAL := help

help:
	@echo "data-harness make targets:"
	@echo "  make smoke              one-liner sanity check (glance(load(...)))"
	@echo "  make check-all-skills   run dh check-skill against every fixture"
	@echo "  make caps               print Capabilities snapshot"
	@echo "  make models             pull all model weights declared by retained-weights.toml"
	@echo "  make models-small       pull only the small/embedder weights"
	@echo "  make models-clear       drop all locally-cached model weights"

smoke:
	@uv run --no-sync python -c "from helpers import glance, load; print(glance(load('/etc/hosts')))"

check-all-skills:
	@for skill in interaction-skills/*/ domain-skills/*/; do \
	  if [ -d "$$skill/fixtures" ]; then \
	    echo "==> $$skill" ; \
	    uv run --no-sync python run.py check-skill "$$skill" || exit 1 ; \
	  fi ; \
	done

caps:
	@uv run --no-sync python run.py caps

models:
	@uv run --no-sync python run.py models pull

models-small:
	@uv run --no-sync python run.py models pull --small

models-clear:
	@uv run --no-sync python run.py models clear
