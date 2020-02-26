import serial
import time
from threading import Thread

from config.params import params_t


def trigger_factory():
    if params_t.trigger_type == 'GPIO':
        return TriggerGPIO()
    elif params_t.trigger_type == 'Arduino':
        return TriggerArduino()
    else:
        raise  NotImplementedError


""" Trigger base class. """
class Trigger(object):
    def __init__(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError

    def set_fps(self, fps):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def end(self):
        raise NotImplementedError


class TriggerGPIO(Trigger):
    def __init__(self):
        self.device = None
        self.device = serial.Serial(params_t.gpio_path, timeout=1)
        self._fps = params_t.fps

        self._gpio_delay = 1  # rough delay this module has in ms
        self._gpio_pin_id = 0

        self._clear_gpio(self._gpio_pin_id)  # default state is low

        # intialize thread
        self.thread = Thread(target=self.trigger_loop, args=())
        self.thread.daemon = True

    def __del__(self):
        if self.device is not None:
            self.device.close()

    def ping(self):
        self.device.write(b'ver\r')
        time.sleep(0.1)
        s = self.device.read(100)
        print('pong=', self._pretty_str(s))

    def set_fps(self, fps):
        fps = float(fps)
        if fps < params_t.min_fps or fps > params_t.max_fps:
            print('Invalid fps value', fps)
            return

        self._fps = fps

    def start(self):
        time.sleep(params_t.trigger_delay)
        self.thread.start()

    def trigger_loop(self):
        self._stop = False
        while not self._stop:
            start = time.time()
            self._set_gpio(self._gpio_pin_id)
            while (time.time() - start)*1000.0 < 500.0/self._fps - self._gpio_delay:
                time.sleep(0.001)
            self._clear_gpio(self._gpio_pin_id)
            while (time.time() - start)*1000.0 < 1000.0/self._fps - self._gpio_delay:
                time.sleep(0.001)

    def end(self):
        self._stop = True
        self.thread.join()

    def _set_gpio(self, gpio_id):
        self.device.write(b'gpio set %d\r' % gpio_id)

    def _clear_gpio(self, gpio_id):
        self.device.write(b'gpio clear %d\r' % gpio_id)

    def _pretty_str(self, s):
        s = s.decode('utf-8')
        s = s.replace('\n', '')
        s = s.replace('\r', '')
        s = s.replace('>', '')
        return s


class TriggerArduino(Trigger):
    def __init__(self):
        self.device = None
        self.device = serial.Serial(params_t.gpio_path, timeout=1)
        self._fps = params_t.fps

        # arduino commands
        self._ping_cmd = b'P\r'
        self._start_cmd = b'S%d\r'
        self._stop_cmd = b'Q\r'
        self._send_string_cmd =b'T%s\r'
        
    def __del__(self):
        if self.device is not None:
            self.device.close()

    def ping(self):
        self.device.write(self._ping_cmd)
        time.sleep(0.1)
        s = self.device.read(100)
        print('pong=', self._pretty_str(s))

    def set_fps(self, fps):
        fps = float(fps)
        if fps < params_t.min_fps or fps >= params_t.max_fps:
            print('Invalid fps value', fps)
            return

        self._fps = fps

    def start(self):
        self.device.write(self._start_cmd % self._fps)
        
    def send_string(self,string2send):
        self.device.write(self._send_string_cmd % string2send.encode('utf-8'))

    def end(self):
        self.device.write(self._stop_cmd)

    def _pretty_str(self, s):
        s = s.decode('utf-8')
        s = s.replace('\n', '')
        s = s.replace('\r', '')
        s = s.replace('>', '')
        return s


if __name__ == '__main__':
    # mod = TriggerGPIO()
    # mod.ping()
    # mod.set_fps(2.0)
    # mod.start()
    # time.sleep(10.0)
    # mod.end()

    # TODO: make this work with Arduino
    mod = TriggerArduino()
    mod.ping()
    mod.set_fps(2.0)
    mod.start()
    time.sleep(10.0)
    mod.end()


