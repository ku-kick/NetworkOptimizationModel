PYTHON = python3

clean:
	git checkout -- *csv
	rm -rf out

venv:
	$(PYTHON) -m venv ./venv

test: venv
	. ./venv/bin/activate \
		&& find ./test -type f -name '*.py' \
		| grep 'test' \
		| xargs -n 1 $(PYTHON)

.PHONY: test
