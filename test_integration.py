import os
import subprocess
import time
import pytest

@pytest.fixture(scope="module")
def running_server():
    """
    A pytest fixture that starts the Butterfly server for the duration of the tests.
    """
    # Set environment variables needed for the server and tests
    os.environ['BUTTERFLY_ENCRYPTION_KEY'] = "test-key-for-ci-coverage-report-generation"
    os.environ['JWT_SECRET_KEY'] = "ci-test-secret-key"

    # Run the first-time setup wizard non-interactively
    setup_process = subprocess.run("printf 'y\\n1\\ny\\nadmin-app\\n' | python app.py", shell=True, capture_output=True)
    assert setup_process.returncode == 0, "Setup wizard failed to run."

    # Start the server in the background
    server_process = subprocess.Popen(["python", "app.py"])

    # Wait for the server to initialize
    time.sleep(15)

    yield  # This is where the tests will run

    # Teardown: stop the server after tests are done
    server_process.terminate()

def test_health_check(running_server):
    """Runs the health_check.py script and asserts that it passes."""
    result = subprocess.run(["python", "health_check.py"], capture_output=True, text=True)
    print(result.stdout) # Print output for easier debugging in CI
    print(result.stderr)
    assert result.returncode == 0, "Health check script failed."