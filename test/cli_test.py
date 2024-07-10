import time

from click.testing import CliRunner

from rohe.rohe_cli.__main__ import rohe_cli


def test_cli_runtime():
    runner = CliRunner()
    start_time = time.time()
    result = runner.invoke(rohe_cli)
    end_time = time.time()
    execution_time = end_time - start_time
    assert (
        execution_time < 0.001
    ), f"Execution time is too long: {execution_time:.4f} seconds"
    assert result.exit_code == 0
