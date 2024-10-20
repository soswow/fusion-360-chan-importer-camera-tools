import os
from typing import List

from adsk.core import *
from adsk.fusion import *

from ...lib.fusionAddInUtils import log
from .chan import ChanFrame, parse_chan_file

app = Application.get()
product = Design.cast(app.activeProduct)

local_chan_frames: List[ChanFrame] = None
file_paths = []
default_reference_component_name = 'Reference'

ATTR_GROUP_ID = 'scan_ref_tool_group'

CHAN_FILEPATH_ATTRIBUTE_ID = 'chan_filepath'
IMAGES_DIRECTORY_ATTRIBUTE_ID = 'images_directory'
REF_COMPONENT_NAME_ATTRIBUTE_ID = 'reference_component_name'
SCALE_FACTOR_ATTRIBUTE_ID = 'scale_factor'
OPACITY_ATTRIBUTE_ID = 'opacity'

attributes_local_copy = dict()
def _get_attribute(name: str):
    chan_filepath_attribute = product.attributes.itemByName(ATTR_GROUP_ID, name)
    if chan_filepath_attribute:
        return chan_filepath_attribute.value
    else:
        log(f'#get_attribute: no value for {name}')
        return None

def _set_attribute(name: str, value: str):
    product.attributes.add(ATTR_GROUP_ID, name, value)

def set_chan_filepath(chan_filepath: str):
    _set_attribute(CHAN_FILEPATH_ATTRIBUTE_ID, chan_filepath)

def get_chan_filepath():
    return _get_attribute(CHAN_FILEPATH_ATTRIBUTE_ID)
    
def set_images_directory(images_directory: str):
    _set_attribute(IMAGES_DIRECTORY_ATTRIBUTE_ID, images_directory)

def get_images_directory():
    return _get_attribute(IMAGES_DIRECTORY_ATTRIBUTE_ID)
    
def set_reference_component_name(reference_component_name: str):
    _set_attribute(REF_COMPONENT_NAME_ATTRIBUTE_ID, reference_component_name)

def get_reference_component_name():
    return _get_attribute(REF_COMPONENT_NAME_ATTRIBUTE_ID)

def set_scale_factor(scale_factor: float):
    _set_attribute(SCALE_FACTOR_ATTRIBUTE_ID, str(scale_factor))

def get_scale_factor():
    scale_factor = _get_attribute(SCALE_FACTOR_ATTRIBUTE_ID)
    if scale_factor:
        return float(scale_factor)
    else:
        return 1
    
def set_opacity(opacity: int):
    _set_attribute(OPACITY_ATTRIBUTE_ID, str(opacity))

def get_opacity():
    opacity = _get_attribute(OPACITY_ATTRIBUTE_ID)
    if opacity:
        return int(opacity)
    else:
        return 100
    
last_images_directory = None
def list_files_alphanum():
    global file_paths
    global last_images_directory
    images_directory = get_images_directory()
    if not images_directory:
        log('#list_files_alphanum: no image_directory')
        return
    if len(file_paths) > 0 and images_directory == last_images_directory:
        return file_paths
    
    # List all files in the directory
    files = [os.path.join(images_directory, f) for f in os.listdir(images_directory) if os.path.isfile(os.path.join(images_directory, f)) and not f.startswith('.')]

    # Sort the files alphanumerically
    file_paths = sorted(files)
    last_images_directory = images_directory

    return file_paths
    
def get_image_path(frame_number: int):
    files = list_files_alphanum()
    if files:
        return files[frame_number-1]

last_used_chan_filepath = None
last_used_scale_factor = 1
def get_chan_frames():
    global local_chan_frames
    global last_used_chan_filepath
    global last_used_scale_factor

    chan_filepath = get_chan_filepath()
    if not chan_filepath:
        log('#get_chan_frames: no chan filepath')
        return
    scale_factor = get_scale_factor()
    if (local_chan_frames is None and chan_filepath) or last_used_chan_filepath != chan_filepath or last_used_scale_factor != scale_factor:
        local_chan_frames = parse_chan_file(chan_filepath, scale_factor)
        last_used_chan_filepath = chan_filepath
        last_used_scale_factor = scale_factor
        log(f'{len(local_chan_frames)} frames loaded from {chan_filepath}')
    
    return local_chan_frames
        
