import subprocess

def run_apt_get(command):
    """Runs an apt-get command and returns the output."""

    try:
        result = subprocess.run(
            ["sudo", "apt-get", *command.split()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return result.stdout.decode()
    except subprocess.CalledProcessError as e:
        print("Error:", e.stderr.decode())
