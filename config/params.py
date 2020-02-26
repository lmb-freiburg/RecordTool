from utils.VideoWriterFast import codec_t


class params_t:
    cam_set = 'neuro'
    # cam_set = 'info'

    """ default camera parameters """
    fps = 10.0
    cam_timeout = 1000   # time in ms
    exposure = 5000  # default value exposure time in us
    gain = 3.5  # default value gain

    """ default save parameters """
    out_path = '/home/zimmermc/projects/RecordTool/recordings'
    codec = codec_t.divx

    """ default trigger parameters """
    # trigger_type = 'GPIO'
    trigger_type = 'Arduino'
    trigger_delay = 0.0  # delay making cameras ready and trigger start (GPIO only)
    gpio_path = '/dev/ttyACM0'  # where the Arduino or GPIO module registers

    """ valid value range. """
    min_fps = 0.1  # min fps
    max_fps = 100.0  # max fps, also cant be exceeded in hw trigger mode (looks like the python api is limited to around 50fps, Our cameras are limited to 75 fps in BGR mode)

    """ UI settings """
    show_recorded_frames = True  # make false if recording with high fps
    show_delay = 0.5  # maximum time in sec between showing two recorded frames, dont chose this to high because showing is fairly expensive
    show_size = (800, 1000)  # size of window shown during recording

    """ Debugging flags """
    inpaint_image_id = False  # writes cameras given name and frame id into each image
    warn_frame_missing = True  # gives warnings when frames are being lost
    print_aquisition_state = False  # shows how fast we poll cameras, video writer queue state and frames written to video per sec
