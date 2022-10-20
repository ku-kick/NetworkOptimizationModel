TEST = test_linsmat.py test_linsolv_planner.py test_sim.py test_ushakov.py test_cli.py

clean:
	- find ./test -name "*.csv" -type f | xargs rm
	rm -rf out

test%.py:
	echo $@
	. ./venv/bin/activate && cd test && python3 $@

test: $(TEST)

.PHONY: test
