import os
import cv2
import time
import datetime
import numpy as np
from collections import defaultdict

from pypylon import genicam
from pypylon import pylon

from core.Trigger import trigger_factory

from utils.general_util import my_mkdir
from utils.VideoWriterFast import VideoWriterFast
from utils.StitchedImage import StitchedImage

from config.params import params_t
from config.camera_infos import get_camera_infos


# Another way to get warnings when images are missing ... not used
class MyImageEventHandler(pylon.ImageEventHandler):
    def OnImagesSkipped(self, camera, countOfSkippedImages):
        print("EVENT: OnImagesSkipped", countOfSkippedImages)

def zeros():
    return 0.0

def rel_close(v, max_v, thresh=5.0):
    v_scaled = v / max_v * 100.0
    if 100.0 - v_scaled < thresh:
        return True
    return False


class Recorder(object):
    def __init__(self, verbosity=0):
        self._verbosity = verbosity

        self._camera_info = get_camera_infos()
        self._camera_list = list()
        self._camera_names_list = list()

        self._take_name = 'take'
        self._rid = 0
        self.fps = params_t.fps
        self._trigger = None

    @property
    def fps(self):
        return self.__fps

    @fps.setter
    def fps(self, fps_new):
        if fps_new < params_t.min_fps:
            self.__fps = params_t.min_fps
        elif fps_new > params_t.max_fps:
            self.__fps = params_t.max_fps
        else:
            self.__fps = fps_new

    def get_cam_info(self):
        self._setup_cams()

        print('Connected cameras:')
        print('DevId \tGiven Name \tSerial Number')
        for idx, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):
            print('%d \t%s \t\t%s' % (idx, cam_name, cam.GetDeviceInfo().GetSerialNumber()))

    def run_single_cam_show(self, cid):
        self._setup_cams()
        cam_name = 'cam%d' % cid
        print('Showing device "%s" with %.1f FPS' % (cam_name, self.fps))

        if cam_name not in self._camera_names_list:
            print('Camera with given name "%s" not found. Only found these cameras:' % cam_name, self._camera_names_list)
            return
        ind = self._camera_names_list.index(cam_name)
        self._config_cams_continuous(self._camera_list[ind])
        self._camera_list[ind].StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        k = None
        while not k == ord('q'):
            try:
                grabResult = self._camera_list[ind].RetrieveResult(params_t.cam_timeout, pylon.TimeoutHandling_ThrowException)
                img = grabResult.GetArray()
                if len(img.shape) == 2:
                    img = np.stack([img]*3, -1)

                cv2.imshow(cam_name, img)
                k = cv2.waitKey(10)

            except genicam.TimeoutException as e:
                print(e)
                print('Timeout happened. Giving up')
                break

        self._camera_list[ind].Close()
        cv2.destroyAllWindows()

    def run_record_cams(self):
        self._setup_cams()
        print('Start recording with hardware trigger at %.1f FPS. (press "q" to stop recording)' % self.fps)

        video_path_template = self._init_recording()
        self._init_trigger()

        # make cameras ready for trigger
        video_writer_list = list()
        for cam_name, cam in zip(self._camera_names_list, self._camera_list):
            self._config_cams_hw_trigger(cam)
            cam.StartGrabbing(pylon.GrabStrategy_LatestImages)
            # cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)  # here you dont have any buffer
            # cam.StartGrabbing(pylon.GrabStrategy_OneByOne)  # here you dont get warnings if something gets skipped
            video_writer_list.append( VideoWriterFast(video_path_template % cam_name,
                                                      fps=self.fps,
                                                      codec=params_t.codec) )

        # start trigger
        self._trigger.start()

        # recording loop
        k = None
        last_show = 0
        num_frames = defaultdict(zeros)
        video_writer_q_state, cam_polling_freq, cam_last_poll = defaultdict(zeros), defaultdict(zeros), defaultdict(zeros)
        while not k == ord('q'):
            try:
                img_list = list()
                for cid, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):
                    grabResult = cam.RetrieveResult(params_t.cam_timeout, pylon.TimeoutHandling_ThrowException)

                    if params_t.warn_frame_missing:
                        if grabResult.GetNumberOfSkippedImages() > 0:
                            print('WARNING: Missed %d frames' % grabResult.GetNumberOfSkippedImages())

                    img = grabResult.GetArray()

                    if len(img.shape) == 2:
                        img = np.stack([img]*3, -1)

                    if params_t.inpaint_image_id:
                        cv2.putText(img, '%s_%d' % (cam_name, num_frames[cid]),
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # feed image to the writer
                    video_writer_list[cid].feed(img)

                    # keep track of our speed
                    if params_t.print_aquisition_state:
                        video_writer_q_state[cid] = video_writer_list[cid].get_state()
                        if cam_last_poll[cid] > 0:
                            if cam_polling_freq[cid] > 0:
                                cam_polling_freq[cid] = 0.85*cam_polling_freq[cid] + 0.15 * (time.time() - cam_last_poll[cid])
                            else:
                                cam_polling_freq[cid] = time.time() - cam_last_poll[cid]
                        cam_last_poll[cid] = time.time()
                    num_frames[cid] += 1

                    # keep image around for visualization
                    img_list.append(img)

                # show image
                if (time.time() - last_show) > params_t.show_delay and params_t.show_recorded_frames:
                    stitch = StitchedImage(img_list, target_size=params_t.show_size)
                    cv2.imshow('cams', stitch.image)
                    k = cv2.waitKey(1)
                    last_show = time.time()

                # dummy show image (otherwise 'q' key is not readable)
                if not params_t.show_recorded_frames:
                    cv2.imshow('cams', np.ones((25, 25, 3), dtype=np.uint8))
                    k = cv2.waitKey(1)

                # print speed measurements if needed
                if params_t.print_aquisition_state:
                    for cid in range(len(cam_polling_freq)):
                        print('dev%d' % cid, 'Polling freq = %d' % round(1.0/cam_polling_freq[cid]), 'Queue state', video_writer_q_state[cid], end='\t')
                    print('', end='\r')
                    # print('', end='\n')

            except genicam.TimeoutException as e:
                print(e)
                print('Timeout happened. Giving up.')
                break

        if params_t.print_aquisition_state:
            print('')

        # stop trigger
        self._trigger.end()
        del self._trigger
        self._trigger = None

        if self._verbosity > 2:
            for cid, num in num_frames.items():
                print('Device %d recorded %d frames' % (cid, num))

        for cam in self._camera_list:
            cam.Close()

        if self._verbosity > 0:
            print('Waiting for writers to finish ...')
        for writer in video_writer_list:
            writer.wait_to_finish()
            writer.stop()
        cv2.destroyAllWindows()

        self._rid += 1

    def run_white_balance(self):
        self._setup_cams()

        for idx, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):
            cam.Open()

            if not self.is_color_cam(cam):
                print('Not a color cam: %d \t%s \t\t%s' % (idx, cam_name, cam.GetDeviceInfo().GetSerialNumber()))
                print('Skipping white balancing.')
                continue

            cam.AutoFunctionROISelector.SetValue('ROI1')
            cam.AutoFunctionROIUseWhiteBalance.SetValue(False)
            cam.AutoFunctionROISelector.SetValue('ROI2')
            cam.AutoFunctionROIUseWhiteBalance.SetValue(True)

            # define ROI to use
            cam.AutoFunctionROISelector.SetValue('ROI2')
            cam.AutoFunctionROIWidth.SetValue(cam.Width.GetValue())
            cam.AutoFunctionROIHeight.SetValue(cam.Height.GetValue())
            cam.AutoFunctionROIOffsetX.SetValue(0)
            cam.AutoFunctionROIOffsetY.SetValue(0)

            # get initial values
            if self._verbosity > 1:
                print('Initial balance ratio:', end='\t')
                cam.BalanceRatioSelector.SetValue('Red')
                print('Red= ', cam.BalanceRatio.GetValue(), end='\t')
                cam.BalanceRatioSelector.SetValue('Green')
                print('Green= ', cam.BalanceRatio.GetValue(), end='\t')
                cam.BalanceRatioSelector.SetValue('Blue')
                print('Blue= ', cam.BalanceRatio.GetValue())

            cam.BalanceWhiteAuto.SetValue('Once')

            i = 0
            while not cam.BalanceWhiteAuto.GetValue() == 'Off':
                cam.GrabOne(5000)
                i += 1

                if i > 100:
                    print('Auto Gain was not successful')
                    break

            # get final values
            if self._verbosity > 1:
                print('Final balance ratio:', end='\t')
                cam.BalanceRatioSelector.SetValue('Red')
                print('Red= ', cam.BalanceRatio.GetValue(), end='\t')
                cam.BalanceRatioSelector.SetValue('Green')
                print('Green= ', cam.BalanceRatio.GetValue(), end='\t')
                cam.BalanceRatioSelector.SetValue('Blue')
                print('Blue= ', cam.BalanceRatio.GetValue())

            cam.Close()

    def set_gain_exposure(self):
        """ Set default values defined in config/params.py """
        self._setup_cams()

        for idx, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):
            cam.Open()
            # set exposure to its reference value
            sn = cam.GetDeviceInfo().GetSerialNumber()
            cam.Gain.SetValue(self._camera_info[sn]['gain'])
            cam.ExposureTime.SetValue(self._camera_info[sn]['exposure'])
            cam.Close()

    def run_auto_gain(self):
        """ Adjust gain while keeping exposure time fixed. """
        self._setup_cams()

        for idx, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):
            print('Auto gain for: %d \t%s \t\t%s' % (idx, cam_name, cam.GetDeviceInfo().GetSerialNumber()))

            cam.Open()
            cam.AutoFunctionROISelector.SetValue('ROI1')
            cam.AutoFunctionROIUseBrightness.SetValue(True)
            cam.AutoFunctionROISelector.SetValue('ROI2')
            cam.AutoFunctionROIUseBrightness.SetValue(False)

            # define ROI to use
            cam.AutoFunctionROISelector.SetValue('ROI1')
            wOff = int(cam.Width.GetValue() / 4)
            hOff = int(cam.Height.GetValue() / 4)
            wSize = int(cam.Width.GetValue() / 2)
            hSize = int(cam.Height.GetValue() / 2)

            # Enforce size is a multiple of two (important because of bayer pattern)
            wSize = int(wSize/2)*2
            hSize = int(hSize/2)*2

            # set ROI
            cam.AutoFunctionROIWidth.SetValue(wSize)
            cam.AutoFunctionROIHeight.SetValue(hSize)
            cam.AutoFunctionROIOffsetX.SetValue(wOff)
            cam.AutoFunctionROIOffsetY.SetValue(hOff)

            # 0.3 means that the target brightness is 30 % of the maximum brightness
            # of the raw pixel value read out from the sensor.
            cam.AutoTargetBrightness.SetValue(0.2)

            # give auto some bounds
            cam.AutoGainLowerLimit.SetValue(cam.Gain.GetMin())
            cam.AutoGainUpperLimit.SetValue(cam.Gain.GetMax())

            # set exposure to its reference value
            sn = cam.GetDeviceInfo().GetSerialNumber()
            cam.ExposureTime.SetValue(self._camera_info[sn]['exposure'])
            # print('Initial gain', cam.Gain.GetValue())
            cam.GainAuto.SetValue('Once')

            i = 0
            while not cam.GainAuto.GetValue() == 'Off':
                cam.GrabOne(5000)
                i += 1

                if i > 100:
                    print('Auto Gain was not successful')
                    break

            if self._verbosity > 1:
                print('Final gain after %d images %.1f '
                      '(in [%.1f, %.1f])' % (i, cam.Gain.GetValue(),
                                             cam.Gain.GetMin(), cam.Gain.GetMax()))

            # check if we should give warnings
            if rel_close(cam.Gain.GetValue(), cam.Gain.GetMax()):
                if self._verbosity > 0:
                    print('Final gain value is very close to its maximum value:'
                          ' Consider increasing gain, opening camera shutter wider or put more light.')

            cam.Close()

    def run_auto_exposure(self):
        """ Adjust exposure time while keeping gain fixed. """
        self._setup_cams()

        for idx, (cam_name, cam) in enumerate(zip(self._camera_names_list, self._camera_list)):

            print('Auto exposure for: %d \t%s \t\t%s' % (idx, cam_name, cam.GetDeviceInfo().GetSerialNumber()))

            cam.Open()
            cam.AutoFunctionROISelector.SetValue('ROI1')
            cam.AutoFunctionROIUseBrightness.SetValue(True)
            cam.AutoFunctionROISelector.SetValue('ROI2')
            cam.AutoFunctionROIUseBrightness.SetValue(False)

            # define ROI to use
            cam.AutoFunctionROISelector.SetValue('ROI1')
            wOff = int(cam.Width.GetValue() / 4)
            hOff = int(cam.Height.GetValue() / 4)
            wSize = int(cam.Width.GetValue() / 2)
            hSize = int(cam.Height.GetValue() / 2)

            # Enforce size is a multiple of two (important because of bayer pattern)
            wSize = int(wSize/2)*2
            hSize = int(hSize/2)*2

            # set ROI
            cam.AutoFunctionROIWidth.SetValue(wSize)
            cam.AutoFunctionROIHeight.SetValue(hSize)
            cam.AutoFunctionROIOffsetX.SetValue(wOff)
            cam.AutoFunctionROIOffsetY.SetValue(hOff)

            # 0.3 means that the target brightness is 30 % of the maximum brightness
            # of the raw pixel value read out from the sensor.
            cam.AutoTargetBrightness.SetValue(0.2)

            # give auto some bounds
            cam.AutoExposureTimeLowerLimit.SetValue(cam.AutoExposureTimeLowerLimit.GetMin())
            cam.AutoExposureTimeUpperLimit.SetValue(cam.AutoExposureTimeUpperLimit.GetMax())

            # set exposure to its reference value
            sn = cam.GetDeviceInfo().GetSerialNumber()
            cam.Gain.SetValue(self._camera_info[sn]['gain'])
            # print('Initial exposure', cam.ExposureTime.GetValue())
            cam.ExposureAuto.SetValue('Once')

            i = 0
            while not cam.ExposureAuto.GetValue() == 'Off':
                cam.GrabOne(5000)
                i += 1

                if i > 100:
                    print('Auto ExposureAuto was not successful')
                    break

            if self._verbosity > 1:
                print('Final exposure after %d '
                      'images %d ms (in [%d, %d])' % (i, cam.ExposureTime.GetValue(),
                                                      cam.AutoExposureTimeLowerLimit.GetMin(), cam.AutoExposureTimeUpperLimit.GetMax()))

            # check if we should give warnings
            if rel_close(cam.ExposureTime.GetValue(), cam.AutoExposureTimeUpperLimit.GetMax()):
                if self._verbosity > 0:
                    print('Final exposure value is very close to its maximum value:'
                          ' Consider increasing gain, opening camera shutter wider or put more light.')

            cam.Close()

    def _init_trigger(self):
        self._trigger = trigger_factory()
        self._trigger.set_fps(self.fps)

    def _init_recording(self):
        """Create output folders. """
        take_name = self._take_name + '_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        out_path = os.path.join(params_t.out_path,
                                take_name)
        my_mkdir(out_path)
        out_path = out_path + '/run%03d' % self._rid + '_%s.avi'
        return out_path

    def _setup_cams(self):
        """ Searches for attached Basler cams and puts them into our list of cameras. """
        # reset cams
        self._camera_list, self._camera_names_list = list(), list()

        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        devices = tlFactory.EnumerateDevices()
        if len(devices) == 0:
            print('No camera present. Quitting')
            exit()

        if self._verbosity > 0:
            print('Found %d cameras' % len(devices))

        for did, dev in enumerate(devices):
            self._camera_list.append( pylon.InstantCamera(tlFactory.CreateDevice(dev)) )
            assert devices[did].IsSerialNumberAvailable(), 'Could not read serial number.'
            sn = dev.GetSerialNumber()
            msg = 'Camera with serial number %s does not have a given name. Please define one in config/camera_names.py'  % sn
            assert sn in self._camera_info.keys(), msg
            give_name = self._camera_info[sn]['name']
            self._camera_names_list.append(give_name)
            if self._verbosity > 0:
                print('Device %d: %s %s' % (did, give_name, sn))

    def _config_cams_continuous(self, cam):
        # cam.RegisterImageEventHandler(MyImageEventHandler(),
        #                               pylon.RegistrationMode_Append,
        #                               pylon.Cleanup_Delete)

        if not cam.IsOpen():
            cam.Open()

        # some things are to be set as attributes ...
        cam.AcquisitionFrameRate = self.fps
        cam.AcquisitionFrameRateEnable = True

        cam.MaxNumBuffer.SetValue(16)  # how many buffers there are in total (empty and full)
        cam.OutputQueueSize.SetValue(8)  # maximal number of filled buffers (if another image is retrieved it replaces an old one and is called skipped)

        # ... other via this weird nodemap
        nodemap = cam.GetNodeMap()
        nodemap.GetNode("AcquisitionMode").FromString("Continuous")
        if self.is_color_cam(cam):
            nodemap.GetNode("PixelFormat").FromString("BGR8")
            cam.DemosaicingMode.SetValue('BaslerPGI')
        else:
            nodemap.GetNode("PixelFormat").FromString("Mono8")
        nodemap.GetNode("TriggerMode").FromString("Off")

    def _config_cams_hw_trigger(self, cam):
        # cam.RegisterImageEventHandler(MyImageEventHandler(),
        #                               pylon.RegistrationMode_Append,
        #                               pylon.Cleanup_Delete)
        if not cam.IsOpen():
            cam.Open()
        cam.AcquisitionFrameRate = params_t.max_fps  # here we go to max fps in order to not be limited
        cam.AcquisitionFrameRateEnable = True
        # behavior wrt to these values is a bit strange to me. Important seems to be to use LastImages Strategy and make MaxNumBuffers larger than OutputQueueSize. Otherwise its not guaranteed to work
        cam.MaxNumBuffer.SetValue(16)  # how many buffers there are in total (empty and full)
        cam.OutputQueueSize.SetValue(8)  # maximal number of filled buffers (if another image is retrieved it replaces an old one and is called skipped)

        nodemap = cam.GetNodeMap()
        nodemap.GetNode("AcquisitionMode").FromString("Continuous")
        if self.is_color_cam(cam):
            nodemap.GetNode("PixelFormat").FromString("BGR8")
            cam.DemosaicingMode.SetValue('BaslerPGI')
        else:
            nodemap.GetNode("PixelFormat").FromString("Mono8")

        nodemap.GetNode("LineSelector").FromString("Line3")
        nodemap.GetNode("LineMode").FromString("Input")

        nodemap.GetNode("TriggerMode").FromString("On")
        nodemap.GetNode("TriggerSource").FromString("Line3")
        nodemap.GetNode("TriggerActivation").FromString("RisingEdge")

    def is_color_cam(self, cam):
        # get available formats
        available_formats = cam.PixelFormat.Symbolics

        # figure out if a color format is available
        if 'BGR8' in available_formats:
            return True
        return False

