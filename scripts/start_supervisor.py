import os
import subprocess

from supervisor.supervisord import main as supervisor_main


def main():
    # manage_py = os.path.abspath(os.path.join(os.path.realpath( __file__ ), '..','manage.py'))
    print("my name is vatsa")
    # os.system(' ../Python/python ../pkgs/manage.py runserver ')
    subprocess.check_call(["../Python/python", "../pkgs/manage.py", "makemigrations"])
    subprocess.check_call(["../Python/python", "../pkgs/manage.py", "migrate"])
    # subprocess.check_call(["../Python/python", "../pkgs/manage.py", "runserver"])
    einvoicing_file = os.path.abspath(os.path.join(os.path.realpath(__file__), "..", r"einvoicing\supervisord.conf"))
    subprocess.check_call(supervisor_main(["-c", einvoicing_file]))
    # supervisor_main((["-c", r"C:\\Users\\Srivatsa B\\Deployment\\gst-comply\\projects\\einvoicing-local-UI\\build\\nsis\\pkgs\\einvoicing\\supervisord.conf"]))


main()
