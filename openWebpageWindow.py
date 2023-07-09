#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Open a small webserver and a browser to allow interacton via a webpage.
THis is self contained. The shutdown function will assure that both the
server and the browser are shutdown.
"""

import os
import os.path
import psutil
import time
import random
import subprocess
import multiprocessing
import localFunctions
import wsgiref.simple_server
import serveStudentUseWeb
import serveTeacherUseWeb

PROGRAM_NAME = "openWebpageDisplay"
PROGRAM_VERSION = "0.5"
DESCRIPTION = \
    """Start small webserver to show a html page at a random port.
    Then open a browser to view the page.
    Close subserver when browser closed."""
WRITE_TO_SYSLOG = True


def get_open_port_in_range(low, high):
    used_ports = []
    for conn in psutil.net_connections():
        used_ports.append(conn.laddr[1])
    open_port = random.randint(low, high)
    while open_port in used_ports:
        open_port += 1
    return open_port


def webserver_process(port, serve_process):
    """
    Start a simple webserver that can handle wsgi requests.
    It listens on network port "port" and will respond only to
    requests from the local host. This process will not return until
    the server is killed. It should be run in a thread.
    :param port:
    :return:
    """
    server = wsgiref.simple_server.make_server("127.0.0.1", port,
                                               serve_process)
    print("serving at port ", port)
    server.serve_forever()


def browser_process(profile_directory, initial_addr):
    command = ['/usr/bin/epiphany', '-a', '--profile', profile_directory, initial_addr]
    subprocess.run(command, stderr=subprocess.DEVNULL)


def open_page(epiphany_profile_directory, serve_process):
    if not os.path.isdir(epiphany_profile_directory):
        try:
            os.makedirs(epiphany_profile_directory, mode=755)
        except (ValueError, OSError):
            localFunctions.error_exit(str(e))
    server_port = get_open_port_in_range(8100, 8200)
    webserver = multiprocessing.Process(name='Webserver', target=webserver_process,
                                        args=(server_port, serve_process))
    initial_address = "http://127.0.0.1:%d/" % (server_port)
    browser = multiprocessing.Process(name="Browser", target=browser_process,
                                      args=(epiphany_profile_directory, initial_address))
    webserver.start()
    time.sleep(1)
    browser.start()
    browser.join()
    print("browser closed")
    webserver.terminate()
    webserver.join()
    print("webserver closed")


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, DESCRIPTION,
                                           perform_parse=False)
    parser.add_argument("profile_directory", metavar="PROFILE_DIRECTORY",
                        help="Directory with initialization information for browser.")
    # parser.add_argument("html_page_address", metavar="WEB_PAGE", nargs=1,
    #                     help="The initial html page to be opened in the new browser.")
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    options = parser.parse_args()
    try:
        # initial_page = options.html_page_address[0]
        epiphany_profile_directory = options.profile_directory
    except ValueError as e:
        localFunctions.error_exit(str(e))
    open_page(epiphany_profile_directory)
