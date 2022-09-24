
clean:
	- find ./test -name "*.csv" -type f | xargs rm
	rm -rf out
