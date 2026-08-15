.PHONY: check package verify

check:
	python3 -B package/check-runtime-preservation.py
	python3 -B tests/test_inventory_mapping.py
	python3 -B package/check-generation.py
	python3 -B package/check-installation.py \
		magicrampage/extractor.json \
		magicrampage/nxport.json \
		magicrampage/INSTALLATION.md \
		nxrelease.json

package:
	package/build-package.sh

verify:
	package/test-final-zip.sh dist/v1.1.3/magicrampage.zip
