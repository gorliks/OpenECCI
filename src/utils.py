import datetime
import time
from PIL import Image
import cv2
import numpy as np
import cv2
import matplotlib.pyplot as plt
import tifffile
import xml.etree.ElementTree as ET

def test_load():
    print('utils loaded')


def map_scrollbar_to_value(x_start : float = -5,
                           x_end   : float = +5,
                           number_of_steps : int =1000,
                           value_to_map : int = 0) -> float:
    a0 = x_start
    slope = (x_end - x_start) / number_of_steps
    return (a0 + slope * value_to_map)


def map_value_to_scrollbar(x_start : float = -5,
                           x_end   : float = +5,
                           number_of_steps : int =1000,
                           value_to_map : int = 0) -> int:
    slope = number_of_steps / (x_end - x_start)
    return int( (value_to_map-x_start) * slope )


def load_image(file_path):
    #image = Image.open(file_path).convert('L') # load image .tiff .png .jpg, convert to grayscale
    #image = np.array(image, dtype=np.float64)
    image = plt.imread(file_path)
    return image


def normalise(image):
    norm = np.linalg.norm(image)
    image_norm = image / norm  # normalized matrix
    return image_norm

def calculate_difference(image1, image2):
    return normalise(image1) - normalise(image2)

def modal_assurance_criterion(image1, image2):
    """
        Computers and Structures 74 (2000) 375-383
        The Modal Assurance Criterion – Twenty Years of Use and Abuse, SOund and Vibrations 2003
    """
    image1 = normalise(image1)
    image2 = normalise(image2)
    m, n = image1.shape
    I1 = 0
    I2 = 0
    I3 = 0
    for ii in range(m):
        I1 = I1 + np.dot( image1[ii,:], np.conj(image2[ii,:]) )
        I2 = I2 + np.dot( image1[ii,:], np.conj(image1[ii,:]) )
        I3 = I3 + np.dot( image2[ii,:], np.conj(image2[ii,:]) )

    MAC = np.abs(I1)**2 / (I2*I3)
    return MAC


def current_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime("%y%m%d.%H%M%S")


def enhance_contrast(image, clipLimit=1.0, tileGridSize=8):
    # if image.dtype == 'float64' or 'uint64':
    #     pass

    # the images needs to be 8bit, otherwise the algorithm does not work TODO fix 8-bit to any-bit
    try:
        image = image / image.max()
    except:
        image = image.data / image.data.max()
    image = (image * 2 ** 8).astype('uint8')

    tileGridSize = int(tileGridSize)

    clahe = cv2.createCLAHE(clipLimit=clipLimit,
                            tileGridSize=(tileGridSize, tileGridSize))
    image = clahe.apply(image)
    return image


def equalise_histogram(image, bitdepth=8):
    try:
        _image = image.data
    except:
        _image = image

    # _image = _image / _image.max()
    # _image = (_image * 2 ** bitdepth).astype("uint8")

    _image = cv2.equalizeHist(_image)
    return _image


def resize(image, size=(200,200)):
    return cv2.resize(image, size)



def _reformat_HKL_metadata(metadata):
    output = {}
    output['pc_x'] = float(metadata['pattern-center-x-pu'])
    output['pc_y'] = float(metadata['pattern-center-y-pu'])
    output['pc_z'] = float(metadata['detector-distance-pu'])
    output['energy'] = float(metadata['sem-acc-voltage-kv'])
    output['working_distance'] = float(metadata['sem-working-distance-mm'])
    #
    output['sample_tilt']      = float(metadata['specimen-tilt-deg'])
    output['sample_tilt_axis'] = metadata['specimen-tilt-axis']
    #
    output['detector_tilt_Euler1'] = float(metadata['detector-orientation-euler1-deg'])
    output['detector_tilt_Euler2'] = float(metadata['detector-orientation-euler2-deg'])
    output['detector_tilt_Euler3'] = float(metadata['detector-orientation-euler3-deg'])
    output['detector_tilt']        = float(metadata['detector-orientation-euler1-deg'])
    #
    output['lens-distortion']       = float(metadata['lens-distortion'])
    output['lens-field-of-view-mm'] = float(metadata['lens-field-of-view-mm'])
    #
    output['detector-insertion-distance-mm'] = float(metadata['detector-insertion-distance-mm'])
    output['beam-position-offset-x-um'] = float(metadata['beam-position-offset-x-um'])
    output['beam-position-offset-y-um'] = float(metadata['beam-position-offset-y-um'])

    return output


def HKL_metadata(file_name, reformat='True'):
    with tifffile.TiffFile(file_name) as tif:
        tif_tags = {}
        for tag in tif.pages[0].tags.values():
            name, value = tag.name, tag.value
            tif_tags[name] = value
        #image = tif.pages[0].asarray()

        raw_metadata = tif_tags['51122']
        myroot = ET.fromstring(raw_metadata)

        metadata = {myroot[0][i].tag: myroot[0][i].text for i in range(len(myroot[0]))}

        if reformat:
            try:
                metadata = _reformat_HKL_metadata(metadata)
            except Exception as e:
                print(f'could not reformat the metadata, {e}')

    return metadata


class BlittedCursor:
    """
    A cross-hair cursor using blitting for faster redraw.
    """

    def __init__(self, ax):
        self.ax = ax
        self.background = None
        self.horizontal_line = ax.axhline(color='y', lw=0.8, ls='--')
        self.vertical_line = ax.axvline(color='y', lw=0.8, ls='--')
        # text location in axes coordinates
        self.text = ax.text(0.72, 0.9, '', transform=ax.transAxes)
        self._creating_background = False
        ax.figure.canvas.mpl_connect('draw_event', self.on_draw)

    def on_draw(self, event):
        self.create_new_background()

    def set_cross_hair_visible(self, visible):
        need_redraw = self.horizontal_line.get_visible() != visible
        self.horizontal_line.set_visible(visible)
        self.vertical_line.set_visible(visible)
        self.text.set_visible(visible)
        return need_redraw

    def create_new_background(self):
        if self._creating_background:
            # discard calls triggered from within this function
            return
        self._creating_background = True
        self.set_cross_hair_visible(False)
        self.ax.figure.canvas.draw()
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox)
        self.set_cross_hair_visible(True)
        self._creating_background = False

    def on_mouse_move(self, event):
        if self.background is None:
            self.create_new_background()
        if not event.inaxes:
            need_redraw = self.set_cross_hair_visible(False)
            if need_redraw:
                self.ax.figure.canvas.restore_region(self.background)
                self.ax.figure.canvas.blit(self.ax.bbox)
        else:
            self.set_cross_hair_visible(True)
            # update the line positions
            x, y = event.xdata, event.ydata
            self.horizontal_line.set_ydata([y])
            self.vertical_line.set_xdata([x])
            #self.text.set_text('x=%1.2f, y=%1.2f' % (x, y))

            self.ax.figure.canvas.restore_region(self.background)
            self.ax.draw_artist(self.horizontal_line)
            self.ax.draw_artist(self.vertical_line)
            self.ax.draw_artist(self.text)
            self.ax.figure.canvas.blit(self.ax.bbox)

