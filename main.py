import unicodedata
import sys
# reload(sys)
# sys.setdefaultencoding('utf-8')

# import io
import argparse
import Xlib
from Xlib import display, X, protocol

# for s in ("stdin","stdout","stderr"):
#     setattr(sys, s, io.TextIOWrapper(getattr(sys, s).detach(), encoding="utf8"))

disp = Xlib.display.Display()
root = disp.screen().root
win_id = None

NET_CLIENT_LIST = disp.intern_atom('_NET_CLIENT_LIST')
NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
NET_WM_NAME = disp.intern_atom('_NET_WM_NAME') # UTF-8
WM_NAME = disp.intern_atom('WM_NAME') # Legacy encoding

NET_WM_STATE = disp.intern_atom('_NET_WM_STATE')
NET_WM_STATE_ABOVE = disp.intern_atom('_NET_WM_STATE_ABOVE')
NET_WM_STATE_BELOW = disp.intern_atom('_NET_WM_STATE_BELOW')
NET_WM_STATE_SKIP_TASKBAR = disp.intern_atom('_NET_WM_STATE_SKIP_TASKBAR')
NET_WM_STATE_MODAL = disp.intern_atom('_NET_WM_STATE_MODAL')
NET_WM_STATE_STICKY = disp.intern_atom('_NET_WM_STATE_STICKY')

def get_window_name(win_obj):
    """Simplify dealing with _NET_WM_NAME (UTF-8) vs. WM_NAME (legacy)"""
    for atom in (NET_WM_NAME, WM_NAME):
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

def get_window_by_name(name):
    winid_list = root.get_full_property(NET_CLIENT_LIST, Xlib.X.AnyPropertyType).value
    for winid in winid_list:
        win = disp.create_resource_object('window', winid)
        wmname = get_window_name(win)
        if wmname != None and name == wmname:
            return win
    return None

last_seen = {'xid': None}
def get_active_window():
    window_id = root.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]

    focus_changed = (window_id != last_seen['xid'])
    last_seen['xid'] = window_id

    return window_id, focus_changed

# def get_window_name(window_id):
#     try:
#         window_obj = disp.create_resource_object('window', window_id)
#         window_name = window_obj.get_full_property(NET_WM_NAME, 0).value
#     except Xlib.error.XError:
#         window_name = None

#     return window_name

def handle_xevent(event, target_win_id):
    # Loop through, ignoring events until we're notified of focus/title change
    if event.type != Xlib.X.PropertyNotify:
        return

    if event.atom == NET_ACTIVE_WINDOW:
        win_id = root.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]
        if win_id != target_win_id:
            print("lost focus")

def parse_args():
    global args
    parser = argparse.ArgumentParser(description='Toggle window')
    parser.add_argument('-n', '--name', required=True, help='Name of window to operate on')
    parser.add_argument('-s', '--sticky', action='store_true', help='Make window sticky')
    parser.add_argument('-i', '--info', action='store_true', help='Print info on window operating on')
    parser.set_defaults(sticky=False, info=False)
    args = parser.parse_args()

def set_property(client_type, data, win=None, mask=None):
    """
    Send a ClientMessage event to the root window
    """
    if not win:
        win = root
    if type(data) is str:
        dataSize = 8
    else:
        data = (data+[0]*(5-len(data)))[:5]
        dataSize = 32

    ev = protocol.event.ClientMessage(window=win, client_type=client_type, data=(dataSize, data))

    if not mask:
        mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    root.send_event(ev, event_mask=mask)

if __name__ == '__main__':
    parse_args()
    win = get_window_by_name(args.name)
    if win == None:
        print('Unable to find window')
        sys.exit(1)

    if args.info:
        print(win)
        sys.exit(0)
    else:
        win_id = win.id
        root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
        # win.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
        set_property(NET_WM_STATE, [0, NET_WM_STATE_BELOW, 0, 1], win)
        set_property(NET_WM_STATE, [1, NET_WM_STATE_MODAL, NET_WM_STATE_ABOVE, 1], win)
        while True:
            handle_xevent(disp.next_event(), win.id)

    root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
    while True:
        win, changed = get_active_window()
        if changed:
            print(get_window_name(win))

        while True:
            event = disp.next_event()
            if (event.type == Xlib.X.PropertyNotify and event.atom == NET_ACTIVE_WINDOW):
                break

