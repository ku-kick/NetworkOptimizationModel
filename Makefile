
clean:
	git checkout -- *csv
	rm -rf out

test:
	. ./venv/bin/activate && echo test/*py | xargs -n 1 python3

.PHONY: test
