PROJECT:=$(notdir $(abspath .))
SOURCES_BIN:=$(wildcard bin/*)
PYTHON_MODULES=$(patsubst src/py/%,%,$(wildcard src/py/*))
SOURCES_PY:=$(wildcard src/py/*.py src/py/*/*.py src/py/*/*/*.py src/py/*/*/*/*.py)

PATH_LOCAL_PY=$(firstword $(shell python -c "import sys,pathlib;sys.stdout.write(' '.join([_ for _ in sys.path if _.startswith(str(pathlib.Path.home()))] ))"))
PATH_LOCAL_BIN=~/.local/bin

install:
	@for file in $(SOURCES_BIN); do
		ln -sfr $$file $(PATH_LOCAL_BIN)/$$(basename $$file)
		echo "Installed $(PATH_LOCAL_BIN)/$$(basename $$file)"
	done
	if [ -s "$(PATH_LOCAL_PY)" ]; then
		for module in $(PYTHON_MODULES); do
			ln -sfr src/py/$$module "$(PATH_LOCAL_PY)"/$$module
			echo "Installed module $(PATH_LOCAL_PY)/$$module"
		done
	fi


uninstall:
	@for file in $(SOURCES_BIN); do
		unlink $(PATH_LOCAL_BIN)/$$(basename $$file)
		echo "Uninstalled $(PATH_LOCAL_BIN)/$$(basename $$file)"
	done
	if [ -s "$(PATH_LOCAL_PY)" ]; then
		for module in $(PYTHON_MODULES); do
			unlink "$(PATH_LOCAL_PY)"/$$module
			echo "Uninstalled module $(PATH_LOCAL_PY)/$$module"
		done
	fi

audit:
	bandit -s B101 -r src/py


print-%:
	@echo "$*="
	@for FILE in $($*); do echo $$FILE; done

.ONESHELL:

# EOF
