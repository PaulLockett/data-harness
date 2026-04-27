.PHONY: smoke check-all-skills caps models models-small models-clear

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
