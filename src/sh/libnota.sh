# --
# Nota bash library

if [ -z "$NOTA_HOME" ]; then
	NOTA_HOME=$HOME/.nota
fi

function nota-init {
	if [ ! -e "$NOTA_HOME" ]; then
		mkdir -p "$NOTA_HOME"
	fi
	if [ ! -e "$NOTA_HOME/.git" ]; then
		env -C "$NOTA_HOME" git init
	fi
}

function nota-edit {
	nota-init
	local query="$1"
	$EDITOR "$(find "$NOTA_HOME" -name "*.?d" | fzf --query="$query" --select-1 --exit-0)"
	nota-commit
}


function nota-sync {
	nota-commit
	git -C "$NOTA_HOME" pull
	git -C "$NOTA_HOME" push
}

function nota-list {
	env -C "$NOTA_HOME" find . -name "*.?d" | cut -b3- | sort
}

function nota-commit {
	nota-init
	local changed=$(git -C "$NOTA_HOME" status --short | cut -b4-)
	git -C "$NOTA_HOME" add $changed
	git -C "$NOTA_HOME" commit -a -m "[Edited] $USER: $changed"
	git -C "$NOTA_HOME" push
}

# EOF
