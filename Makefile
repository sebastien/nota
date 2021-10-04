PATH_LOCAL_PY=$(firstword $(shell python -c "import sys,pathlib;sys.stdout.write(' '.join([_ for _ in sys.path if _.startswith(str(pathlib.Path.home()))] ))"))
PATH_LOCAL_BIN=~/.local/bin

try-install:
	ln -sfr bin/nota $(PATH_LOCAL_BIN)/nota
	if [ -s "$(PATH_LOCAL_PY)" ]; then ln -sfr src/py/nota "$(PATH_LOCAL_PY)"/nota; fi

try-uninstall:
	unlink $(PATH_LOCAL_BIN)/nota; true
	if [ -s "$(PATH_LOCAL_PY)" ]; then unlink src/py/nota "$(PATH_LOCAL_PY)"/nota; true; fi
