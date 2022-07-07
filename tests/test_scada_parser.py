#!/usr/bin/env python3
# import pytest
import logging
import app.dlr_import_amps
import os
from datetime import datetime

log = logging.getLogger(__name__)


# Test of parsing CSV-file
def test_parsefile(tmpdir, caplog):
    caplog.set_level(logging.DEBUG)

    # Create a test-file to send to the parsefile function
    file_path = os.path.join(tmpdir.mkdir('data').strpath, "input.csv")
    with open(file_path, "w") as file:
        for i in range(1, 5):
            file.write(",".join([str(i)*16, str(i*11.1111).rjust(21), "0", "\n"]))

    log.debug(f"Created test.file '{file_path}'")

    # Test the output of the function
    timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
    test_json = app.dlr_import_amps.load_dlr_file(file_path)

    assert len(test_json) == 4

    for i, item in enumerate(test_json):
        assert item['MRID'] == str(i+1)*16
        assert item['Value'] == (i+1)*11.1111
        assert item['Quality'] == "0"
        assert item['Time'] == timestamp

        log.debug(f"Validated row: {item}")
