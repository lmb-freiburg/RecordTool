# RecordTool

This is the recording software developed in conjunction with our recent publication

    @TechReport{Freipose2020,
        author    = {Christian Zimmermann, Artur Schneider, Mansour Alyahyay, Ilka Diester and Thomas Brox},
        title     = {FreiPose: A Deep Learning Framework for Precise Animal Motion Capture in 3D Spaces},
        year      = {2020},
        url          = {"https://lmb.informatik.uni-freiburg.de/projects/freipose/"}
    }

It allows to record synchronous video from a multi camera rig using Basler cameras and an Arduino for trigger generation.

## Installation guide
Select suitable release of Pylon's Python Bindings from:
    https://github.com/Basler/pypylon/releases

I chose 'pypylon-1.4.0-cp36-cp36m-linux_x86_64.whl' because I want to use python3.6 and have a Linux machine with 64bit.

    pip install ~/libs/pypylon-1.4.0-cp36-cp36m-linux_x86_64.whl
    pip3 install scipy Pillow numpy opencv-python progressbar pyserial

Add your cameras to config/camera_names.py. This gives your cameras unique names. (we already did that for our cams)

## User guide

Start the RecordTool
    
    python3.6 run.py
    
Use 'h' + Enter to get help.

Convert recorded videos to single frames

   python vid2frames.py recordings/take00/run000_cam5.avi --out-path ./recordings_frames/

  

