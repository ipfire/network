#!/bin/bash

decompress() {
	local file=${1}

	[ -e "${file}" ] || return

	cpio --quiet --extract --to-stdout data.img < ${file} \
		| tar xvvJ -C /
}

action=${1}
shift

case "${action}" in
	localinstall)
		for file in $@; do
			decompress ${file}
		done
		;;
	*)
		echo
		echo "This is only a very light version to install"
		echo "packages easyly."
		echo "Run: ${0} localinstall <file>.ipk [<file>.ipk ...]"
		echo
		;;
esac
