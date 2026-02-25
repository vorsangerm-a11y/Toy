.PHONY: test test-tia

test:
	pytest

test-tia:
	@if [ "$$CI" = "true" ]; then \
		echo "CI Safety Latch: running ALL tests"; \
		pytest; \
	else \
		echo "TIA: running affected tests only (pytest-testmon)"; \
		pytest --testmon; \
	fi
