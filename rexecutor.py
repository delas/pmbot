import subprocess
import tempfile


def run_r_code(r_script, filename, log):
    new_file, tmp_filename = tempfile.mkstemp(suffix="png")
    subprocess.run([r_script,
                    filename,
                    log,
                    tmp_filename])
    return tmp_filename
