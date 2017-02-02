import os
import errno
import shutil
import unicodedata
import sys
import argparse
import tempfile
import getpass
import hashlib
import Xlib
from Xlib import display, X, protocol

class ToggleChat:
    disp = Xlib.display.Display()
    root = disp.screen().root

    def __init__(self):
        self.target_window = None
        self.created_socket_dir = False
        self.parse_args()

    def run(self):
        self.target_window = self.get_window_by_name(self.options.name)
        if self.target_window == None:
            print('Unable to find window')
            sys.exit(1)

        if self.options.info:
            print("file: {}".format(self.options.file))
            print(self.target_window)
            pid = self.target_window.get_full_property(self.NET_WM_PID, X.AnyPropertyType).value[0]
            print(pid)
            self._create_socket_dir()
            self._cleanup()
            sys.exit(0)
        else:
            self.root.change_attributes(event_mask=X.PropertyChangeMask)
            # win.change_attributes(event_mask=X.PropertyChangeMask)
            self.set_property(self.NET_WM_STATE, [0, self.NET_WM_STATE_BELOW, self.NET_WM_ACTION_MINIMIZE, 1], self.target_window)
            self.set_property(self.NET_WM_STATE, [1, self.NET_WM_STATE_MODAL, self.NET_WM_STATE_ABOVE, 1], self.target_window)
            while True:
                self.handle_xevent(self.disp.next_event())

    def handle_xevent(self, event):
        # Loop through, ignoring events until we're notified of focus/title change
        if event.type != X.PropertyNotify:
            return

        if event.atom == self.NET_ACTIVE_WINDOW:
            id = self.root.get_full_property(self.NET_ACTIVE_WINDOW, X.AnyPropertyType).value[0]
            if id != self.target_window.id:
                print("lost focus")

    def get_window_by_name(self, name):
        for id in self.root.get_full_property(self.NET_CLIENT_LIST, X.AnyPropertyType).value:
            win = self.disp.create_resource_object('window', id)
            wmname = self.get_window_name(win)
            if wmname != None and name == wmname:
                return win
        return None

    def get_window_name(self, win_obj):
        """Simplify dealing with _NET_WM_NAME (UTF-8) vs. WM_NAME (legacy)"""
        for atom in (self.NET_WM_NAME, self.WM_NAME):
            try:
                window_name = win_obj.get_full_property(atom, 0)
            except UnicodeDecodeError:  # Apparently a Debian distro package bug
                title = "<could not decode characters>"
            else:
                if window_name:
                    win_name = window_name.value
                    if isinstance(win_name, bytes):
                        # Apparently COMPOUND_TEXT is so arcane that this is how
                        # tools like xprop deal with receiving it these days
                        win_name = win_name.decode('iso-8859-1', 'replace').encode('iso-8859-1')
                        # win_name = win_name.decode('utf8', 'replace').encode('utf8')
                    return win_name
                else:
                    title = "<unnamed window>"

        return "{} (XID: {})".format(title, win_obj.id)

    def set_property(self, client_type, data, win=None, mask=None):
        """
        Send a ClientMessage event to the root window
        """
        if not win:
            win = self.root
        if type(data) is str:
            dataSize = 8
        else:
            data = (data+[0]*(5-len(data)))[:5]
            dataSize = 32

        ev = protocol.event.ClientMessage(window=win, client_type=client_type, data=(dataSize, data))

        if not mask:
            mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.root.send_event(ev, event_mask=mask)

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Toggle window', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('name', help='Name of window to operate on')
        parser.add_argument('-s', '--sticky', action='store_true', help='Make window sticky')
        parser.add_argument('-f', '--file', help='Path to unix socket file to create')
        parser.add_argument('-i', '--info', action='store_true', help='Print info on window operating on')
        parser.set_defaults(sticky=False, info=False, file=self._get_socket_file())
        self.options = parser.parse_args()

    def _create_socket_dir(self):
        try:
            os.makedirs(os.path.dirname(self.options.file), 0700)
            self.created_socket_dir = True
        except OSError as e:
            if e.errno != errno.EEXIST: raise

    def _get_socket_file(self):
        return os.path.join(tempfile.gettempdir(), hashlib.md5(getpass.getuser() + '-' + os.path.realpath(__file__)).hexdigest() + '.toggle_chat', 'socket')

    def _cleanup(self):
        if self.created_socket_dir:
            shutil.rmtree(os.path.dirname(self.options.file))

    # Define a bunch of atoms for usage
    NET_CLIENT_LIST = disp.intern_atom('_NET_CLIENT_LIST')
    NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
    NET_WM_NAME = disp.intern_atom('_NET_WM_NAME') # UTF-8
    WM_NAME = disp.intern_atom('WM_NAME') # Legacy encoding
    NET_WM_PID = disp.intern_atom('_NET_WM_PID')

    NET_WM_STATE = disp.intern_atom('_NET_WM_STATE')
    NET_WM_ACTION_MINIMIZE = disp.intern_atom('_NET_WM_ACTION_MINIMIZE')
    NET_WM_STATE_ABOVE = disp.intern_atom('_NET_WM_STATE_ABOVE')
    NET_WM_STATE_BELOW = disp.intern_atom('_NET_WM_STATE_BELOW')
    NET_WM_STATE_SKIP_TASKBAR = disp.intern_atom('_NET_WM_STATE_SKIP_TASKBAR')
    NET_WM_STATE_MODAL = disp.intern_atom('_NET_WM_STATE_MODAL')
    NET_WM_STATE_STICKY = disp.intern_atom('_NET_WM_STATE_STICKY')

if __name__ == '__main__':
    ToggleChat().run()
