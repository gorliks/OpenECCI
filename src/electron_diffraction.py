import hyperspy.api as hs
import kikuchipy as kp
import h5py
import numpy as np
import matplotlib.pyplot as plt
import os, glob
import utils

import importlib
importlib.reload(utils)

from diffpy.structure import Atom, Lattice, Structure
from orix.crystal_map import CrystalMap, Phase, PhaseList
from orix.io import load, save, loadctf
from orix import io, plot, quaternion, vector, crystal_map
from orix.quaternion import Orientation, Rotation, symmetry
from orix.vector import Vector3d, AxAngle, Miller

class Kikuchi():
    def __init__(self, mode='EBSD'):
        self.mode = mode
        self.path_to_master_pattern = None
        self.path_to_ctf_file = None

        self.master_pattern = None
        self.pattern = None

        self.Eulers_angles = None
        self.Eulers_average = None
        self.Eulers = None
        self.point_Eulers = None

        self.energy = 20 # keV
        self.pc_x = 0.5
        self.pc_y = 0.5
        self.pc_z = 0.4
        self.pixel_size = 1
        self.binning = 1
        self.detector_tilt = -90
        self.sample_tilt = 0
        self.projection = "lambert"
        self.hemispheres = "both"
        self.detector_shape = (1024, 884)
        self.convention = None #'oxford' #bruker

        self.detector = None


    def update_settings(self,
                        path_to_master_pattern=None,
                        energy=None,
                        pc_x = None,
                        pc_y = None,
                        pc_z = None,
                        pixel_size = None,
                        binning = None,
                        detector_tilt = None,
                        sample_tilt = None,
                        projection = None,
                        hemispheres = None,
                        detector_shape = None,
                        convention = None):
        if path_to_master_pattern is not None: self.path_to_master_pattern = path_to_master_pattern
        if energy is not None: self.energy = energy
        if pc_x is not None: self.pc_x = pc_x
        if pc_y is not None: self.pc_y = pc_y
        if pc_z is not None: self.pc_z = pc_z
        if pixel_size is not None: self.pixel_size = pixel_size
        if binning is not None: self.binning = binning
        if detector_tilt is not None: self.detector_tilt = detector_tilt
        if sample_tilt is not None: self.sample_tilt = sample_tilt
        if projection is not None: self.projection = projection
        if hemispheres is not None: self.hemispheres = hemispheres
        if detector_shape is not None: self.detector_shape = detector_shape
        if convention is not None: self.convention = convention


    def update_settings_from_dict(self, dict):
        self.dictionary = dict
        if 'pc_x' in dict.keys(): self.pc_x = dict['pc_x']
        if 'pc_y' in dict.keys(): self.pc_y = dict['pc_y']
        if 'pc_z' in dict.keys(): self.pc_z = dict['pc_z']
        #
        if 'energy' in dict.keys(): self.energy = dict['energy']
        if 'detector_tilt' in dict.keys(): self.detector_tilt = dict['detector_tilt']
        if 'sample_tilt' in dict.keys(): self.sample_tilt = dict['sample_tilt']
        if 'pc_x' in dict.keys(): self.pc_x = dict['pc_x']
        if 'pc_x' in dict.keys(): self.pc_x = dict['pc_x']
        if 'pc_x' in dict.keys(): self.pc_x = dict['pc_x']
        if 'pc_x' in dict.keys(): self.pc_x = dict['pc_x']


    def load_master_pattern(self, path_to_master_pattern=None):
        try:
            self.master_pattern = kp.load(path_to_master_pattern,
                                         projection=self.projection,
                                         hemisphere=self.hemispheres,
                                         energy=self.energy)
            print(f'loading MP: projection {self.projection}, '
                  f'hemispheres {self.hemispheres}, energy {self.energy}')
            self.path_to_master_pattern = path_to_master_pattern
            # TODO crystal phase more generic, now hardcoded as Si and space group 227
            phase = crystal_map.Phase(name="Si", space_group=227)
            self.master_pattern.phase = phase
            print('Master pattern loaded successfully')
            return('Master pattern loaded successfully')
        except Exception as e:
            print('could not load the master pattern')
            return('could not load the master pattern')


    def create_detector(self):
        self.detector = kp.detectors.EBSDDetector(
            shape=self.detector_shape,
            tilt=self.detector_tilt,
            sample_tilt=self.sample_tilt,
            pc=[self.pc_x, self.pc_y, self.pc_z],
            px_size=self.pixel_size,
            binning=self.binning,
            convention=self.convention
        )


    def load_xmap(self, file_name=None):
        if file_name is not None:
            self.path_to_ctf_file = file_name
            phase_id, x, y, bands, errors, euler1, euler2, euler3, MAD, BC, BS = \
                np.loadtxt(file_name, skiprows=16, unpack=True)

            self.Eulers_angles = np.array([euler1, euler2, euler3])
            self.Eulers_average = np.mean(self.Eulers_angles, axis=1)

            # Convert Euler angle convention from Oxford to EDAX
            self.Eulers = np.radians(np.column_stack((self.Eulers_average)))

            # post-multiply the Rotation instance created from AZtec Euler angles with Rotation.from_axes_angles([0, 0, 1], -np.pi / 2)
            self.point_Eulers = Rotation.from_euler(self.Eulers) * Rotation.from_axes_angles([0, 0, 1], -np.pi / 2)

            return self.point_Eulers

        else:
            print('......')


    def calculate_diffraction_pattern(self, tilt_x = 0, tilt_y = 0):
        self.create_detector()
        tilt_y = [0, -tilt_y, 0]
        tilt_x = [-90, -tilt_x, 90]
        st_tilt_y = quaternion.Rotation.from_euler(np.deg2rad([tilt_y]))
        st_tilt_x = quaternion.Rotation.from_euler(np.deg2rad([tilt_x]))

        if (self.master_pattern is not None) and (self.point_Eulers is not None):
            self.pattern = self.master_pattern.get_patterns(
                                        rotations=self.point_Eulers * st_tilt_y * st_tilt_x,
                                        detector=self.detector,
                                        energy=self.energy,
                                        phase=self.master_pattern.phase,
                                        compute=True)

            return np.squeeze(self.pattern.data)

        else:
            return( np.random.randint(0, 255, self.detector_shape) )




if __name__ == "__main__":
    path_to_data =  r'C:\Users\sergeyg\Github\OpenECCI\data'
    master_pattern_file = r'Si-master-20kv.h5'
    ctf_file = r'20kv_26nA_15mm WD_4x4 binning Si Map Data 2.ctf'

    measured_ref_ECP_file_name  = os.path.join(path_to_data, 'Si_ECP_001.tif')
    measured_ref_EBSD_file_name = os.path.join(path_to_data, 'Si_pattern.tiff')

    file_name_MP = os.path.join(path_to_data, master_pattern_file)
    print(file_name_MP)
    file_name_ctf = os.path.join(path_to_data, ctf_file)
    print(file_name_ctf)

    ########################################################################################################################################
    ecp_reference = Kikuchi(mode='ECP')
    ecp_reference.update_settings(energy=20,
                                  pc_x = 0.5,
                                  pc_y = 0.5,
                                  pc_z = 4.0,
                                  pixel_size = 10,
                                  binning = 1,
                                  detector_tilt = -90,
                                  sample_tilt = 0,
                                  projection = 'lambert',
                                  hemispheres = 'both',
                                  detector_shape = (884, 1024),
                                  convention=None)

    ecp_reference.load_master_pattern(path_to_master_pattern=file_name_MP)
    ecp_reference.load_xmap(file_name=file_name_ctf)
    print(f'ECP point Euler angle = {ecp_reference.point_Eulers}')

    measured_ref_ECP = utils.load_image(measured_ref_ECP_file_name)
    measured_ref_ECP = measured_ref_ECP[:884,:]
    simulated_ECP = ecp_reference.calculate_diffraction_pattern(tilt_x=0,
                                                                tilt_y=0)
    difference_ECP = utils.calculate_difference(image1=measured_ref_ECP,
                                                image2=simulated_ECP)


    ########################################################################################################################################
    ebsd_reference = Kikuchi(mode='EBSD')
    ebsd_reference.update_settings(energy=20,
                                   pc_x = 0.4895443444173796,
                                   pc_y = 0.62040462473423286,
                                   pc_z = 0.49422998235067966,
                                   pixel_size = 59.2,
                                   binning = 4,
                                   detector_tilt = 0.0,
                                   sample_tilt = 70.0,
                                   projection = 'lambert',
                                   hemispheres = 'both',
                                   detector_shape = (120, 160),
                                   convention='oxford')
    ebsd_reference.load_master_pattern(path_to_master_pattern=file_name_MP)
    ebsd_reference.load_xmap(file_name=file_name_ctf)
    print(f'EBSD point Euler angle = {ebsd_reference.point_Eulers}')

    measured_ref_EBSD = utils.load_image(measured_ref_EBSD_file_name)
    measured_ref_EBSD = np.flipud(measured_ref_EBSD)
    simulated_EBSD = ebsd_reference.calculate_diffraction_pattern(tilt_x=0,
                                                                  tilt_y=0)
    difference_EBSD = utils.calculate_difference(image1=measured_ref_EBSD,
                                                 image2=simulated_EBSD)

    ########################################################################################################################################

    fig = plt.figure(figsize=(10, 5))
    ax1 = fig.add_subplot(231)
    ax2 = fig.add_subplot(232)
    ax3 = fig.add_subplot(233)
    ax4 = fig.add_subplot(234)
    ax5 = fig.add_subplot(235)
    ax6 = fig.add_subplot(236)

    ax1.imshow(measured_ref_ECP, cmap='gray')
    ax2.imshow(simulated_ECP, cmap='gray')
    ax3.imshow(difference_ECP, cmap='bwr')
    ###
    ax4.imshow(measured_ref_EBSD, cmap='gray')
    ax5.imshow(simulated_EBSD, cmap='gray')
    ax6.imshow(difference_EBSD, cmap='bwr')

    plt.show()
