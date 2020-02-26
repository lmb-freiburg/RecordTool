from config.params import params_t


class camera_type(object):
    basler = 'basler'
    realsense = 'realsense'


def get_camera_infos():
    if params_t.cam_set == 'info':
        return _get_camera_infos_cs()
    elif params_t.cam_set == 'neuro':
        return _get_camera_infos_neuro()
    else:
        raise NotImplementedError


def _get_camera_infos_neuro():
    camera_names = dict()
    camera_names["22382608"] = {"name": "cam0", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22551262"] = {"name": "cam1", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22561089"] = {"name": "cam2", "exposure": params_t.exposure, "gain": params_t.gain}

    camera_names["22561096"] = {"name": "cam3", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22561086"] = {"name": "cam4", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22561087"] = {"name": "cam5", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22551254"] = {"name": "cam6", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22479410"] = {"name": "cam7", "exposure": params_t.exposure, "gain": params_t.gain}

    return camera_names


def _get_camera_infos_cs():
    camera_names = dict()
    camera_names["22501177"] = {"name": "cam0", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22501174"] = {"name": "cam1", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22551251"] = {"name": "cam2", "exposure": params_t.exposure, "gain": params_t.gain}

    camera_names["22625334"] = {"name": "cam3", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22625338"] = {"name": "cam4", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22625346"] = {"name": "cam5", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22625357"] = {"name": "cam6", "exposure": params_t.exposure, "gain": params_t.gain}
    camera_names["22625348"] = {"name": "cam7", "exposure": params_t.exposure, "gain": params_t.gain}

    return camera_names
