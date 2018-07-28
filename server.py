# Python standard libraries
import os
from json import dumps

# Library modules
from utils import setup_logging, load_config

# 3rd party modules
from fasteners import process_lock
from bottle import get, post, run, request
import dice

VERSION = (0, 0, 1)
VIEWS_DIR = os.path.join(os.path.dirname(__file__), 'views')
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')


def str_to_bool(s):
    """
    If the input string starts with t, y, or 1 (case-insensitive), it returns True. Else, False.

    :param s: String to process into a boolean
    :return:
    :rtype: bool
    """
    if s and str(s).lower()[0] in ['t', 'y', '1']:
        return True
    return False


class Server:
    """
    On load:
     - Check if any other server instances are running, fail if so.
     - Establish logging to the server.log file. Redirect stderr to this log file, to catch the output thrown
       by the Bottle server.
     - Spin up a VehicleSim instance.
     - Load the WSGI functions.
     - Start the Bottle server.
    """

    server_thread = None
    interval = None

    def __init__(self, host=None, port=None, log_level=None, run_as_thread=None):
        global logger

        self._get_process_lock()

        cfg = load_config()
        logger = setup_logging("log", log_level=log_level)

        self._load_wsgi_functions()
        self._init_server(
            host=cfg.get("Settings", "host") if host is None else host,
            port=cfg.getint("Settings", "port") if port is None else port,
            run_as_thread=cfg.getboolean("Settings", "run as thread") if run_as_thread is None else run_as_thread
        )

    def _get_process_lock(self):
        lock = process_lock.InterProcessLock("server.lock")
        if not lock.acquire(blocking=False):
            raise ChildProcessError("Server process is already running")

    def _init_server(self, host=None, port=None, run_as_thread=None):
        if run_as_thread:
            from threading import Thread
            self.server_thread = Thread(name="SecretTunnelServer", target=self._run_server, args=[host, port],
                                        daemon=True)
            self.server_thread.start()
            print("Server thread started.")
        else:
            self._run_server(host, port)

    def _run_server(self, host, port):
        run(host=host, port=port)
        print("Server instance is ending.")

    def _load_wsgi_functions(self):
        """
        Loads functions into the WSGI
        """
        @get('/')
        @get('/help')
        def index_help():
            return "This is some help. Try /roll <dice string>"

        @post('/roll')
        def roll():
            dice_text = request.forms.get("text")
            print(dict(request.forms))
            print(dict(request.cookies))
            print(dict(request.headers))
            try:
                roll_result = dice.roll(dice_text)
                response = "/roll {} = *{}*".format(dice_text, roll_result)
            except dice.exceptions.DiceException as e:
                print(repr(dice_text))
                print(e)
                response = "I didn't understand your dice string ({!r}). ".format(dice_text) + \
                           "Please see https://github.com/borntyping/python-dice for dice string options."

            return {
                "response_type": "in_channel",
                "text": response
            }


if __name__ == "__main__":
    Server()
