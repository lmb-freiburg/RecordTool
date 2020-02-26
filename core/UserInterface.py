from core.Recorder import Recorder

class UserInterface(object):
    def __init__(self, verbosity=0):
        self._commands = list()
        # this is always hotkey, description, function handle
        self._commands.append(('h', 'help', self._show_commands))
        self._commands.append(('f', 'set fps', self._set_fps))
        self._commands.append(('t', 'set take name', self._set_takename))
        self._commands.append(('l', 'list cams', self._list_cams))
        self._commands.append(('s', 'show single cam', self._show_cam))
        self._commands.append(('r', 'record cams', self._record_cams))
        self._commands.append(('w', 'white balance cameras', self._white_balance))
        self._commands.append(('g', 'auto gain', self._auto_gain))
        self._commands.append(('e', 'auto exposure', self._auto_exposure))
        self._commands.append(('d', 'default values gain/exposure', self._fix_gain_exposure))
        self._commands.append(('x', 'quit', exit))        
        self._commands.append(('k', 'calibrate cams', self._record_cams_delayed))

        self.recorder = Recorder(verbosity)

    def _print_splash(self):
        print('-------RECORDING TOOL---------')
        self._show_commands()
        print('------------------------------')

    def _show_commands(self):
        print('>AVAILABLE COMMANDS')
        for k, txt, _ in self._commands:
            print('  > key "%s": %s' % (k, txt))

    def _list_cams(self):
        self.recorder.get_cam_info()

    def _show_cam(self):
        cid = input('>Camid=')
        while type(cid) is not int:
            try:
                cid = int(cid)
            except ValueError: #catch typos                
                cid = input('!Should be an int!>Camid=')        
        self.recorder.run_single_cam_show(cid)

    def _set_fps(self):
        fps = input('>FPS=')
        while type(fps) is not float:
            try:
                fps = float(fps)
            except ValueError: #catch typos
                fps = input('!Should be a number!>FPS=')
        self.recorder.fps = fps
        print('Actual fps:', self.recorder.fps)

    def _set_takename(self):
        take_name = input('>Takename=')
        take_name = str(take_name)
        self.recorder._take_name = take_name

    def _record_cams(self):
        self.recorder.run_record_cams()
        
    def _record_cams_delayed(self):
        print('Calibration-waiting 20 sec..')
        import time
        time.sleep(20)
        self.recorder.run_record_cams()

    def _white_balance(self):
        self.recorder.run_white_balance()

    def _auto_gain(self):
        self.recorder.run_auto_gain()

    def _auto_exposure(self):
        self.recorder.run_auto_exposure()

    def _fix_gain_exposure(self):
        self.recorder.set_gain_exposure()

    def _check_cmd(self, cmd):
        """ Checks if a cmd exists and returns the respective function handle. """
        keys = [x[0] for x in self._commands]
        fcts = [x[2] for x in self._commands]

        if cmd in keys:
            return fcts[keys.index(cmd)]
        return None

    def run(self):
        self._print_splash()

        while True:
            cmd = input('>')
            cmd_fct = self._check_cmd(cmd)

            if cmd_fct is None:
                continue
            else:
                cmd_fct()
